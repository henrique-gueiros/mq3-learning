from __future__ import annotations

import pandas as pd
import pytest

from src.data_io import load_raw_data, read_session_csv, write_csv
from src.data_validation import (
    DataValidationError,
    check_consistency,
    validate_attempts,
    validate_readings,
)
from src.paths import ML_ROOT
from tests.conftest import make_dataset, make_session

FIRMWARE_SAMPLE = ML_ROOT.parent / "esp32-esp8266" / "leituras.csv"


def _attempts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "attempt_id": ["a1", "a2"],
            "session_file": ["leituras_1.csv", "leituras_1"],
            "participant_id": ["p1", "p1"],
            "condition": ["perfume", "Drink"],
            "blow_start_s": [20, 80],
            "blow_end_s": [None, 86],
            "reference_mg_l": [None, 0.2],
        }
    )


def test_firmware_session_is_typed_and_sorted():
    df = validate_readings(make_session("clean").iloc[::-1])

    assert df["t_ms"].is_monotonic_increasing
    assert df["mq3_raw"].dtype == float
    assert df["humidity_pct"].isna().sum() == 2
    assert {"ppm", "alcool"} <= set(df.columns)


@pytest.mark.skipif(not FIRMWARE_SAMPLE.exists(), reason="sem amostra do firmware no repositório")
def test_real_firmware_sample_is_accepted():
    df = read_session_csv(FIRMWARE_SAMPLE)
    assert len(df) > 0
    assert set(df["session_file"]) == {"leituras.csv"}


def test_readings_report_all_problems_together():
    df = make_session("clean").astype(object)
    df.loc[0, "t_ms"] = None
    df.loc[1, "mq3_raw"] = None
    df.loc[2, "humidity_pct"] = "úmido"

    with pytest.raises(DataValidationError) as exc:
        validate_readings(df)
    assert len(exc.value.problems) == 3


def test_repeated_t_ms_is_rejected():
    df = make_session("clean")
    df.loc[1, "t_ms"] = df.loc[0, "t_ms"]
    with pytest.raises(DataValidationError, match="t_ms repetido"):
        validate_readings(df)


def test_attempts_get_target_and_csv_extension():
    attempts = validate_attempts(_attempts())

    assert dict(zip(attempts["attempt_id"], attempts["target"])) == {"a1": "sem_efeito", "a2": "sob_efeito"}
    assert set(attempts["session_file"]) == {"leituras_1.csv"}


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("condition", "vinho", "condition desconhecida"),
        ("blow_start_s", None, "blow_start_s"),
        ("blow_end_s", 10, "blow_end_s"),
        ("reference_mg_l", -1, "reference_mg_l"),
        ("participant_id", "", "participant_id vazio"),
        ("attempt_id", "a1", "attempt_id repetido"),
    ],
)
def test_invalid_attempts_are_rejected(column, value, message):
    df = _attempts().astype(object)
    df.loc[1, column] = value
    with pytest.raises(DataValidationError, match=message):
        validate_attempts(df)


def test_consistency_between_sessions_and_attempts():
    readings, attempts = make_dataset(n_participants=1, repetitions=1)
    assert check_consistency(readings, attempts) == []

    extra = attempts.iloc[[0]].assign(attempt_id="x", session_file="nao_existe.csv")
    with pytest.raises(DataValidationError, match="nao_existe.csv"):
        check_consistency(readings, pd.concat([attempts, extra]))

    warnings = check_consistency(readings, attempts.iloc[1:])
    assert "sem tentativas cadastradas" in warnings[0]


def test_load_raw_data(tmp_path):
    for condition in ("clean", "drink"):
        write_csv(make_session(condition), tmp_path / "sessions" / f"{condition}.csv")
    write_csv(
        pd.DataFrame(
            {
                "attempt_id": ["a1", "a2"],
                "session_file": ["clean.csv", "drink.csv"],
                "participant_id": ["p1", "p1"],
                "condition": ["clean", "drink"],
                "blow_start_s": [20, 20],
            }
        ),
        tmp_path / "attempts.csv",
    )

    readings, attempts, warnings = load_raw_data(tmp_path / "sessions", tmp_path / "attempts.csv")
    assert set(readings["session_file"]) == {"clean.csv", "drink.csv"}
    assert len(attempts) == 2
    assert warnings == []


def test_load_raw_data_explains_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="firmware"):
        load_raw_data(tmp_path / "sessions", tmp_path / "attempts.csv")
