import pytest

from coleta.ingestor import tratar
from coleta.mensagens import codificar

pytestmark = pytest.mark.integracao

RODADA = "7f1c0a52-0000-4000-8000-000000000002"
MSG_RODADA = codificar({
    "rodada_id": RODADA, "placa": "placa01", "caso": "perfume", "participante": "p01",
    "inicio": "2026-11-05T14:00:00+00:00", "arquivo_sessao": "a.csv", "origem": "ponte",
})
MSG_LEITURA = codificar({
    "rodada_id": RODADA, "amostra": 1, "t_ms": 1000, "mq3_raw": 1200, "ppm": 0.4,
    "mq135_raw": 450, "mq135_mv": 520, "temperature_c": None, "humidity_pct": None, "alcool": 0,
})
MSG_SOPRO = codificar({"rodada_id": RODADA, "tipo": "sopro_inicio", "t_ms": 1000})


def _contar(con, tabela):
    return con.execute(f"select count(*) from {tabela}").fetchone()[0]


def test_rodada_leituras_eventos(pg):
    tratar(pg, "mq3/placa01/rodada", MSG_RODADA)
    tratar(pg, "mq3/placa01/leituras", MSG_LEITURA)
    tratar(pg, "mq3/placa01/eventos", MSG_SOPRO)
    assert (_contar(pg, "rodadas"), _contar(pg, "leituras"), _contar(pg, "eventos")) == (1, 1, 1)


def test_mensagem_repetida(pg):
    for _ in range(2):
        tratar(pg, "mq3/placa01/rodada", MSG_RODADA)
        tratar(pg, "mq3/placa01/leituras", MSG_LEITURA)
    assert (_contar(pg, "rodadas"), _contar(pg, "leituras")) == (1, 1)


def test_leitura_antes_da_rodada(pg):
    tratar(pg, "mq3/placa01/leituras", MSG_LEITURA)
    tratar(pg, "mq3/placa01/eventos", MSG_SOPRO)
    tratar(pg, "mq3/placa01/rodada", MSG_RODADA)
    assert pg.execute("select caso from v_leituras").fetchone() == ("perfume",)


def test_json_invalido_nao_derruba(pg, capsys):
    tratar(pg, "mq3/placa01/leituras", b"{")
    tratar(pg, "mq3/placa01/leituras", codificar({"rodada_id": RODADA}))
    assert capsys.readouterr().out.count("aviso:") == 2
    assert _contar(pg, "leituras") == 0


def test_status_e_ignorado(pg):
    tratar(pg, "mq3/placa01/status", b"online")
    assert _contar(pg, "rodadas") == 0


def test_rodada_fim_grava_sha(pg):
    tratar(pg, "mq3/placa01/rodada", MSG_RODADA)
    tratar(pg, "mq3/placa01/eventos", codificar(
        {"rodada_id": RODADA, "tipo": "rodada_fim", "t_ms": 9, "sha256": "cd" * 32}
    ))
    assert pg.execute("select sha256 from rodadas").fetchone() == ("cd" * 32,)
