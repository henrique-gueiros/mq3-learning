"""Configuração lida do ambiente. Os padrões servem para rodar na máquina local."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Endereços do broker, do banco e do arquivo do modelo."""

    mqtt_host: str
    mqtt_port: int
    database_url: str
    model_path: Path


def broker_recusou(reason_code) -> bool:
    """True quando o Mosquitto recusou a conexão do cliente."""
    if hasattr(reason_code, "is_failure"):
        return bool(reason_code.is_failure)
    return int(reason_code) != 0


def load_settings() -> Settings:
    """Lê MQTT_HOST, MQTT_PORT, DATABASE_URL e MODEL_PATH."""
    return Settings(
        mqtt_host=os.environ.get("MQTT_HOST", "localhost"),
        mqtt_port=int(os.environ.get("MQTT_PORT", "1883")),
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://mq3:mq3@localhost:5432/mq3"
        ),
        model_path=Path(
            os.environ.get("MODEL_PATH", str(REPO_ROOT / "ml" / "models" / "sob_efeito.joblib"))
        ),
    )
