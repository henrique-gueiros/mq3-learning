"""Transforma as leituras de cada tentativa de sopro em uma linha de features.

Primeiro, ``assign_phases`` recorta de cada sessão as leituras de cada tentativa,
a partir do ``blow_start_s`` cadastrado em ``attempts.csv``:

- ``before``: os ``BEFORE_SECONDS`` antes do sopro (o ambiente);
- ``blow``: do início ao fim do sopro;
- ``after``: os ``AFTER_SECONDS`` depois do sopro (pico e recuperação).

Depois, ``compute_features`` calcula para cada sensor (``mq3``, ``mq135``,
``humidity``; a temperatura fica de fora porque não distingue hálito de ambiente):

- ``<sensor>_before``: mediana na fase ``before``;
- ``<sensor>_peak``: máximo nas fases ``blow`` e ``after``;
- ``<sensor>_rise``: ``peak - before`` (quanto subiu com o sopro);
- ``<sensor>_peak_time_s``: segundos entre o início do sopro e o pico;
- ``<sensor>_recovery_s``: segundos entre o pico e a volta para menos da
  metade da subida (vazio se não voltou ou se não subiu).

E features que combinam sensores:

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

BEFORE_SECONDS = 15.0
DEFAULT_BLOW_SECONDS = 5.0
AFTER_SECONDS = 30.0

SENSORS = {
    "mq3": "mq3_raw",
    "mq135": "mq135_raw",
    "humidity": "humidity_pct",
}
_STATS = ("before", "peak", "rise", "peak_time_s", "recovery_s")
_MIN_RISE = 1e-9

SENSOR_GROUPS = {
    "mq3": [f"mq3_{s}" for s in _STATS],
    "mq135": [f"mq135_{s}" for s in _STATS] + ["mq135_mq3_rise_ratio"],
    "dht11": [f"humidity_{s}" for s in _STATS]
    + ["mq3_humidity_peak_lag_s"],
}

SENSOR_SETS = {
    "mq3": ["mq3"],
    "mq3+mq135": ["mq3", "mq135"],
    "mq3+dht11": ["mq3", "dht11"],
    "mq3+mq135+dht11": ["mq3", "mq135", "dht11"],
}

def feature_columns(sensor_set: str) -> list[str]:
    """Colunas de features usadas por um conjunto de sensores de ``SENSOR_SETS``."""
    if sensor_set not in SENSOR_SETS:
        raise ValueError(f"conjunto de sensores desconhecido: {sensor_set}; use um de {list(SENSOR_SETS)}")
    return [col for group in SENSOR_SETS[sensor_set] for col in SENSOR_GROUPS[group]]


def all_feature_columns() -> list[str]:
    return feature_columns("mq3+mq135+dht11")


def assign_phases(readings: pd.DataFrame, attempts: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Recorta as leituras de cada tentativa e marca a fase de cada uma.

    Args:
        readings: leituras validadas, com ``session_file`` e ``t_ms``.
        attempts: tentativas com ``attempt_id``, ``session_file``, ``blow_start_s``
            e, opcionalmente, ``blow_end_s``.

    Returns:
        ``(leituras com attempt_id, phase e blow_start_ms; avisos)``. Há aviso
        quando as janelas de duas tentativas da mesma sessão se sobrepõem, porque
        o "antes" de uma fica contaminado pelo sopro da outra.
    """
    blow_end = pd.to_numeric(attempts.get("blow_end_s", pd.Series(np.nan, index=attempts.index)), errors="coerce")
    windows = pd.DataFrame(
        {
            "attempt_id": attempts["attempt_id"],
            "session_file": attempts["session_file"],
            "start_ms": attempts["blow_start_s"] * 1000,
            "end_ms": blow_end.fillna(attempts["blow_start_s"] + DEFAULT_BLOW_SECONDS) * 1000,
        }
    )

    frames: list[pd.DataFrame] = []
    empty_windows: list[str] = []
    for window in windows.itertuples(index=False):
        session = readings[readings["session_file"] == window.session_file]
        t = session["t_ms"]
        phase = pd.Series(pd.NA, index=session.index, dtype="string")
        phase[(t >= window.start_ms - BEFORE_SECONDS * 1000) & (t < window.start_ms)] = "before"
        phase[(t >= window.start_ms) & (t <= window.end_ms)] = "blow"
        phase[(t > window.end_ms) & (t <= window.end_ms + AFTER_SECONDS * 1000)] = "after"
        part = session[phase.notna()].copy()
        part.insert(0, "attempt_id", window.attempt_id)
        part["phase"] = phase[phase.notna()]
        part["blow_start_ms"] = window.start_ms
        if not {"before", "blow"} <= set(part["phase"]):
            empty_windows.append(str(window.attempt_id))
        frames.append(part)

    warnings: list[str] = []
    if empty_windows:
        warnings.append(
            f"tentativas sem leituras antes ou durante o sopro (confira blow_start_s): {empty_windows[:10]}"
        )
    for session_file, group in windows.sort_values("start_ms").groupby("session_file"):
        previous_end = (group["end_ms"] + AFTER_SECONDS * 1000).shift()
        overlapping = group.loc[group["start_ms"] - BEFORE_SECONDS * 1000 < previous_end, "attempt_id"]
        if not overlapping.empty:
            warnings.append(
                f"{session_file}: tentativas muito próximas (o 'antes' pega o sopro anterior): "
                f"{overlapping.tolist()[:10]}"
            )

    columns = ["attempt_id", *readings.columns, "phase", "blow_start_ms"]
    phased = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
    return phased, warnings


def compute_features(phased: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Calcula uma linha de features por ``attempt_id`` a partir de ``assign_phases``.

    Tentativas sem leitura do MQ-3 na fase ``before`` ou na fase ``blow`` são
    descartadas, porque não dá para comparar o antes com o sopro.

    Returns:
        ``(features, avisos)``; ``features`` tem a coluna ``attempt_id`` e as
        colunas de ``all_feature_columns()``.
    """
    rows: list[dict] = []
    skipped: list[str] = []
    for attempt_id, attempt in phased.groupby("attempt_id", sort=True):
        before = attempt[attempt["phase"] == "before"]
        window = attempt[attempt["phase"].isin(["blow", "after"])]
        blow = attempt[attempt["phase"] == "blow"]
        if before["mq3_raw"].isna().all() or blow["mq3_raw"].isna().all():
            skipped.append(str(attempt_id))
            continue

        blow_start_ms = float(attempt["blow_start_ms"].iloc[0])
        row: dict = {"attempt_id": attempt_id}
        for name, column in SENSORS.items():
            row.update(_sensor_features(name, before[column], window, column, blow_start_ms))

        row["mq135_mq3_rise_ratio"] = _safe_ratio(row["mq135_rise"], row["mq3_rise"])
        row["mq3_humidity_peak_lag_s"] = row["mq3_peak_time_s"] - row["humidity_peak_time_s"]
        rows.append(row)

    warnings = []
    if skipped:
        warnings.append(
            f"tentativas sem leituras do MQ-3 antes ou durante o sopro (descartadas; confira blow_start_s): {skipped[:10]}"
        )
    features = pd.DataFrame(rows, columns=["attempt_id", *all_feature_columns()])
    return features, warnings


def build_dataset(features: pd.DataFrame, attempts: pd.DataFrame) -> pd.DataFrame:
    """Junta as features com sessão, participante, condição e classe de cada tentativa."""
    meta = ["attempt_id", "session_file", "participant_id", "condition", "target"]
    if "reference_mg_l" in attempts.columns:
        meta.append("reference_mg_l")
    return attempts[meta].merge(features, on="attempt_id", how="inner")


def _sensor_features(
    name: str, before: pd.Series, window: pd.DataFrame, column: str, blow_start_ms: float
) -> dict:
    result = {f"{name}_{stat}": np.nan for stat in _STATS}
    values = window[[column, "t_ms"]].dropna()
    if before.isna().all() or values.empty:
        return result

    baseline = float(before.median())
    peak_index = values[column].idxmax()
    peak = float(values.loc[peak_index, column])
    peak_ms = float(values.loc[peak_index, "t_ms"])
    rise = peak - baseline

    result[f"{name}_before"] = baseline
    result[f"{name}_peak"] = peak
    result[f"{name}_rise"] = rise
    result[f"{name}_peak_time_s"] = (peak_ms - blow_start_ms) / 1000

    if rise > _MIN_RISE:
        after_peak = values[values["t_ms"] > peak_ms]
        recovered = after_peak[after_peak[column] <= baseline + rise / 2]
        if not recovered.empty:
            result[f"{name}_recovery_s"] = (float(recovered["t_ms"].iloc[0]) - peak_ms) / 1000
    return result


def _safe_ratio(numerator: float, denominator: float) -> float:
    if pd.isna(numerator) or pd.isna(denominator) or abs(denominator) <= _MIN_RISE:
        return np.nan
    return float(numerator / denominator)
