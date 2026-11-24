"""Servidor do modelo ao vivo, no contrato da coleta (``applications/coleta/mensagens.py``)."""

import json
from pathlib import Path

import pytest

from mq3mqtt.ao_vivo import (
    ESPERA_APOS_SOPRO_S,
    FimDeSopro,
    classificar_sopro,
    fim_de_sopro,
    sessao_da_rodada,
)

RODADA = "7f1c0a52-0000-4000-8000-000000000009"


def _msg(**campos) -> bytes:
    return json.dumps(campos).encode("utf-8")


def test_fim_de_sopro_le_o_evento_da_coleta():
    fim = fim_de_sopro("mq3/placa01/eventos", _msg(rodada_id=RODADA, tipo="sopro_fim", t_ms=45000))
    assert fim == FimDeSopro(placa="placa01", rodada_id=RODADA, t_ms=45000)


@pytest.mark.parametrize(
    "topico, corpo",
    [
        ("mq3/placa01/eventos", _msg(rodada_id=RODADA, tipo="sopro_inicio", t_ms=40000)),
        ("mq3/placa01/eventos", _msg(rodada_id=RODADA, tipo="rodada_fim", t_ms=90000)),
        ("mq3/placa01/leituras", _msg(rodada_id=RODADA, tipo="sopro_fim", t_ms=45000)),
        ("outro/placa01/eventos", _msg(rodada_id=RODADA, tipo="sopro_fim", t_ms=45000)),
        ("mq3/placa01/eventos", b"nao e json"),
        ("mq3/placa01/eventos", _msg(tipo="sopro_fim", t_ms=45000)),
    ],
)
def test_o_resto_e_ignorado(topico, corpo):
    assert fim_de_sopro(topico, corpo) is None


def test_espera_a_janela_depois_do_sopro():
    from src.features import AFTER_SECONDS

    from mq3mqtt.ao_vivo import JANELA_DEPOIS_MS

    assert ESPERA_APOS_SOPRO_S > AFTER_SECONDS
    assert JANELA_DEPOIS_MS == AFTER_SECONDS * 1000


def test_sessao_da_rodada():
    assert sessao_da_rodada("leituras_3.csv", RODADA) == "leituras_3.csv"
    assert sessao_da_rodada(None, RODADA) == f"{RODADA}.csv"
    assert sessao_da_rodada("", RODADA) == f"{RODADA}.csv"


def _rodada_com_sopro(pg, com_inicio: bool = True) -> None:
    pg.execute(
        "INSERT INTO rodadas (id, placa, arquivo_sessao, origem) VALUES (%s, 'placa01', 'leituras_3.csv', 'placa')",
        (RODADA,),
    )
    for amostra in range(1, 91):
        pg.execute(
            "INSERT INTO leituras (rodada_id, amostra, t_ms, mq3_raw, humidity_pct) VALUES (%s, %s, %s, 500, 60)",
            (RODADA, amostra, amostra * 1000),
        )
    if com_inicio:
        pg.execute("INSERT INTO eventos (rodada_id, tipo, t_ms) VALUES (%s, 'sopro_inicio', 40000)", (RODADA,))
    pg.execute("INSERT INTO eventos (rodada_id, tipo, t_ms) VALUES (%s, 'sopro_fim', 45000)", (RODADA,))


@pytest.mark.integracao
def test_classifica_e_grava_o_resultado(pg):
    _rodada_com_sopro(pg)
    fim = FimDeSopro(placa="placa01", rodada_id=RODADA, t_ms=45000)

    resultado = classificar_sopro(pg, fim, Path("modelo_que_nao_existe.joblib"))

    assert resultado["rodada_id"] == RODADA
    assert resultado["sessao"] == "leituras_3.csv"
    assert resultado["status"] == "sem_modelo"
    assert resultado["prediction"] is None
    linha = pg.execute("SELECT status, attempt_id FROM resultados WHERE rodada_id = %s", (RODADA,)).fetchone()
    assert linha == ("sem_modelo", resultado["attempt_id"])


@pytest.mark.integracao
def test_sopro_fim_sem_inicio_nao_inventa_classe(pg):
    _rodada_com_sopro(pg, com_inicio=False)
    fim = FimDeSopro(placa="placa01", rodada_id=RODADA, t_ms=45000)

    resultado = classificar_sopro(pg, fim, Path("modelo_que_nao_existe.joblib"))

    assert resultado["status"] == "sem_inicio"
    assert resultado["prediction"] is None


class _Agenda:
    """Guarda os timers em vez de esperar."""

    def __init__(self):
        self.pendentes = []

    def __call__(self, atraso_s, funcao, *args):
        self.pendentes.append((atraso_s, funcao, args))

    def rodar(self):
        atual, self.pendentes = self.pendentes, []
        for _, funcao, args in atual:
            funcao(*args)


def _servidor(classificar, ultima_ms, conectar=lambda: object()):
    from mq3mqtt.ao_vivo import ServidorAoVivo

    publicados = []
    agenda = _Agenda()
    servidor = ServidorAoVivo(
        conectar=conectar,
        model_path=Path("x.joblib"),
        publicar=lambda topico, corpo: publicados.append((topico, json.loads(corpo))),
        agendar=agenda,
        classificar=classificar,
        ultima_leitura_ms=ultima_ms,
    )
    return servidor, agenda, publicados


FIM = _msg(rodada_id=RODADA, tipo="sopro_fim", t_ms=45000)


def test_sopro_fim_repetido_classifica_uma_vez():
    chamadas = []
    servidor, agenda, publicados = _servidor(
        lambda con, fim, path, aviso: chamadas.append(fim) or {"status": "sem_modelo", "prediction": None},
        lambda con, rodada_id: 80000,
    )
    servidor.ao_receber("mq3/p1/eventos", FIM)
    servidor.ao_receber("mq3/p1/eventos", FIM)
    agenda.rodar()
    assert len(chamadas) == 1
    assert publicados[0][0] == "mq3/p1/resultado"


def test_espera_as_leituras_atrasadas_e_depois_avisa():
    avisos = []
    servidor, agenda, publicados = _servidor(
        lambda con, fim, path, aviso: avisos.append(aviso) or {"status": "classificado", "prediction": "sem_efeito"},
        lambda con, rodada_id: 50000,  # janela "depois" (até 75000) nunca completa
    )
    servidor.ao_receber("mq3/p1/eventos", FIM)
    for _ in range(10):
        agenda.rodar()
    assert len(publicados) == 1
    assert avisos == ["a janela depois do sopro estava incompleta (leituras até 50.0 s)"]


def test_reconecta_quando_o_banco_cai():
    import psycopg

    conexoes = []
    tentativas = []

    def classificar(con, fim, path, aviso):
        tentativas.append(con)
        if len(tentativas) == 1:
            raise psycopg.OperationalError("caiu")
        return {"status": "sem_modelo", "prediction": None}

    servidor, agenda, publicados = _servidor(
        classificar, lambda con, rodada_id: 80000, conectar=lambda: conexoes.append(object()) or conexoes[-1]
    )
    servidor.ao_receber("mq3/p1/eventos", FIM)
    agenda.rodar()
    assert len(publicados) == 1
    assert tentativas[0] is not tentativas[1]
