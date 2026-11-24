"""Fixture ``pg``: um schema temporário com o banco da coleta (``applications/db/01-schema.sql``).

Os testes de banco só rodam com ``PG_DSN`` definido, por exemplo::

    docker run --rm -d --name pg-teste -e POSTGRES_PASSWORD=t -p 55432:5432 postgres:16
    PG_DSN=postgresql://postgres:t@localhost:55432/postgres python -m pytest
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

ESQUEMA = Path(__file__).resolve().parents[2] / "applications" / "db" / "01-schema.sql"


def pytest_configure(config):
    config.addinivalue_line("markers", "integracao: precisa de um Postgres (PG_DSN)")


@pytest.fixture
def pg():
    dsn = os.environ.get("PG_DSN")
    if not dsn:
        pytest.skip("defina PG_DSN para rodar os testes de banco")
    import psycopg

    nome = f"t_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(dsn, autocommit=True) as con:
        con.execute(f"CREATE SCHEMA {nome}")
        con.execute(f"SET search_path TO {nome}")
        con.execute(ESQUEMA.read_text(encoding="utf-8"))
        try:
            yield con
        finally:
            con.execute(f"DROP SCHEMA {nome} CASCADE")
