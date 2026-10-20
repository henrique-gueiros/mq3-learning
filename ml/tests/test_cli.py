from __future__ import annotations

import json

import pandas as pd

from src.cli import main
from src.data_io import write_readings_csv
from src.paths import ProjectPaths
from tests.conftest import make_fake_real


def test_full_pipeline_with_fake_real_data(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_readings_csv(make_fake_real(n_sessions=6), paths.raw_dir / "sessoes.csv")

    assert main(["--root", str(tmp_path), "all", "--n-sessions", "5"]) == 0

    manifest = json.loads(paths.split_manifest.read_text(encoding="utf-8"))
    assert not set(manifest["train_sessions"]) & set(manifest["test_sessions"])

    train = pd.read_csv(paths.train)
    test = pd.read_csv(paths.test)
    assert set(train["source"]) == {"real", "synthetic"}
    assert set(test["source"]) == {"real"}
    assert set(test["session_id"]) == set(manifest["test_sessions"])
    assert (paths.synthetic_dir / "synthetic_estimated.csv").exists()


def test_split_is_stable_across_runs(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_readings_csv(make_fake_real(n_sessions=6), paths.raw_dir / "sessoes.csv")

    assert main(["--root", str(tmp_path), "split"]) == 0
    first = paths.split_manifest.read_text(encoding="utf-8")
    assert main(["--root", str(tmp_path), "split", "--seed", "99"]) == 0
    assert paths.split_manifest.read_text(encoding="utf-8") == first


def test_errors_return_exit_code_1(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "validate"]) == 1
    assert "nenhum CSV" in capsys.readouterr().err
