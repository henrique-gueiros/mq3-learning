"""Esquema dos dados e validação.

Os dados reais chegam em dois tipos de arquivo:

- **sessões** (``data/raw/sessions/*.csv``): os CSVs gravados pelo firmware da
  ESP32, sem alteração. Cada arquivo é uma sessão (do ligar ao desligar da placa),
  com uma leitura por linha e o tempo em ``t_ms`` (milissegundos desde a partida).
- **tentativas** (``data/raw/attempts.csv``): uma linha por tentativa de sopro,
  preenchida por quem conduz o experimento: em qual sessão, em que segundo o
  sopro começou, quem soprou e qual era a condição.

O rótulo de cada tentativa vem da **condição experimental**, nunca do valor dos
sensores. Por isso as colunas ``alcool`` e ``ppm`` do firmware (derivadas do
próprio MQ-3) nunca são usadas como rótulo nem como feature.

A validação reúne todos os problemas encontrados e os mostra de uma vez. Os
números de linha nas mensagens contam o cabeçalho do CSV como linha 1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SENSOR_COLUMNS = ["mq3_raw", "mq135_raw", "temperature_c", "humidity_pct"]
READING_COLUMNS = ["t_ms", *SENSOR_COLUMNS]
UNUSED_FIRMWARE_COLUMNS = ["amostra", "ppm", "mq135_mv", "alcool"]

ATTEMPT_COLUMNS = ["attempt_id", "session_file", "participant_id", "condition", "blow_start_s"]
OPTIONAL_ATTEMPT_COLUMNS = ["blow_end_s", "reference_mg_l", "notes"]

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


class DataValidationError(ValueError):
    """Erro com a lista de problemas encontrados nos dados."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("dados inválidos:\n" + "\n".join(f"  - {p}" for p in problems))


def validate_readings(df: pd.DataFrame) -> pd.DataFrame:
    """Valida e converte os tipos de um CSV de sessão do firmware.

    ``t_ms`` e ``mq3_raw`` são obrigatórios em toda linha. ``mq135_raw``,
    ``temperature_c`` e ``humidity_pct`` podem ficar vazios (o DHT11 só responde
    alguns segundos depois da partida). Colunas extras são mantidas.

    Returns:
        Uma cópia com os sensores como float, ``t_ms`` como inteiro e as linhas
        ordenadas por ``t_ms``.

    Raises:
        DataValidationError: com todos os problemas encontrados.
    """
    _require_columns(df, READING_COLUMNS)
    out = df.copy()
    problems: list[str] = []

    t_ms = pd.to_numeric(out["t_ms"], errors="coerce")
    bad_time = t_ms.isna() | _as_bool(t_ms < 0)
    if bad_time.any():
        problems.append(_describe("t_ms vazio, negativo ou não numérico", bad_time))

    for column in SENSOR_COLUMNS:
        values = pd.to_numeric(out[column], errors="coerce")
        not_numeric = out[column].notna() & values.isna()
        if not_numeric.any():
            problems.append(_describe(f"{column} não numérico", not_numeric))
        out[column] = values.astype(float)
    if out["mq3_raw"].isna().any():
        problems.append(_describe("mq3_raw vazio", out["mq3_raw"].isna()))

    if not bad_time.any():
        out["t_ms"] = t_ms.astype("int64")
        duplicated = out["t_ms"].duplicated(keep=False)
        if duplicated.any():
            problems.append(_describe("t_ms repetido", duplicated))

    if problems:
        raise DataValidationError(problems)
    return out.sort_values("t_ms", kind="stable").reset_index(drop=True)


def validate_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Valida a tabela de tentativas e acrescenta a coluna ``target``.

    ``blow_start_s`` é o segundo da sessão (``t_ms / 1000``) em que o sopro
    começou. ``blow_end_s`` é opcional; sem ele, o sopro dura
    ``features.DEFAULT_BLOW_SECONDS``. ``target`` é a classe derivada de
    ``condition`` pelo dicionário ``CONDITIONS``.

    Raises:
        DataValidationError: com todos os problemas encontrados.
    """
    _require_columns(df, ATTEMPT_COLUMNS)
    out = df.copy()
    problems: list[str] = []

    for column in ("attempt_id", "session_file", "participant_id"):
        out[column] = _required_text(out[column], column, problems)
    without_extension = _as_bool(~out["session_file"].str.lower().str.endswith(".csv"))
    out.loc[without_extension, "session_file"] = out.loc[without_extension, "session_file"] + ".csv"

    condition = out["condition"].astype("string").str.strip().str.lower()
    bad_condition = _as_bool(~condition.isin(list(CONDITIONS)))
    if bad_condition.any():
        found = sorted(condition[bad_condition].dropna().unique())
        problems.append(
            _describe(f"condition desconhecida {found}; use uma de {sorted(CONDITIONS)}", bad_condition)
        )
    out["condition"] = condition

    start = pd.to_numeric(out["blow_start_s"], errors="coerce")
    bad_start = start.isna() | _as_bool(start < 0)
    if bad_start.any():
        problems.append(_describe("blow_start_s vazio, negativo ou não numérico", bad_start))
    out["blow_start_s"] = start.astype(float)

    if "blow_end_s" in out.columns:
        end = pd.to_numeric(out["blow_end_s"], errors="coerce")
        bad_end = (out["blow_end_s"].notna() & end.isna()) | _as_bool(end <= start)
        if bad_end.any():
            problems.append(_describe("blow_end_s deve ser maior que blow_start_s ou vazio", bad_end))
        out["blow_end_s"] = end.astype(float)

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
    """Confere se tentativas e sessões se correspondem.

    Uma tentativa que aponta para um arquivo de sessão inexistente é erro.
    Sessões sem nenhuma tentativa cadastrada viram aviso (ficam de fora).

    Returns:
        Lista de avisos.
    """
    sessions = set(readings["session_file"])
    missing = sorted(set(attempts["session_file"]) - sessions)
    if missing:
        raise DataValidationError(
            [f"attempts.csv cita sessões que não estão em data/raw/sessions/: {missing[:10]}"]
        )
    unused = sorted(sessions - set(attempts["session_file"]))
    if unused:
        return [f"sessões sem tentativas cadastradas em attempts.csv (ignoradas): {unused[:10]}"]
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


def _as_bool(mask: pd.Series) -> pd.Series:
    return mask.fillna(False).astype(bool)


def _describe(message: str, mask: pd.Series) -> str:
    positions = np.flatnonzero(mask.to_numpy(dtype=bool))
    lines = [int(p) + 2 for p in positions[:5]]
    suffix = " ..." if len(positions) > 5 else ""
    return f"{message}: {len(positions)} linha(s), ex.: linhas {lines}{suffix}"
