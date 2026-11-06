"""Configuração por variáveis de ambiente, com padrões para rodar no notebook.

Sem ``PG_DSN`` definido, as ferramentas do host montam a conexão a partir do
``.env`` da raiz do repositório (o mesmo que o Docker Compose usa).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

ENV_REPOSITORIO = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class Config:
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    pg_dsn: str = "postgresql://mq3:mq3@localhost:5432/mq3"
    placa: str = "placa01"

    @classmethod
    def do_ambiente(cls, arquivo_env: Optional[Path] = None) -> "Config":
        padrao = cls()
        return cls(
            mqtt_host=os.environ.get("MQTT_HOST", padrao.mqtt_host),
            mqtt_port=int(os.environ.get("MQTT_PORT", padrao.mqtt_port)),
            pg_dsn=os.environ.get("PG_DSN") or _dsn_do_env(arquivo_env or ENV_REPOSITORIO) or padrao.pg_dsn,
            placa=os.environ.get("PLACA", padrao.placa),
        )


def _dsn_do_env(caminho: Path) -> Optional[str]:
    valores = _ler_env(caminho)
    if "POSTGRES_PASSWORD" not in valores:
        return None
    usuario = valores.get("POSTGRES_USER", "mq3")
    banco = valores.get("POSTGRES_DB", "mq3")
    return f"postgresql://{usuario}:{valores['POSTGRES_PASSWORD']}@localhost:5432/{banco}"


def _ler_env(caminho: Path) -> Dict[str, str]:
    if not caminho.exists():
        return {}
    valores = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, _, valor = linha.partition("=")
            valores[chave.strip()] = valor.strip()
    return valores
