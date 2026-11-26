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


def test_connect_with_retry_insiste_ate_o_banco_subir(monkeypatch):
    import psycopg

    from mq3mqtt import config

    tentativas = []

    def conectar(url, autocommit):
        tentativas.append(url)
        if len(tentativas) < 50:
            raise psycopg.OperationalError("ainda subindo")
        return "conexao"

    monkeypatch.setattr(psycopg, "connect", conectar)
    assert config.connect_with_retry("postgresql://x", attempts=0, pause_s=0) == "conexao"
    assert len(tentativas) == 50


# ---- modelo contínuo: a placa publica só leituras; o modelo classifica janelas deslizantes ----


def _leitura(t_ms, rodada=RODADA):
    return _msg(rodada_id=rodada, amostra=t_ms // 1000, t_ms=t_ms, mq3_raw=800, humidity_pct=55.0)


def _publicar_leituras(servidor, segundos, rodada=RODADA, placa="p1"):
    for s in range(segundos):
        servidor.ao_receber(f"mq3/{placa}/leituras", _leitura(s * 1000, rodada))


def _servidor_continuo(predicoes):
    """Servidor cujo modelo devolve as classes de ``predicoes`` em ordem."""
    janelas = []

    def classificar(con, fim, path, aviso):
        janelas.append(fim)
        p = predicoes[min(len(janelas), len(predicoes)) - 1]
        return {"rodada_id": fim.rodada_id, "t_ms": fim.t_ms, "status": "classificado", "prediction": p}

    servidor, agenda, publicados = _servidor(classificar, lambda con, rodada_id: 10**9)
    return servidor, agenda, publicados, janelas


def test_continuo_classifica_janelas_de_tres_amostras_quando_ha_o_depois():
    from mq3mqtt.ao_vivo import CONTINUO_AFTER_MS, CONTINUO_BEFORE_MS, CONTINUO_PASSO_MS, CONTINUO_SOPRO_MS

    servidor, agenda, publicados, janelas = _servidor_continuo(["sem_efeito"])
    _publicar_leituras(servidor, 60)
    agenda.rodar()
    # primeira janela começa 15 s depois da primeira leitura; só sai com 30 s de "depois"
    assert janelas[0].inicio_ms == CONTINUO_BEFORE_MS
    assert janelas[0].t_ms - janelas[0].inicio_ms == CONTINUO_SOPRO_MS
    assert all(b.inicio_ms - a.inicio_ms == CONTINUO_PASSO_MS for a, b in zip(janelas, janelas[1:]))
    assert all(j.t_ms + CONTINUO_AFTER_MS <= 59000 for j in janelas)
    assert all(p[1]["origem"] == "continuo" for p in publicados)


def test_continuo_so_alerta_depois_de_janelas_seguidas():
    from mq3mqtt.ao_vivo import ALERTA_JANELAS_SEGUIDAS

    predicoes = ["sob_efeito", "sem_efeito"] + ["sob_efeito"] * (ALERTA_JANELAS_SEGUIDAS + 2)
    servidor, agenda, publicados, _ = _servidor_continuo(predicoes)
    _publicar_leituras(servidor, 90)
    agenda.rodar()
    alertas = [p[1] for p in publicados if p[1]["alerta"]]
    assert len(alertas) == 1  # avisa uma vez quando chega a N seguidas, não a cada janela
    assert alertas[0]["sob_efeito_seguidos"] == ALERTA_JANELAS_SEGUIDAS


def test_rodada_marcada_na_ponte_nao_usa_o_continuo():
    servidor, agenda, publicados, janelas = _servidor_continuo(["sem_efeito"])
    servidor.ao_receber("mq3/p1/eventos", _msg(rodada_id=RODADA, tipo="sopro_inicio", t_ms=1000))
    _publicar_leituras(servidor, 60)
    agenda.rodar()
    assert janelas == []


def test_sopro_marcado_alerta_direto():
    servidor, agenda, publicados = _servidor(
        lambda con, fim, path, aviso: {"status": "classificado", "prediction": "sob_efeito"},
        lambda con, rodada_id: 10**9,
    )
    servidor.ao_receber("mq3/p1/eventos", FIM)
    agenda.rodar()
    assert publicados[0][1]["origem"] == "marcado"
    assert publicados[0][1]["alerta"] is True


@pytest.mark.integracao
def test_classifica_janela_com_inicio_conhecido_sem_evento_no_banco(pg):
    _rodada_com_sopro(pg, com_inicio=False)
    fim = FimDeSopro(placa="placa01", rodada_id=RODADA, t_ms=42000, inicio_ms=40000)

    resultado = classificar_sopro(pg, fim, Path("modelo_que_nao_existe.joblib"))

    assert resultado["status"] == "sem_modelo"  # usou o início dado, não "sem_inicio"
