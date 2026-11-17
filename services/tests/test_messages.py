from mq3mqtt.messages import (
    leitura_de_linha_csv,
    parse_evento,
    parse_leitura,
    parse_topic,
    topic,
)


def test_linha_do_csv_vira_leitura_com_dht_vazio():
    row = leitura_de_linha_csv(
        {
            "amostra": "4",
            "t_ms": "3000",
            "mq3_raw": "410",
            "ppm": "0.0",
            "mq135_raw": "390",
            "mq135_mv": "300",
            "temperature_c": "",
            "humidity_pct": "",
            "alcool": "0",
        },
        "leituras_3",
    )
    assert row["sessao"] == "leituras_3.csv"
    assert row["t_ms"] == 3000
    assert row["mq3_raw"] == 410
    assert row["temperature_c"] is None
    assert row["humidity_pct"] is None
    assert row["ppm"] == 0.0
    assert row["alcool"] == 0


def test_leitura_sem_mq3_falha():
    try:
        parse_leitura({"sessao": "leituras_1.csv", "amostra": 1, "t_ms": 0, "mq3_raw": ""})
    except ValueError as exc:
        assert "mq3_raw" in str(exc)
    else:
        raise AssertionError("mq3_raw vazio deveria falhar")


def test_topico_separa_placa_e_tipo():
    assert topic("bancada", "leituras") == "mq3/bancada/leituras"
    assert parse_topic("mq3/bancada/sopro_pronto") == ("bancada", "sopro_pronto")


def test_evento_de_sopro():
    evento = parse_evento(
        {"sessao": "leituras_1.csv", "evento": "sopro_fim", "t_ms": 45000, "attempt_id": "p01-1"}
    )
    assert evento["evento"] == "sopro_fim"
    assert evento["attempt_id"] == "p01-1"
