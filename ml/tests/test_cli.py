from __future__ import annotations

import json

import pandas as pd

from src.cli import main
from src.data_io import write_csv
from src.paths import ProjectPaths
from tests.conftest import BLOW_START_S, make_dataset, make_session


def _write_raw(paths: ProjectPaths, n_participants: int = 6) -> None:
    readings, attempts = make_dataset(n_participants=n_participants, repetitions=1)
    for session_file, session in readings.groupby("session_file"):
        write_csv(session.drop(columns="session_file"), paths.raw_sessions_dir / session_file)
    write_csv(attempts.drop(columns="target"), paths.raw_attempts)


def test_full_pipeline_and_prediction(tmp_path, capsys):
    paths = ProjectPaths(tmp_path)
    _write_raw(paths)

    assert main(["--root", str(tmp_path), "validate"]) == 0
    assert main(["--root", str(tmp_path), "all", "--por-classe", "6"]) == 0

    manifest = json.loads(paths.split_manifest.read_text(encoding="utf-8"))
    assert not set(manifest["train_groups"]) & set(manifest["test_groups"])
    test = pd.read_csv(paths.test)
    assert set(test["participant_id"]) == set(manifest["test_groups"])
    assert (paths.reports_dir / "experiment.csv").exists()
    final = json.loads((paths.reports_dir / "final.json").read_text(encoding="utf-8"))
    assert final["sensor_set"] == "subidas"
    assert "test_metrics" in final

    write_csv(make_session("drink", seed=500), tmp_path / "leituras_99.csv")
    capsys.readouterr()
    code = main(
        [
            "--root", str(tmp_path), "predict",
            "--session", str(tmp_path / "leituras_99.csv"),
            "--blow-start-s", str(BLOW_START_S),
            "--model", str(paths.models_dir / "sob_efeito.joblib"),
        ]
    )
    assert code == 0
    output = capsys.readouterr().out
    assert "leituras_99@20s" in output
    assert "sob_efeito" in output


def test_prepare_keeps_split_stable(tmp_path):
    paths = ProjectPaths(tmp_path)
    _write_raw(paths)

    assert main(["--root", str(tmp_path), "prepare", "--por-classe", "6"]) == 0
    first = paths.split_manifest.read_text(encoding="utf-8")
    assert main(["--root", str(tmp_path), "prepare", "--seed", "7", "--por-classe", "6"]) == 0
    assert paths.split_manifest.read_text(encoding="utf-8") == first


def test_errors_return_exit_code_1(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "validate"]) == 1
    assert "firmware" in capsys.readouterr().err


def test_train_usa_o_mesmo_fluxo_do_pipeline(tmp_path):
    paths = ProjectPaths(tmp_path)
    _write_raw(paths)

    assert main(["--root", str(tmp_path), "all", "--por-classe", "6"]) == 0
    assert (paths.figuras_dir / "matriz_confusao.png").exists()
    assert "f1_macro_std" in pd.read_csv(paths.reports_dir / "experiment.csv").columns


def test_train_imprime_traco_quando_nao_ha_auc(tmp_path, capsys, monkeypatch):
    import src.cli as cli

    monkeypatch.setattr(cli, "treinar_modelos", lambda *a, **k: {"relatorio": "reports/experiment.csv"})
    monkeypatch.setattr(
        cli,
        "avaliar_teste",
        lambda *a, **k: {
            "modelo": "m", "sensor_set": "mq3", "n_teste": 3, "modelo_arquivo": "x", "relatorio": "y",
            "metricas_teste": {"f1_macro": 0.5, "roc_auc": None},
        },
    )
    paths = ProjectPaths(tmp_path)
    write_csv(pd.DataFrame({"sensor_set": ["mq3"], "model": ["m"], "f1_macro": [0.5], "balanced_accuracy": [0.5]}),
              paths.reports_dir / "experiment.csv")

    cli.run_train(paths, "f1_macro", 42)

    assert "f1_macro=0.50, roc_auc=—" in capsys.readouterr().out
