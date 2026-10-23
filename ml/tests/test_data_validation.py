from __future__ import annotations

import pandas as pd
import pytest

from src.data_io import load_raw_data, read_readings_csv, write_csv
from src.data_validation import (
    DataValidationError,
    check_consistency,
    validate_attempts,
    validate_readings,
)
from tests.conftest import make_attempt, make_dataset


def _readings() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": ["2026-10-20T14:00:00-03:00", "2026-10-20T14:00:01-03:00"],
            "attempt_id": ["a1", "a1"],
            "phase": ["before", "BLOW"],
            "mq3_raw": ["512", "530.5"],
            "mq135_raw": [None, "300"],
            "temperature_c": [25, None],
            "humidity_pct": [60, None],
        }
    )


def _attempts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "attempt_id": ["a1", "a2"],
            "participant_id": ["p1", "p1"],
            "session_id": ["s1", "s1"],
            "condition": ["perfume", "Drink"],
            "reference_mg_l": [None, 0.2],
        }
    )


def test_valid_readings_are_typed_and_converted_to_utc():
    df = validate_readings(_readings())

    assert str(df["timestamp"].dt.tz) == "UTC"
    assert df.loc[0, "timestamp"] == pd.Timestamp("2026-10-20T17:00:00Z")
    assert list(df["phase"]) == ["before", "blow"]
    assert df["mq3_raw"].dtype == float
    assert df["mq135_raw"].isna().sum() == 1


def test_readings_report_all_problems_together():
    df = _readings().astype(object)
    df.loc[0, "phase"] = "durante"
    df.loc[1, "mq3_raw"] = None
    df.loc[1, "humidity_pct"] = "úmido"
    df.loc[0, "timestamp"] = "2026-10-20T14:00:00"

    with pytest.raises(DataValidationError) as exc:
        validate_readings(df)
    assert len(exc.value.problems) == 4


def test_duplicate_reading_is_rejected():
    df = _readings()
    df.loc[1, "timestamp"] = df.loc[0, "timestamp"]
    with pytest.raises(DataValidationError, match="repetidas"):
        validate_readings(df)


def test_attempts_get_target_from_condition():
    attempts = validate_attempts(_attempts())
    assert dict(zip(attempts["attempt_id"], attempts["target"])) == {"a1": "externo", "a2": "bebida"}


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("condition", "vinho", "condition desconhecida"),
        ("reference_mg_l", -1, "reference_mg_l"),
        ("participant_id", "", "participant_id vazio"),
        ("attempt_id", "a1", "attempt_id repetido"),
    ],
)
def test_invalid_attempts_are_rejected(column, value, message):
    df = _attempts()
    df.loc[1, column] = value
    with pytest.raises(DataValidationError, match=message):
        validate_attempts(df)


def test_consistency_requires_registered_attempts():
    readings = validate_readings(_readings())
    attempts = validate_attempts(_attempts())
    assert check_consistency(readings, attempts) == ["tentativas sem leituras (ignoradas): ['a2']"]

    with pytest.raises(DataValidationError, match="não estão em attempts.csv"):
        check_consistency(readings, attempts[attempts["attempt_id"] == "a2"])


def test_csv_round_trip(tmp_path):
    original = validate_readings(make_attempt("a1", "drink", "2026-10-20T14:00:00-03:00"))
    write_csv(original, tmp_path / "out.csv")
    pd.testing.assert_frame_equal(read_readings_csv(tmp_path / "out.csv"), original)


def test_load_raw_data(tmp_path):
    readings, attempts = make_dataset(n_participants=2, repetitions=1)
    write_csv(readings, tmp_path / "readings" / "dia1.csv")
    write_csv(attempts.drop(columns="target"), tmp_path / "attempts.csv")

    loaded, loaded_attempts, warnings = load_raw_data(tmp_path / "readings", tmp_path / "attempts.csv")
    assert set(loaded["source_file"]) == {"dia1.csv"}
    assert len(loaded_attempts) == len(attempts)
    assert warnings == []


def test_load_raw_data_explains_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="readings_template"):
        load_raw_data(tmp_path / "readings", tmp_path / "attempts.csv")
