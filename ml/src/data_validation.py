"""Esquema do dataset e validação das leituras.

Toda leitura (real ou sintética) passa por ``validate_readings`` antes de ser usada.
A validação reúne todos os problemas encontrados e os mostra de uma vez, para que
a equipe consiga corrigir o arquivo sem precisar rodar várias vezes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["timestamp", "session_id", "sensor_raw", "label", "source"]
OPTIONAL_NUMERIC_COLUMNS = ["temperature_c", "humidity_pct"]
OPTIONAL_TEXT_COLUMNS = ["notes"]
VALID_LABELS = (0, 1)

_TZ_SUFFIX = r"(?:Z|[+-]\d{2}:?\d{2})$"


class DataValidationError(ValueError):
    """Erro com a lista de problemas encontrados nos dados."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("dados inválidos:\n" + "\n".join(f"  - {p}" for p in problems))


def validate_readings(df: pd.DataFrame, expected_source: str | None = None) -> pd.DataFrame:
    """Valida e converte os tipos de uma tabela de leituras.

    Args:
        df: tabela com as colunas de ``REQUIRED_COLUMNS`` (e, opcionalmente,
            ``temperature_c``, ``humidity_pct`` e ``notes``). Colunas extras são mantidas.
        expected_source: se informado, todas as linhas precisam ter esse ``source``
            (por exemplo ``"real"`` para os arquivos de ``data/raw/``).

    Returns:
        Uma cópia com ``timestamp`` em UTC, ``sensor_raw`` como float, ``label`` como
        inteiro anulável (``Int64``) e as linhas ordenadas por sessão e horário.

    Raises:
        DataValidationError: com todos os problemas encontrados. Os números de linha
            citados nas mensagens contam o cabeçalho do CSV como linha 1.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise DataValidationError([f"colunas obrigatórias ausentes: {', '.join(missing)}"])
    if df.empty:
        raise DataValidationError(["nenhuma leitura encontrada"])

    out = df.copy()
    problems: list[str] = []

    timestamps = _parse_timestamps(out["timestamp"], problems)
    if timestamps is not None:
        out["timestamp"] = timestamps

    for column in ("session_id", "source"):
        text = out[column].astype("string").str.strip()
        empty = _as_bool(text.isna() | (text == ""))
        if empty.any():
            problems.append(_describe(f"{column} vazio", empty))
        out[column] = text

    if expected_source is not None:
        wrong = _as_bool(out["source"] != expected_source)
        if wrong.any():
            found = sorted(out.loc[wrong, "source"].dropna().unique())
            problems.append(
                _describe(f"source deveria ser '{expected_source}', mas há {found}", wrong)
            )

    sensor = pd.to_numeric(out["sensor_raw"], errors="coerce")
    bad_sensor = sensor.isna() | ~np.isfinite(sensor)
    if bad_sensor.any():
        problems.append(_describe("sensor_raw vazio ou não numérico", bad_sensor))
    out["sensor_raw"] = sensor.astype(float)

    label = pd.to_numeric(out["label"], errors="coerce")
    bad_label = (out["label"].notna() & label.isna()) | (label.notna() & ~label.isin(VALID_LABELS))
    if bad_label.any():
        problems.append(_describe("label deve ser 0, 1 ou vazio", bad_label))
    else:
        out["label"] = label.astype("Int64")

    for column in OPTIONAL_NUMERIC_COLUMNS:
        if column in out.columns:
            values = pd.to_numeric(out[column], errors="coerce")
            bad = out[column].notna() & values.isna()
            if bad.any():
                problems.append(_describe(f"{column} não numérico", bad))
            out[column] = values.astype(float)

    for column in OPTIONAL_TEXT_COLUMNS:
        if column in out.columns:
            out[column] = out[column].astype("string")

    if not problems:
        duplicated = out.duplicated(subset=["session_id", "timestamp"], keep=False)
        if duplicated.any():
            problems.append(_describe("leituras repetidas (mesma session_id e timestamp)", duplicated))

    if problems:
        raise DataValidationError(problems)

    return out.sort_values(["session_id", "timestamp"], kind="stable").reset_index(drop=True)


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
