from __future__ import annotations

import json

import pandas as pd

from src.cli import main
from src.data_io import write_csv
from src.paths import ProjectPaths
from tests.conftest import make_attempt, make_dataset


def _write_raw(paths: ProjectPaths, n_participants: int = 6) -> None:
    readings, attempts = make_dataset(n_participants=n_participants, repetitions=1)
    write_csv(readings, paths.raw_readings_dir / "coleta.csv")
    write_csv(attempts.drop(columns="target"), paths.raw_attempts)


def test_full_pipeline_and_prediction(tmp_path, capsys):
    paths = ProjectPaths(tmp_path)
    _write_raw(paths)

    assert main(["--root", str(tmp_path), "validate"]) == 0
    assert main(["--root", str(tmp_path), "all", "--task", "etapa2"]) == 0

    manifest = json.loads(paths.split_manifest.read_text(encoding="utf-8"))
    assert not set(manifest["train_groups"]) & set(manifest["test_groups"])
    test = pd.read_csv(paths.test)
    assert set(test["participant_id"]) == set(manifest["test_groups"])
    assert (paths.reports_dir / "experiment_etapa2.csv").exists()
    final = json.loads((paths.reports_dir / "final_etapa2.json").read_text(encoding="utf-8"))
    assert "test_metrics" in final

    write_csv(make_attempt("novo", "drink", "2026-10-22T10:00:00Z"), tmp_path / "novo.csv")
    capsys.readouterr()
    code = main(
        [
            "--root", str(tmp_path), "predict",
            "--readings", str(tmp_path / "novo.csv"),
            "--model", str(paths.models_dir / "etapa2.joblib"),
        ]
    )
    assert code == 0
    assert "bebida" in capsys.readouterr().out


def test_prepare_keeps_split_stable(tmp_path):
    paths = ProjectPaths(tmp_path)
    _write_raw(paths)

    assert main(["--root", str(tmp_path), "prepare"]) == 0
    first = paths.split_manifest.read_text(encoding="utf-8")
    assert main(["--root", str(tmp_path), "prepare", "--seed", "7"]) == 0
    assert paths.split_manifest.read_text(encoding="utf-8") == first


def test_errors_return_exit_code_1(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "validate"]) == 1
    assert "readings_template" in capsys.readouterr().err
