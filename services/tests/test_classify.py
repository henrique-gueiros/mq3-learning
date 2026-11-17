from pathlib import Path

from mq3mqtt.classify import attempt_id_de, montar_resultado


def test_sem_inicio_nao_inventa_classe():
    resultado = montar_resultado("leituras_1.csv", None, 45000, [], Path("ausente.joblib"))
    assert resultado["status"] == "sem_inicio"
    assert resultado["prediction"] is None


def test_sem_modelo_guarda_o_sopro_sem_classificar():
    inicio = {"t_ms": 40000, "attempt_id": None}
    readings = [{"t_ms": 40000, "mq3_raw": 500, "ppm": 12.0, "alcool": 1}]
    resultado = montar_resultado(
        "leituras_1.csv",
        inicio,
        45000,
        readings,
        Path("modelo_que_ainda_nao_existe.joblib"),
    )
    assert resultado["status"] == "sem_modelo"
    assert resultado["prediction"] is None
    assert resultado["prob_sob_efeito"] is None
    assert resultado["attempt_id"] == attempt_id_de("leituras_1.csv", 40000, None)
