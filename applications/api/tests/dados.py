"""Rodadas montadas à mão para os testes da API; não representam o sensor real."""

from __future__ import annotations

import uuid
from typing import Iterable, Optional

from coleta import banco


def rodada(con, caso: str, participante: str = "p01", origem: str = "ponte",
           inicio: str = "2026-11-05T14:00:00+00:00") -> str:
    rodada_id = str(uuid.uuid4())
    banco.gravar_rodada(con, {
        "rodada_id": rodada_id, "placa": "placa01", "caso": caso, "participante": participante,
        "inicio": inicio, "arquivo_sessao": f"{caso}.csv", "origem": origem,
    })
    return rodada_id


def leituras(con, rodada_id: str, pontos: Iterable[tuple]) -> None:
    """``pontos``: (t_ms, mq3, mq135, umidade[, ppm])."""
    for amostra, ponto in enumerate(pontos, start=1):
        t_ms, mq3, mq135, umidade, *resto = ponto
        banco.gravar_leitura(con, {
            "rodada_id": rodada_id, "amostra": amostra, "t_ms": t_ms, "mq3_raw": mq3,
            "ppm": resto[0] if resto else 0.5, "mq135_raw": mq135, "mq135_mv": 500,
            "temperature_c": 30.0, "humidity_pct": umidade, "alcool": 0,
        })


def sopro(con, rodada_id: str, inicio_ms: int, fim_ms: Optional[int] = None) -> None:
    banco.gravar_evento(con, {"rodada_id": rodada_id, "tipo": "sopro_inicio", "t_ms": inicio_ms})
    if fim_ms is not None:
        banco.gravar_evento(con, {"rodada_id": rodada_id, "tipo": "sopro_fim", "t_ms": fim_ms})


def constante(n: int, mq3: int, mq135: int, umidade: float, passo_ms: int = 1000) -> list:
    """``n`` leituras iguais, uma por segundo."""
    return [(i * passo_ms, mq3, mq135, umidade) for i in range(n)]
