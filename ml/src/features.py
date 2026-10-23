"""Transforma as leituras de cada tentativa de sopro em uma linha de features.

Para cada sensor (``mq3``, ``mq135``, ``humidity``, ``temperature``):

- ``<sensor>_before``: mediana na fase ``before`` (o ambiente antes do sopro);
- ``<sensor>_peak``: máximo nas fases ``blow`` e ``after``;
- ``<sensor>_rise``: ``peak - before`` (quanto subiu com o sopro);
- ``<sensor>_peak_time_s``: segundos entre o início do sopro e o pico;
- ``<sensor>_recovery_s``: segundos entre o pico e a volta para menos da
  metade da subida (vazio se não voltou ou se não subiu).

Features que combinam sensores:

- ``mq135_mq3_rise_ratio``: subida do MQ-135 dividida pela subida do MQ-3
  (a "assinatura" do gás);
- ``mq3_humidity_peak_lag_s``: atraso entre o pico do MQ-3 e o pico de umidade
  (se o álcool subiu junto com o sopro).

Essas features são o ponto de partida; devem ser revistas depois da análise
exploratória das leituras reais.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SENSORS = {
    "mq3": "mq3_raw",
    "mq135": "mq135_raw",
    "humidity": "humidity_pct",
    "temperature": "temperature_c",
}
_STATS = ("before", "peak", "rise", "peak_time_s", "recovery_s")
_MIN_RISE = 1e-9

SENSOR_GROUPS = {
    "mq3": [f"mq3_{s}" for s in _STATS],
    "mq135": [f"mq135_{s}" for s in _STATS] + ["mq135_mq3_rise_ratio"],
    "dht11": [f"humidity_{s}" for s in _STATS]
    + [f"temperature_{s}" for s in _STATS]
    + ["mq3_humidity_peak_lag_s"],
}

SENSOR_SETS = {
    "mq3": ["mq3"],
    "mq3+mq135": ["mq3", "mq135"],
    "mq3+dht11": ["mq3", "dht11"],
    "mq3+mq135+dht11": ["mq3", "mq135", "dht11"],
}

TASKS = {
    "3classes": "sem_alcool, externo ou bebida",
    "etapa1": "há álcool? (alcool ou sem_alcool)",
    "etapa2": "de onde vem o álcool? (bebida ou externo), só tentativas com álcool",
}


def feature_columns(sensor_set: str) -> list[str]:
    """Colunas de features usadas por um conjunto de sensores de ``SENSOR_SETS``."""
    if sensor_set not in SENSOR_SETS:
        raise ValueError(f"conjunto de sensores desconhecido: {sensor_set}; use um de {list(SENSOR_SETS)}")
    return [col for group in SENSOR_SETS[sensor_set] for col in SENSOR_GROUPS[group]]


def all_feature_columns() -> list[str]:
    return feature_columns("mq3+mq135+dht11")


def compute_features(readings: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Calcula uma linha de features por ``attempt_id``.

    Tentativas sem leitura do MQ-3 na fase ``before`` ou na fase ``blow`` são
    descartadas, porque não dá para comparar o antes com o sopro.

    Returns:
        ``(features, avisos)``; ``features`` tem a coluna ``attempt_id`` e as
        colunas de ``all_feature_columns()``.
    """
    rows: list[dict] = []
    skipped: list[str] = []
    for attempt_id, attempt in readings.groupby("attempt_id", sort=True):
        before = attempt[attempt["phase"] == "before"]
        window = attempt[attempt["phase"].isin(["blow", "after"])]
        blow = attempt[attempt["phase"] == "blow"]
        if before["mq3_raw"].isna().all() or blow["mq3_raw"].isna().all():
            skipped.append(str(attempt_id))
            continue

        blow_start = blow["timestamp"].min()
        row: dict = {"attempt_id": attempt_id}
        for name, column in SENSORS.items():
            row.update(_sensor_features(name, before[column], window, column, blow_start))

        row["mq135_mq3_rise_ratio"] = _safe_ratio(row["mq135_rise"], row["mq3_rise"])
        row["mq3_humidity_peak_lag_s"] = row["mq3_peak_time_s"] - row["humidity_peak_time_s"]
        rows.append(row)

    warnings = []
    if skipped:
        warnings.append(f"tentativas sem MQ-3 antes ou durante o sopro (descartadas): {skipped[:10]}")
    columns = ["attempt_id", *all_feature_columns()]
    features = pd.DataFrame(rows, columns=columns)
    return features, warnings


def build_dataset(features: pd.DataFrame, attempts: pd.DataFrame) -> pd.DataFrame:
    """Junta as features com participante, sessão, condição e classe de cada tentativa."""
    meta = ["attempt_id", "participant_id", "session_id", "condition", "target"]
    if "reference_mg_l" in attempts.columns:
        meta.append("reference_mg_l")
    return attempts[meta].merge(features, on="attempt_id", how="inner")


def task_target(dataset: pd.DataFrame, task: str) -> tuple[pd.DataFrame, pd.Series]:
    """Seleciona as linhas e o rótulo de uma tarefa de ``TASKS``.

    - ``3classes``: todas as tentativas; rótulo ``target``.
    - ``etapa1``: todas as tentativas; rótulo ``alcool`` ou ``sem_alcool``.
    - ``etapa2``: só tentativas com álcool; rótulo ``bebida`` ou ``externo``.
    """
    if task == "3classes":
        subset = dataset
        y = subset["target"]
    elif task == "etapa1":
        subset = dataset
        y = subset["target"].where(subset["target"] == "sem_alcool", "alcool")
    elif task == "etapa2":
        subset = dataset[dataset["target"] != "sem_alcool"]
        y = subset["target"]
    else:
        raise ValueError(f"tarefa desconhecida: {task}; use uma de {list(TASKS)}")
    subset = subset.reset_index(drop=True)
    return subset, y.reset_index(drop=True).astype(str)


def _sensor_features(
    name: str, before: pd.Series, window: pd.DataFrame, column: str, blow_start: pd.Timestamp
) -> dict:
    result = {f"{name}_{stat}": np.nan for stat in _STATS}
    values = window[[column, "timestamp"]].dropna()
    if before.isna().all() or values.empty:
        return result

    baseline = float(before.median())
    peak_index = values[column].idxmax()
    peak = float(values.loc[peak_index, column])
    peak_time = values.loc[peak_index, "timestamp"]
    rise = peak - baseline

    result[f"{name}_before"] = baseline
    result[f"{name}_peak"] = peak
    result[f"{name}_rise"] = rise
    result[f"{name}_peak_time_s"] = (peak_time - blow_start).total_seconds()

    if rise > _MIN_RISE:
        after_peak = values[values["timestamp"] > peak_time]
        recovered = after_peak[after_peak[column] <= baseline + rise / 2]
        if not recovered.empty:
            result[f"{name}_recovery_s"] = (recovered["timestamp"].iloc[0] - peak_time).total_seconds()
    return result


def _safe_ratio(numerator: float, denominator: float) -> float:
    if pd.isna(numerator) or pd.isna(denominator) or abs(denominator) <= _MIN_RISE:
        return np.nan
    return float(numerator / denominator)
