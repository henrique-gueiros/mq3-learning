from datetime import datetime, timezone

import pytest

from coleta.casos import CASOS, validar_caso
from coleta.mensagens import (
    codificar,
    decodificar,
    payload_evento,
    payload_leitura,
    payload_rodada,
    topico,
)
from coleta.serial_proto import ler_linha


def test_topicos():
    assert topico("placa01", "leituras") == "mq3/placa01/leituras"
    with pytest.raises(ValueError):
        topico("placa01", "outro")


def test_leitura_com_dht_vazio_vira_null():
    leitura = ler_linha("CSV_LINHA,a.csv,38,811,1222,0.4,462,514,,,0")
    dados = decodificar(codificar(payload_leitura("r1", leitura)))
    assert dados["rodada_id"] == "r1"
    assert dados["temperature_c"] is None
    assert dados["t_ms"] == 811
    assert "bruta" not in dados


def test_rodada_com_inicio_iso():
    inicio = datetime(2026, 11, 5, 14, 0, tzinfo=timezone.utc)
    dados = payload_rodada("r1", "placa01", "perfume", "p01", inicio, "a.csv", "ponte")
    assert dados["inicio"] == "2026-11-05T14:00:00+00:00"
    assert dados["origem"] == "ponte"
    with pytest.raises(ValueError):
        payload_rodada("r1", "placa01", "perfume", "p01", inicio, "a.csv", "outra")


def test_evento():
    assert payload_evento("r1", "sopro_inicio", 20400) == {
        "rodada_id": "r1",
        "tipo": "sopro_inicio",
        "t_ms": 20400,
    }
    assert payload_evento("r1", "rodada_fim", 9, sha256="ab")["sha256"] == "ab"
    with pytest.raises(ValueError):
        payload_evento("r1", "outro", 10)


def test_json_invalido():
    with pytest.raises(ValueError):
        decodificar(b"{")


def test_casos_vem_do_ml():
    assert "perfume" in CASOS and "drink" in CASOS
    assert validar_caso("drink") == "drink"
    with pytest.raises(ValueError, match="perfume"):
        validar_caso("vodka")
