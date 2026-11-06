"""Rodadas montadas à mão para os testes de banco; não representam o sensor real."""

from __future__ import annotations

import uuid
from typing import Iterable, Optional

from coleta import banco


def nova_rodada(con, caso: str = "perfume", origem: str = "ponte") -> str:
    rodada_id = str(uuid.uuid4())
    banco.gravar_rodada(con, {
        "rodada_id": rodada_id, "placa": "placa01", "caso": caso, "participante": "p01",
        "inicio": "2026-11-05T14:00:00+00:00", "arquivo_sessao": "a.csv", "origem": origem,
    })
    return rodada_id


def payload(rodada_id: str, amostra: int, t_ms: int, mq3: int, mq135: int = 450,
            umidade: Optional[float] = 50.0) -> dict:
    return {
        "rodada_id": rodada_id, "amostra": amostra, "t_ms": t_ms, "mq3_raw": mq3, "ppm": 0.4,
        "mq135_raw": mq135, "mq135_mv": 520, "temperature_c": 30.0, "humidity_pct": umidade, "alcool": 0,
    }


def gravar_serie(con, rodada_id: str, pontos: Iterable[tuple]) -> None:
    """``pontos``: (t_ms, mq3) ou (t_ms, mq3, mq135)."""
    for amostra, ponto in enumerate(pontos, start=1):
        banco.gravar_leitura(con, payload(rodada_id, amostra, *ponto))


def sopro(con, rodada_id: str, inicio_ms: int, fim_ms: Optional[int] = None) -> None:
    banco.gravar_evento(con, {"rodada_id": rodada_id, "tipo": "sopro_inicio", "t_ms": inicio_ms})
    if fim_ms is not None:
        banco.gravar_evento(con, {"rodada_id": rodada_id, "tipo": "sopro_fim", "t_ms": fim_ms})
