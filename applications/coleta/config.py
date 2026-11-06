"""Configuração por variáveis de ambiente, com padrões para rodar no notebook."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    pg_dsn: str = "postgresql://mq3:mq3@localhost:5432/mq3"
    placa: str = "placa01"

    @classmethod
    def do_ambiente(cls) -> "Config":
        padrao = cls()
        return cls(
            mqtt_host=os.environ.get("MQTT_HOST", padrao.mqtt_host),
            mqtt_port=int(os.environ.get("MQTT_PORT", padrao.mqtt_port)),
            pg_dsn=os.environ.get("PG_DSN", padrao.pg_dsn),
            placa=os.environ.get("PLACA", padrao.placa),
        )
