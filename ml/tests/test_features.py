from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data_validation import validate_readings
from src.features import (
    SENSOR_SETS,
    all_feature_columns,
    build_dataset,
    compute_features,
    feature_columns,
    task_target,
)
from tests.conftest import make_attempt, make_dataset


def _simple_attempt() -> pd.DataFrame:
    """MQ-3: 100 antes, pico 300 no 2º segundo do sopro, volta a 150 depois."""
    mq3 = [100, 100, 100, 200, 300, 250, 150, 120]
    humidity = [50, 50, 50, 70, 90, 80, 60, 55]
    phases = ["before"] * 3 + ["blow"] * 3 + ["after"] * 2
    return validate_readings(
        pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-10-20T14:00:00-03:00", periods=8, freq="1s"),
                "attempt_id": "a1",
                "phase": phases,
                "mq3_raw": mq3,
                "mq135_raw": [200, 200, 200, 210, 250, 240, 220, 210],
                "temperature_c": [25.0] * 8,
                "humidity_pct": humidity,
            }
        )
    )


def test_features_of_a_simple_attempt():
    features, warnings = compute_features(_simple_attempt())
    row = features.iloc[0]

    assert warnings == []
    assert row["mq3_before"] == 100
    assert row["mq3_peak"] == 300
    assert row["mq3_rise"] == 200
    assert row["mq3_peak_time_s"] == 1
    assert row["mq3_recovery_s"] == 2
    assert row["mq135_mq3_rise_ratio"] == pytest.approx(50 / 200)
    assert row["mq3_humidity_peak_lag_s"] == 0
    assert row["temperature_rise"] == 0
    assert np.isnan(row["temperature_recovery_s"])


def test_attempt_without_blow_is_skipped():
    readings = _simple_attempt()
    readings = readings[readings["phase"] != "blow"]
    features, warnings = compute_features(readings)

    assert features.empty
    assert "a1" in warnings[0]


def test_missing_dht11_readings_do_not_break_features():
    readings = _simple_attempt()
    readings["humidity_pct"] = np.nan
    features, _ = compute_features(readings)

    assert features["humidity_rise"].isna().all()
    assert features["mq3_humidity_peak_lag_s"].isna().all()
    assert features["mq3_rise"].notna().all()


def test_every_sensor_set_uses_mq3_and_the_full_set_uses_everything():
    for sensor_set in SENSOR_SETS:
        assert "mq3_rise" in feature_columns(sensor_set)
    assert feature_columns("mq3+mq135+dht11") == all_feature_columns()
    assert "humidity_rise" not in feature_columns("mq3+mq135")
    with pytest.raises(ValueError):
        feature_columns("mq7")


def test_tasks_select_rows_and_labels():
    readings, attempts = make_dataset(n_participants=2, repetitions=1)
    features, _ = compute_features(readings)
    dataset = build_dataset(features, attempts)

    _, y3 = task_target(dataset, "3classes")
    _, y1 = task_target(dataset, "etapa1")
    subset2, y2 = task_target(dataset, "etapa2")

    assert set(y3) == {"sem_alcool", "externo", "bebida"}
    assert set(y1) == {"sem_alcool", "alcool"}
    assert set(y2) == {"externo", "bebida"}
    assert (subset2["target"] != "sem_alcool").all()


def test_drink_rises_more_than_perfume_in_fixture():
    features, _ = compute_features(make_attempt("d", "drink", "2026-10-20T14:00:00Z"))
    perfume, _ = compute_features(make_attempt("p", "perfume", "2026-10-20T14:00:00Z"))
    assert features["mq3_rise"].iloc[0] > perfume["mq3_rise"].iloc[0]
    assert perfume["mq3_before"].iloc[0] > features["mq3_before"].iloc[0]
