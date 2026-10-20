from __future__ import annotations

import pandas as pd
import pytest

from src.data_generation import SyntheticParams, generate_synthetic, load_params, save_params
from src.data_validation import validate_readings
from src.paths import ProjectPaths
from tests.conftest import make_params


def test_generated_data_follows_schema():
    df = generate_synthetic(make_params())
    validated = validate_readings(df, expected_source="synthetic")

    assert len(validated) == 2 * 4 * 20
    assert validated.groupby("session_id")["label"].nunique().eq(1).all()
    assert validated["session_id"].str.startswith("syn-").all()


def test_same_seed_same_data_and_different_seed_different_data():
    params = make_params()
    pd.testing.assert_frame_equal(generate_synthetic(params), generate_synthetic(params))
    assert not generate_synthetic(params, seed=1).equals(generate_synthetic(params, seed=2))


def test_didactic_config_is_valid_and_classes_overlap():
    params = load_params(ProjectPaths().didactic_params)
    assert params.origin == "didactic"

    df = generate_synthetic(params)
    no_alcohol = df.loc[df["label"] == 0, "sensor_raw"]
    alcohol = df.loc[df["label"] == 1, "sensor_raw"]
    assert alcohol.min() < no_alcohol.max()


def test_clip_limits_values():
    params = make_params()
    params.clip_min, params.clip_max = 150.0, 160.0
    df = generate_synthetic(params)
    assert df["sensor_raw"].between(150.0, 160.0).all()


def test_params_round_trip(tmp_path):
    params = make_params()
    save_params(params, tmp_path / "params.json")
    assert load_params(tmp_path / "params.json") == params


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["classes"].pop("1"),
        lambda d: d["classes"]["0"].update(noise_std=-1),
        lambda d: d.update(start_time="2026-01-01T00:00:00"),
        lambda d: d.update(clip_min=10, clip_max=5),
        lambda d: d["classes"]["0"].update(typo=1),
    ],
)
def test_invalid_params_are_rejected(change):
    data = make_params().to_dict()
    change(data)
    with pytest.raises(ValueError, match="parâmetros sintéticos inválidos"):
        SyntheticParams.from_dict(data)
