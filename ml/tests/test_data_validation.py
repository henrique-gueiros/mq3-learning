from __future__ import annotations

import pandas as pd
import pytest

from src.data_io import load_raw_readings, read_readings_csv, write_readings_csv
from src.data_validation import DataValidationError, validate_readings


def test_valid_rows_are_typed_and_converted_to_utc(raw_csv_rows):
    df = validate_readings(raw_csv_rows, expected_source="real")

    assert str(df["timestamp"].dt.tz) == "UTC"
    assert df.loc[0, "timestamp"] == pd.Timestamp("2026-10-20T17:00:00Z")
    assert df["sensor_raw"].dtype == float
    assert str(df["label"].dtype) == "Int64"
    assert df["label"].isna().sum() == 1


def test_missing_columns_are_reported(raw_csv_rows):
    with pytest.raises(DataValidationError, match="label"):
        validate_readings(raw_csv_rows.drop(columns=["label"]))


def test_timestamp_without_timezone_is_rejected(raw_csv_rows):
    raw_csv_rows.loc[1, "timestamp"] = "2026-10-20T14:00:01"
    with pytest.raises(DataValidationError, match="fuso") as exc:
        validate_readings(raw_csv_rows)
    assert "linhas [3]" in str(exc.value)


def test_all_problems_are_reported_together(raw_csv_rows):
    raw_csv_rows.loc[0, "label"] = 2
    raw_csv_rows.loc[1, "sensor_raw"] = "abc"
    raw_csv_rows.loc[2, "source"] = "synthetic"

    with pytest.raises(DataValidationError) as exc:
        validate_readings(raw_csv_rows, expected_source="real")
    assert len(exc.value.problems) == 3


def test_duplicate_session_and_timestamp_is_rejected(raw_csv_rows):
    raw_csv_rows.loc[1, "timestamp"] = raw_csv_rows.loc[0, "timestamp"]
    with pytest.raises(DataValidationError, match="repetidas"):
        validate_readings(raw_csv_rows)


def test_csv_round_trip(tmp_path, raw_csv_rows):
    original = validate_readings(raw_csv_rows)
    path = tmp_path / "out.csv"
    write_readings_csv(original, path)

    loaded = read_readings_csv(path)
    pd.testing.assert_frame_equal(loaded, original)


def test_load_raw_readings_tracks_file_and_requires_real(tmp_path, raw_csv_rows):
    raw_csv_rows.to_csv(tmp_path / "sessao_a.csv", index=False)
    df = load_raw_readings(tmp_path)
    assert set(df["source_file"]) == {"sessao_a.csv"}

    raw_csv_rows.assign(source="synthetic").to_csv(tmp_path / "errado.csv", index=False)
    with pytest.raises(DataValidationError, match="errado.csv"):
        load_raw_readings(tmp_path)


def test_load_raw_readings_without_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="nenhum CSV"):
        load_raw_readings(tmp_path)
