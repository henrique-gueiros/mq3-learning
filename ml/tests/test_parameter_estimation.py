from __future__ import annotations

import pytest

from src.data_generation import generate_synthetic
from src.parameter_estimation import estimate_params
from tests.conftest import make_fake_real


def test_estimation_recovers_known_parameters():
    df = make_fake_real(n_sessions=40, samples=50)
    params, warnings = estimate_params(df, n_sessions_per_class=None)

    assert warnings == []
    assert params.origin == "estimated"
    assert params.classes[0].level_mean == pytest.approx(100, abs=5)
    assert params.classes[1].level_mean == pytest.approx(200, abs=5)
    assert params.classes[0].level_std == pytest.approx(10, abs=4)
    assert params.classes[1].noise_std == pytest.approx(5, abs=1)
    assert params.classes[0].n_sessions == 40
    assert params.classes[0].samples_per_session == 50
    assert params.sample_interval_seconds == pytest.approx(1.0)


def test_estimated_params_generate_data_in_observed_range():
    df = make_fake_real(n_sessions=6)
    params, _ = estimate_params(df, n_sessions_per_class=10)
    synthetic = generate_synthetic(params)

    assert synthetic["session_id"].nunique() == 20
    assert synthetic["sensor_raw"].between(df["sensor_raw"].min(), df["sensor_raw"].max()).all()


def test_few_sessions_produce_warnings():
    df = make_fake_real(n_sessions=1)
    params, warnings = estimate_params(df)

    assert params.classes[0].level_std == 0.0
    assert any("só 1 sessão" in w for w in warnings)


def test_rejects_synthetic_rows():
    df = make_fake_real()
    df.loc[0, "source"] = "synthetic"
    with pytest.raises(ValueError, match="somente leituras reais"):
        estimate_params(df)


def test_rejects_missing_class():
    df = make_fake_real()
    with pytest.raises(ValueError, match="label=1"):
        estimate_params(df[df["label"] == 0])
