"""Tópicos e mensagens MQTT trocados entre a ponte, o simulador e o ingestor.

Cada placa publica em ``mq3/<placa>/<tipo>``. As mensagens são JSON; valores
ausentes do DHT11 vão como ``null``.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from coleta.serial_proto import Leitura

TIPOS_TOPICO = ("rodada", "leituras", "eventos", "status")
TIPOS_EVENTO = ("sopro_inicio", "sopro_fim", "rodada_fim")
ORIGENS_MQTT = ("ponte", "simulador")


def topico(placa: str, tipo: str) -> str:
    """Tópico de um tipo de mensagem de uma placa."""
    if tipo not in TIPOS_TOPICO:
        raise ValueError(f"tipo de tópico desconhecido: {tipo!r}; use um de {TIPOS_TOPICO}")
    return f"mq3/{placa}/{tipo}"


def payload_rodada(
    rodada_id: str,
    placa: str,
    caso: str,
    participante: str,
    inicio: datetime,
    arquivo_sessao: str,
    origem: str,
) -> dict:
    """Descrição da rodada: publicada retida, para quem assinar depois também saber."""
    if origem not in ORIGENS_MQTT:
        raise ValueError(f"origem desconhecida: {origem!r}; use uma de {ORIGENS_MQTT}")
    return {
        "rodada_id": rodada_id,
        "placa": placa,
        "caso": caso,
        "participante": participante,
        "inicio": inicio.isoformat(),
        "arquivo_sessao": arquivo_sessao,
        "origem": origem,
    }


def payload_leitura(rodada_id: str, leitura: Leitura) -> dict:
    """Uma leitura, com os campos do CSV do firmware."""
    return {"rodada_id": rodada_id, **leitura.como_dict()}


def payload_evento(rodada_id: str, tipo: str, t_ms: int, sha256: Optional[str] = None) -> dict:
    """Início ou fim de sopro, ou fim da rodada (com o SHA-256 do CSV gravado)."""
    if tipo not in TIPOS_EVENTO:
        raise ValueError(f"tipo de evento desconhecido: {tipo!r}; use um de {TIPOS_EVENTO}")
    evento = {"rodada_id": rodada_id, "tipo": tipo, "t_ms": t_ms}
    if sha256 is not None:
        evento["sha256"] = sha256
    return evento


def codificar(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def decodificar(dados: bytes) -> dict:
    """JSON de uma mensagem; ``ValueError`` se não for um objeto JSON válido."""
    try:
        payload = json.loads(dados.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ValueError(f"mensagem não é JSON válido: {erro}") from erro
    if not isinstance(payload, dict):
        raise ValueError("mensagem JSON não é um objeto")
    return payload
