from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data_validation import validate_readings
from src.features import (
    SENSOR_SETS,
    all_feature_columns,
    assign_phases,
    build_dataset,
    compute_features,
    feature_columns,
)
from tests.conftest import make_dataset, make_session


def _simple_session() -> pd.DataFrame:
    """MQ-3: 100 antes, pico 300 um segundo depois do início do sopro (t = 20 s)."""
    t_s = [17, 18, 19, 20, 21, 22, 23, 24]
    df = validate_readings(
        pd.DataFrame(
            {
                "t_ms": [t * 1000 for t in t_s],
                "mq3_raw": [100, 100, 100, 200, 300, 250, 150, 120],
                "mq135_raw": [200, 200, 200, 210, 250, 240, 220, 210],
                "temperature_c": [25.0] * 8,
                "humidity_pct": [50, 50, 50, 70, 90, 80, 60, 55],
            }
        )
    )
    df.insert(0, "session_file", "s1.csv")
    return df


def _attempt(start_s: float = 20, end_s: float = 22, attempt_id: str = "a1") -> pd.DataFrame:
    return pd.DataFrame(
        {"attempt_id": [attempt_id], "session_file": ["s1.csv"], "blow_start_s": [start_s], "blow_end_s": [end_s]}
    )


def test_phases_follow_blow_start():
    phased, warnings = assign_phases(_simple_session(), _attempt())

    assert warnings == []
    assert list(phased["phase"]) == ["before"] * 3 + ["blow"] * 3 + ["after"] * 2
    assert set(phased["attempt_id"]) == {"a1"}


def test_features_of_a_simple_attempt():
    phased, _ = assign_phases(_simple_session(), _attempt())
    features, warnings = compute_features(phased)
    row = features.iloc[0]

    assert warnings == []
    assert row["mq3_before"] == 100
    assert row["mq3_peak"] == 300
    assert row["mq3_rise"] == 200
    assert row["mq3_peak_time_s"] == 1
    assert row["mq3_recovery_s"] == 2
    assert row["mq135_mq3_rise_ratio"] == pytest.approx(50 / 200)
    assert row["mq3_humidity_peak_lag_s"] == 0


def test_blow_start_outside_the_session_is_skipped():
    phased, warnings = assign_phases(_simple_session(), _attempt(start_s=500, end_s=505))
    features, _ = compute_features(phased)

    assert features.empty
    assert "blow_start_s" in warnings[0]


def test_attempts_too_close_in_the_same_session_warn():
    session = validate_readings(make_session("clean"))
    session.insert(0, "session_file", "s1.csv")
    attempts = pd.concat([_attempt(10, 12, "a1"), _attempt(30, 32, "a2")])
    _, warnings = assign_phases(session, attempts)
    assert "a2" in warnings[0]


def test_missing_dht11_readings_do_not_break_features():
    readings = _simple_session()
    readings["humidity_pct"] = np.nan
    phased, _ = assign_phases(readings, _attempt())
    features, _ = compute_features(phased)

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


def test_firmware_columns_derived_from_mq3_are_never_features():
    assert not {"ppm", "alcool", "amostra", "mq135_mv"} & set(all_feature_columns())


def test_temperature_is_not_a_feature():
    # A temperatura não distingue hálito de ambiente e, num carro, varia com o clima.
    assert not [c for c in all_feature_columns() if c.startswith("temperature")]


def test_target_is_only_alcohol_or_not():
    readings, attempts = make_dataset(n_participants=2, repetitions=1)
    phased, _ = assign_phases(readings, attempts)
    features, _ = compute_features(phased)
    dataset = build_dataset(features, attempts)

    assert set(dataset["target"]) == {"sem_efeito", "sob_efeito"}
    assert set(dataset.loc[dataset["condition"].isin(["clean", "perfume"]), "target"]) == {"sem_efeito"}
    assert set(dataset.loc[dataset["condition"] == "drink", "target"]) == {"sob_efeito"}
