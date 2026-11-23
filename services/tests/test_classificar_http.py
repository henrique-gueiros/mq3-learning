"""A aba Modelo pede a classe por HTTP. Estes testes não sobem o Docker."""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from pathlib import Path

import pytest

from mq3mqtt.classificar_http import responder, servir

ROOT = Path(__file__).resolve().parents[2]
MODELO = ROOT / "ml" / "models" / "sob_efeito.joblib"
RECORTES = ROOT / "applications" / "frontend" / "src" / "modelo" / "sopros.json"


def _pedido_minimo() -> dict:
    return {
        "sessao": "demo.csv",
        "attempt_id": "demo",
        "blow_start_s": 10,
        "blow_end_s": 15,
        "leituras": [
            {
                "t_ms": 10000,
                "mq3_raw": 400,
                "mq135_raw": 200,
                "temperature_c": 25,
                "humidity_pct": 40,
                "ppm": 0.2,
            }
        ],
    }


def test_sem_modelo_nao_inventa_classe(tmp_path):
    status, corpo = responder(
        "POST",
        "/modelo/classificar",
        json.dumps(_pedido_minimo()).encode(),
        tmp_path / "ausente.joblib",
    )
    assert status == 200
    assert corpo["status"] == "sem_modelo"
    assert corpo["prediction"] is None


def test_pedido_incompleto_volta_400(tmp_path):
    status, corpo = responder("POST", "/modelo/classificar", b"{}", tmp_path / "ausente.joblib")
    assert status == 400
    assert "leituras" in corpo["detail"]


def test_saude_diz_se_o_arquivo_existe(tmp_path):
    status, corpo = responder("GET", "/modelo/saude", b"", tmp_path / "ausente.joblib")
    assert status == 200
    assert corpo == {"ok": True, "modelo": False}


def test_http_devolve_sem_modelo(tmp_path):
    server = servir(tmp_path / "ausente.joblib", "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        porta = server.server_address[1]
        req = urllib.request.Request(
            f"http://127.0.0.1:{porta}/modelo/classificar",
            data=json.dumps(_pedido_minimo()).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            corpo = json.loads(resp.read().decode())
        assert corpo["status"] == "sem_modelo"
    finally:
        server.shutdown()


def test_recortes_da_aba_recebem_a_classe_do_modelo():
    pytest.importorskip("sklearn")
    if not MODELO.is_file():
        pytest.skip("sem ml/models/sob_efeito.joblib")
    sys.path.insert(0, str(ROOT / "ml"))
    esperado = {"perfume": "sem_efeito", "bebida": "sob_efeito", "ambiente": "sem_efeito"}
    for item in json.loads(RECORTES.read_text(encoding="utf-8")):
        status, corpo = responder(
            "POST",
            "/modelo/classificar",
            json.dumps(
                {
                    "sessao": item["origem"],
                    "attempt_id": f"demo-{item['id']}",
                    "blow_start_s": item["blow_start_s"],
                    "blow_end_s": item["blow_end_s"],
                    "leituras": item["leituras"],
                }
            ).encode(),
            MODELO,
        )
        assert status == 200, corpo
        assert corpo["status"] == "classificado"
        assert corpo["prediction"] == esperado[item["id"]]
