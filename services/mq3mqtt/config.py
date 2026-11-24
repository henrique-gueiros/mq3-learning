"""Configuração lida do ambiente. Os padrões servem para rodar na máquina local."""

from __future__ import annotations

import os
import time
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


def connect_with_retry(database_url: str, attempts: int = 30, pause_s: float = 1.0):
    """Abre o banco em autocommit, tentando de novo enquanto o Postgres do Compose sobe."""
    import psycopg

    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return psycopg.connect(database_url, autocommit=True)
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(pause_s)
    assert last_error is not None
    raise last_error
