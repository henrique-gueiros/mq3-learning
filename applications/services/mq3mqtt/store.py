"""Gravação no PostgreSQL. Leituras repetidas (mesma placa, sessão e amostra) são ignoradas."""

from __future__ import annotations

import time
from typing import Any

import psycopg
from psycopg.rows import dict_row


def connect_with_retry(database_url: str, attempts: int = 30, pause_s: float = 1.0):
    """Abre o banco, tentando de novo enquanto o Postgres do Compose ainda sobe."""
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return psycopg.connect(database_url, autocommit=True, row_factory=dict_row)
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(pause_s)
    assert last_error is not None
    raise last_error


def insert_leitura(conn, placa: str, row: dict[str, Any]) -> bool:
    """Insere uma leitura. Devolve False se essa amostra já existia."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO leituras (
                placa, sessao, amostra, t_ms, mq3_raw, ppm, mq135_raw, mq135_mv,
                temperature_c, humidity_pct, alcool
            )
            VALUES (
                %(placa)s, %(sessao)s, %(amostra)s, %(t_ms)s, %(mq3_raw)s, %(ppm)s,
                %(mq135_raw)s, %(mq135_mv)s, %(temperature_c)s, %(humidity_pct)s, %(alcool)s
            )
            ON CONFLICT (placa, sessao, amostra) DO NOTHING
            RETURNING id
            """,
            {"placa": placa, **row},
        )
        return cur.fetchone() is not None


def insert_evento(conn, placa: str, row: dict[str, Any]) -> int | None:
    """Insere um sopro. Devolve o id, ou None se o mesmo instante já foi gravado."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO eventos (placa, sessao, evento, t_ms, attempt_id)
            VALUES (%(placa)s, %(sessao)s, %(evento)s, %(t_ms)s, %(attempt_id)s)
            ON CONFLICT (placa, sessao, evento, t_ms) DO NOTHING
            RETURNING id
            """,
            {"placa": placa, **row},
        )
        inserted = cur.fetchone()
    return None if inserted is None else int(inserted["id"])


def upsert_status(conn, placa: str, status: str) -> None:
    """Guarda o último online/offline publicado pela placa."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO status_placa (placa, status)
            VALUES (%s, %s)
            ON CONFLICT (placa) DO UPDATE
            SET status = EXCLUDED.status, atualizado_em = now()
            """,
            (placa, status),
        )


def evento_por_id(conn, evento_id: int) -> dict[str, Any] | None:
    """Busca um evento gravado pelo worker."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, placa, sessao, evento, t_ms, attempt_id
            FROM eventos
            WHERE id = %s
            """,
            (evento_id,),
        )
        return cur.fetchone()


def inicio_do_sopro(conn, placa: str, sessao: str, fim_t_ms: int) -> dict[str, Any] | None:
    """Acha o ``sopro_inicio`` ainda aberto imediatamente antes deste fim."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, t_ms, attempt_id
            FROM eventos AS inicio
            WHERE inicio.placa = %s
              AND inicio.sessao = %s
              AND inicio.evento = 'sopro_inicio'
              AND inicio.t_ms <= %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM eventos AS fim
                  WHERE fim.placa = inicio.placa
                    AND fim.sessao = inicio.sessao
                    AND fim.evento = 'sopro_fim'
                    AND fim.t_ms >= inicio.t_ms
                    AND fim.t_ms < %s
              )
            ORDER BY inicio.t_ms DESC
            LIMIT 1
            """,
            (placa, sessao, fim_t_ms, fim_t_ms),
        )
        return cur.fetchone()


def leituras_da_sessao(conn, placa: str, sessao: str) -> list[dict[str, Any]]:
    """Todas as leituras de uma sessão, na ordem do relógio da placa."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT amostra, t_ms, mq3_raw, ppm, mq135_raw, mq135_mv,
                   temperature_c, humidity_pct, alcool
            FROM leituras
            WHERE placa = %s AND sessao = %s
            ORDER BY t_ms, amostra
            """,
            (placa, sessao),
        )
        return list(cur.fetchall())


def insert_resultado(conn, placa: str, resultado: dict[str, Any]) -> None:
    """Guarda a resposta publicada em ``mq3/<placa>/resultado``."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO resultados (
                placa, sessao, attempt_id, status, prediction,
                prob_sem_efeito, prob_sob_efeito, detalhe
            )
            VALUES (
                %(placa)s, %(sessao)s, %(attempt_id)s, %(status)s, %(prediction)s,
                %(prob_sem_efeito)s, %(prob_sob_efeito)s, %(detalhe)s
            )
            """,
            {"placa": placa, **resultado},
        )
