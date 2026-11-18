"""Mensagens MQTT no formato do CSV do firmware.

A placa entra no tópico (``mq3/<placa>/leituras``). O corpo da mensagem traz a
sessão e as mesmas colunas do CSV. ``ppm`` e ``alcool`` viajam juntos para o
banco não perder o arquivo original; o modelo não usa essas colunas.
"""

from __future__ import annotations

import json
from typing import Any

TOPIC_KINDS = ("leituras", "eventos", "status", "resultado", "sopro_pronto")
EVENTOS = ("sopro_inicio", "sopro_fim")
STATUS = ("online", "offline")
CSV_COLUMNS = (
    "amostra",
    "t_ms",
    "mq3_raw",
    "ppm",
    "mq135_raw",
    "mq135_mv",
    "temperature_c",
    "humidity_pct",
    "alcool",
)


def topic(placa: str, kind: str) -> str:
    """Monta um tópico ``mq3/<placa>/<kind>``."""
    if kind not in TOPIC_KINDS:
        raise ValueError(f"tipo de tópico desconhecido: {kind}")
    _placa(placa)
    return f"mq3/{placa}/{kind}"


def parse_topic(topic_name: str) -> tuple[str, str]:
    """Separa a placa e o tipo a partir de um tópico publicado."""
    parts = topic_name.split("/")
    if len(parts) != 3 or parts[0] != "mq3" or parts[2] not in TOPIC_KINDS:
        raise ValueError(f"tópico fora do combinado: {topic_name}")
    return _placa(parts[1]), parts[2]


def normalizar_sessao(sessao: str) -> str:
    """Nome do CSV da sessão, sem pasta. Acrescenta ``.csv`` se faltar."""
    name = str(sessao).strip()
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise ValueError(f"sessao inválida: {sessao!r}")
    if not name.lower().endswith(".csv"):
        name = f"{name}.csv"
    return name


def loads(payload: bytes | str) -> dict[str, Any]:
    """Decodifica o JSON de uma mensagem MQTT."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("mensagem MQTT não é JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("mensagem MQTT precisa ser um objeto JSON")
    return data


def dumps(payload: dict[str, Any]) -> str:
    """Codifica um objeto para publicar no broker."""
    return json.dumps(payload, ensure_ascii=False)


def parse_leitura(data: dict[str, Any]) -> dict[str, Any]:
    """Confere uma leitura e devolve os campos prontos para o banco."""
    row = {
        "sessao": normalizar_sessao(str(data.get("sessao", ""))),
        "amostra": _int(data.get("amostra"), "amostra"),
        "t_ms": _int(data.get("t_ms"), "t_ms"),
        "mq3_raw": _required_float(data.get("mq3_raw"), "mq3_raw"),
        "ppm": _optional_float(data.get("ppm")),
        "mq135_raw": _optional_float(data.get("mq135_raw")),
        "mq135_mv": _optional_float(data.get("mq135_mv")),
        "temperature_c": _optional_float(data.get("temperature_c")),
        "humidity_pct": _optional_float(data.get("humidity_pct")),
        "alcool": _optional_int(data.get("alcool")),
    }
    if row["t_ms"] < 0 or row["amostra"] < 0:
        raise ValueError("amostra e t_ms não podem ser negativos")
    return row


def leitura_de_linha_csv(row: dict[str, str], sessao: str) -> dict[str, Any]:
    """Converte uma linha do CSV do firmware na mensagem de leitura."""
    payload: dict[str, Any] = {"sessao": sessao}
    for column in CSV_COLUMNS:
        payload[column] = row.get(column, "")
    return parse_leitura(payload)


def parse_evento(data: dict[str, Any]) -> dict[str, Any]:
    """Confere ``sopro_inicio`` ou ``sopro_fim``."""
    evento = str(data.get("evento", "")).strip()
    if evento not in EVENTOS:
        raise ValueError(f"evento desconhecido: {evento!r}; use um de {EVENTOS}")
    attempt_id = data.get("attempt_id")
    if attempt_id is not None:
        attempt_id = str(attempt_id).strip() or None
    return {
        "sessao": normalizar_sessao(str(data.get("sessao", ""))),
        "evento": evento,
        "t_ms": _int(data.get("t_ms"), "t_ms"),
        "attempt_id": attempt_id,
    }


def parse_status(data: dict[str, Any]) -> str:
    """Confere ``online`` ou ``offline``."""
    status = str(data.get("status", "")).strip()
    if status not in STATUS:
        raise ValueError(f"status desconhecido: {status!r}")
    return status


def parse_sopro_pronto(data: dict[str, Any]) -> dict[str, Any]:
    """Aviso interno do worker: o sopro já está gravado no banco."""
    return {
        "sessao": normalizar_sessao(str(data.get("sessao", ""))),
        "t_ms": _int(data.get("t_ms"), "t_ms"),
        "evento_id": _int(data.get("evento_id"), "evento_id"),
    }


def _placa(placa: str) -> str:
    name = str(placa).strip()
    if not name or "/" in name or "+" in name or "#" in name:
        raise ValueError(f"placa inválida: {placa!r}")
    return name


def _int(value: Any, field: str) -> int:
    if value is None or value == "":
        raise ValueError(f"{field} é obrigatório")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} não é inteiro") from exc


def _required_float(value: Any, field: str) -> float:
    if value is None or value == "":
        raise ValueError(f"{field} é obrigatório")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} não é numérico") from exc


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
