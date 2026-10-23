"""Esquema dos dados e validação.

Os dados reais chegam em dois tipos de arquivo:

- **leituras** (``data/raw/readings/*.csv``): uma linha por leitura dos sensores,
  gravada pelo sistema de aquisição durante cada tentativa de sopro;
- **tentativas** (``data/raw/attempts.csv``): uma linha por tentativa, preenchida
  por quem conduz o experimento, com participante, sessão e condição.

O rótulo de cada tentativa vem da **condição experimental** (o que foi feito
antes do sopro), nunca do valor dos sensores.

A validação reúne todos os problemas encontrados e os mostra de uma vez. Os
números de linha nas mensagens contam o cabeçalho do CSV como linha 1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PHASES = ("before", "blow", "after")
SENSOR_COLUMNS = ["mq3_raw", "mq135_raw", "temperature_c", "humidity_pct"]
READING_COLUMNS = ["timestamp", "attempt_id", "phase", *SENSOR_COLUMNS]

ATTEMPT_COLUMNS = ["attempt_id", "participant_id", "session_id", "condition"]
OPTIONAL_ATTEMPT_COLUMNS = ["reference_mg_l", "notes"]

CLASSES = ("sem_alcool", "externo", "bebida")
CONDITIONS = {
    "clean": "sem_alcool",
    "perfume": "externo",
    "alcohol70_spray": "externo",
    "alcohol70_hands": "externo",
    "mouthwash": "externo",
    "alcohol_cup": "externo",
    "drink": "bebida",
    "drink_perfume": "bebida",
}

_TZ_SUFFIX = r"(?:Z|[+-]\d{2}:?\d{2})$"


class DataValidationError(ValueError):
    """Erro com a lista de problemas encontrados nos dados."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("dados inválidos:\n" + "\n".join(f"  - {p}" for p in problems))


def validate_readings(df: pd.DataFrame) -> pd.DataFrame:
    """Valida e converte os tipos de uma tabela de leituras.

    ``mq3_raw`` é obrigatório em toda linha. ``mq135_raw``, ``temperature_c`` e
    ``humidity_pct`` podem ficar vazios (por exemplo, quando o DHT11 falha ou é
    lido com frequência menor que os MQ). Colunas extras são mantidas.

    Returns:
        Uma cópia com ``timestamp`` em UTC, sensores como float e linhas
        ordenadas por tentativa e horário.

    Raises:
        DataValidationError: com todos os problemas encontrados.
    """
    _require_columns(df, READING_COLUMNS)
    out = df.copy()
    problems: list[str] = []

    timestamps = _parse_timestamps(out["timestamp"], problems)
    if timestamps is not None:
        out["timestamp"] = timestamps

    out["attempt_id"] = _required_text(out["attempt_id"], "attempt_id", problems)

    phase = out["phase"].astype("string").str.strip().str.lower()
    bad_phase = _as_bool(~phase.isin(PHASES))
    if bad_phase.any():
        problems.append(_describe(f"phase deve ser um de {list(PHASES)}", bad_phase))
    out["phase"] = phase

    for column in SENSOR_COLUMNS:
        values = pd.to_numeric(out[column], errors="coerce")
        not_numeric = out[column].notna() & values.isna()
        if not_numeric.any():
            problems.append(_describe(f"{column} não numérico", not_numeric))
        out[column] = values.astype(float)
    if out["mq3_raw"].isna().any():
        problems.append(_describe("mq3_raw vazio", out["mq3_raw"].isna()))

    if not problems:
        duplicated = out.duplicated(subset=["attempt_id", "timestamp"], keep=False)
        if duplicated.any():
            problems.append(_describe("leituras repetidas (mesmo attempt_id e timestamp)", duplicated))

    if problems:
        raise DataValidationError(problems)
    return out.sort_values(["attempt_id", "timestamp"], kind="stable").reset_index(drop=True)


def validate_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Valida a tabela de tentativas e acrescenta a coluna ``target``.

    ``target`` é a classe derivada de ``condition`` pelo dicionário ``CONDITIONS``.
    ``reference_mg_l`` (leitura de um etilômetro de referência) é opcional.

    Raises:
        DataValidationError: com todos os problemas encontrados.
    """
    _require_columns(df, ATTEMPT_COLUMNS)
    out = df.copy()
    problems: list[str] = []

    for column in ("attempt_id", "participant_id", "session_id"):
        out[column] = _required_text(out[column], column, problems)

    condition = out["condition"].astype("string").str.strip().str.lower()
    bad_condition = _as_bool(~condition.isin(list(CONDITIONS)))
    if bad_condition.any():
        found = sorted(condition[bad_condition].dropna().unique())
        problems.append(
            _describe(f"condition desconhecida {found}; use uma de {sorted(CONDITIONS)}", bad_condition)
        )
    out["condition"] = condition

    if "reference_mg_l" in out.columns:
        reference = pd.to_numeric(out["reference_mg_l"], errors="coerce")
        bad = (out["reference_mg_l"].notna() & reference.isna()) | _as_bool(reference < 0)
        if bad.any():
            problems.append(_describe("reference_mg_l deve ser um número >= 0 ou vazio", bad))
        out["reference_mg_l"] = reference.astype(float)
    if "notes" in out.columns:
        out["notes"] = out["notes"].astype("string")

    duplicated = _as_bool(out["attempt_id"].duplicated(keep=False))
    if duplicated.any():
        problems.append(_describe("attempt_id repetido", duplicated))

    if problems:
        raise DataValidationError(problems)
    out["target"] = out["condition"].map(CONDITIONS).astype("string")
    return out.sort_values("attempt_id", kind="stable").reset_index(drop=True)


def check_consistency(readings: pd.DataFrame, attempts: pd.DataFrame) -> list[str]:
    """Confere se leituras e tentativas se correspondem.

    Leituras de uma tentativa não cadastrada são erro, porque ficariam sem rótulo.
    Tentativas cadastradas sem leituras viram aviso.

    Returns:
        Lista de avisos.
    """
    reading_ids = set(readings["attempt_id"])
    attempt_ids = set(attempts["attempt_id"])
    unregistered = sorted(reading_ids - attempt_ids)
    if unregistered:
        raise DataValidationError(
            [f"leituras de tentativas que não estão em attempts.csv: {unregistered[:10]}"]
        )
    without_readings = sorted(attempt_ids - reading_ids)
    if without_readings:
        return [f"tentativas sem leituras (ignoradas): {without_readings[:10]}"]
    return []


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise DataValidationError([f"colunas obrigatórias ausentes: {', '.join(missing)}"])
    if df.empty:
        raise DataValidationError(["nenhuma linha encontrada"])


def _required_text(values: pd.Series, name: str, problems: list[str]) -> pd.Series:
    text = values.astype("string").str.strip()
    empty = _as_bool(text.isna() | (text == ""))
    if empty.any():
        problems.append(_describe(f"{name} vazio", empty))
    return text


def _parse_timestamps(values: pd.Series, problems: list[str]) -> pd.Series | None:
    """Converte para UTC exigindo fuso explícito; horários sem fuso são ambíguos."""
    if isinstance(values.dtype, pd.DatetimeTZDtype):
        return values.dt.tz_convert("UTC")

    text = values.astype("string").str.strip()
    has_tz = _as_bool(text.str.contains(_TZ_SUFFIX, regex=True))
    if not has_tz.all():
        problems.append(
            _describe(
                "timestamp vazio ou sem fuso horário "
                "(use ISO 8601 com offset, ex.: 2026-10-20T14:00:00-03:00)",
                ~has_tz,
            )
        )
        return None

    parsed = pd.to_datetime(text, utc=True, format="ISO8601", errors="coerce")
    if parsed.isna().any():
        problems.append(_describe("timestamp em formato inválido", parsed.isna()))
        return None
    return parsed


def _as_bool(mask: pd.Series) -> pd.Series:
    return mask.fillna(False).astype(bool)


def _describe(message: str, mask: pd.Series) -> str:
    positions = np.flatnonzero(mask.to_numpy(dtype=bool))
    lines = [int(p) + 2 for p in positions[:5]]
    suffix = " ..." if len(positions) > 5 else ""
    return f"{message}: {len(positions)} linha(s), ex.: linhas {lines}{suffix}"
