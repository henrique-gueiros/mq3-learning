"""Gravação no PostgreSQL. Todas as escritas são idempotentes: repetir uma
mensagem (reconexão do MQTT, ingestor reiniciado) não duplica nada."""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

import psycopg

_COLUNAS_LEITURA = (
    "rodada_id", "amostra", "t_ms", "mq3_raw", "ppm", "mq135_raw",
    "mq135_mv", "temperature_c", "humidity_pct", "alcool",
)
_INSERIR_LEITURA = (
    f"INSERT INTO leituras ({', '.join(_COLUNAS_LEITURA)}) "
    f"VALUES ({', '.join(f'%({c})s' for c in _COLUNAS_LEITURA)}) "
    "ON CONFLICT DO NOTHING"
)


def garantir_rodada(con: psycopg.Connection, rodada_id: str, placa: str) -> None:
    """Cria um esqueleto da rodada se ela ainda não existir (leitura chegou antes)."""
    with con.transaction():
        con.execute(
            "INSERT INTO rodadas (id, placa) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (rodada_id, placa),
        )


def gravar_rodada(con: psycopg.Connection, rodada: dict) -> None:
    """Cria ou completa a rodada com os dados da mensagem ``rodada``."""
    with con.transaction():
        con.execute(
            """
            INSERT INTO rodadas (id, placa, caso, participante, inicio, arquivo_sessao, origem, sha256)
            VALUES (%(rodada_id)s, %(placa)s, %(caso)s, %(participante)s, %(inicio)s,
                    %(arquivo_sessao)s, %(origem)s, %(sha256)s)
            ON CONFLICT (id) DO UPDATE SET
                placa = EXCLUDED.placa,
                caso = EXCLUDED.caso,
                participante = EXCLUDED.participante,
                inicio = EXCLUDED.inicio,
                arquivo_sessao = EXCLUDED.arquivo_sessao,
                origem = EXCLUDED.origem,
                sha256 = coalesce(EXCLUDED.sha256, rodadas.sha256)
            """,
            {"sha256": None, **rodada},
        )


def gravar_leitura(con: psycopg.Connection, leitura: dict) -> bool:
    """Grava uma leitura; ``False`` se ela já estava no banco."""
    with con.transaction():
        cursor = con.execute(_INSERIR_LEITURA, leitura)
    return cursor.rowcount == 1


def gravar_evento(con: psycopg.Connection, evento: dict) -> None:
    """Grava um evento; ``rodada_fim`` também fecha a rodada e guarda o SHA-256 do CSV."""
    with con.transaction():
        con.execute(
            "INSERT INTO eventos (rodada_id, tipo, t_ms) VALUES (%(rodada_id)s, %(tipo)s, %(t_ms)s) "
            "ON CONFLICT DO NOTHING",
            evento,
        )
        if evento["tipo"] == "rodada_fim":
            con.execute(
                "UPDATE rodadas SET fim = now(), sha256 = coalesce(%s, sha256) WHERE id = %s",
                (evento.get("sha256"), evento["rodada_id"]),
            )


def rodada_por_sha(con: psycopg.Connection, sha256: str) -> Optional[str]:
    """Id da rodada que já tem esse CSV, se houver."""
    linha = con.execute("SELECT id FROM rodadas WHERE sha256 = %s", (sha256,)).fetchone()
    return None if linha is None else str(linha[0])


def importar_rodada(
    con: psycopg.Connection,
    rodada: dict,
    leituras: Iterable[dict],
    sopros: List[Tuple[int, Optional[int]]],
) -> str:
    """Grava uma rodada inteira (dados, leituras e sopros) numa única transação."""
    rodada_id = rodada["rodada_id"]
    with con.transaction():
        gravar_rodada(con, rodada)
        with con.cursor() as cursor:
            cursor.executemany(_INSERIR_LEITURA, [{**l, "rodada_id": rodada_id} for l in leituras])
        for inicio_ms, fim_ms in sopros:
            gravar_evento(con, {"rodada_id": rodada_id, "tipo": "sopro_inicio", "t_ms": inicio_ms})
            if fim_ms is not None:
                gravar_evento(con, {"rodada_id": rodada_id, "tipo": "sopro_fim", "t_ms": fim_ms})
    return rodada_id
