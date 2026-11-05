from __future__ import annotations

import pandas as pd
import pytest

from src.data_validation import validate_readings
from src.features import SENSOR_SETS
from src.inference import predict_attempts
from src.splitting import apply_split, update_split
from src.train import choose_best, compute_metrics, model_specs, run_experiment, save_model, train_final_model
from tests.conftest import BLOW_START_S, make_feature_dataset, make_session


def _train_test() -> tuple[pd.DataFrame, pd.DataFrame]:
    dataset = make_feature_dataset(n_participants=8, repetitions=2)
    split, _ = update_split(dataset, existing=None)
    return apply_split(dataset, split)


def test_metrics():
    y_true = pd.Series(["sob_efeito", "sob_efeito", "sem_efeito", "sem_efeito"])
    y_pred = pd.Series(["sob_efeito", "sem_efeito", "sem_efeito", "sem_efeito"])
    metrics = compute_metrics(y_true, y_pred, ["sob_efeito", "sem_efeito"])

    assert metrics["recall_sob_efeito"] == 0.5
    assert metrics["precision_sob_efeito"] == 1.0
    assert metrics["recall_sem_efeito"] == 1.0


def test_experiment_covers_every_sensor_set_and_model():
    train, _ = _train_test()
    results = run_experiment(train, models=model_specs(n_estimators=10))

    assert len(results) == len(SENSOR_SETS) * len(model_specs())
    assert {"recall_sob_efeito", "recall_sem_efeito"} <= set(results.columns)
    by_model = results.groupby("model")["f1_macro"].max()
    assert by_model["random_forest"] > by_model["baseline"]


def test_experiment_requires_enough_groups():
    train, _ = _train_test()
    two_people = train[train["participant_id"].isin(sorted(train["participant_id"].unique())[:2])]
    with pytest.raises(ValueError, match="pelo menos 3"):
        run_experiment(two_people)


def test_choose_best_ignores_baseline():
    results = pd.DataFrame(
        {"sensor_set": ["mq3", "mq3"], "model": ["baseline", "decision_tree"], "f1_macro": [0.9, 0.5]}
    )
    assert choose_best(results, "f1_macro")["model"] == "decision_tree"
    with pytest.raises(ValueError, match="recall_fantasma"):
        choose_best(results, "recall_fantasma")


def test_final_model_is_evaluated_on_test_and_used_for_inference(tmp_path):
    train, test = _train_test()
    model, metadata = train_final_model(train, test, "mq3+mq135+dht11", "random_forest")

    assert set(metadata["classes"]) == {"sob_efeito", "sem_efeito"}
    assert metadata["n_test_attempts"] == len(test)
    assert set(metadata["confusion_matrix"]["labels"]) == {"sob_efeito", "sem_efeito"}

    save_model(model, metadata, tmp_path / "sob_efeito.joblib")
    frames = []
    for session_file, condition, seed in (("nova_bebida.csv", "drink", 100), ("nova_perfume.csv", "perfume", 101)):
        session = validate_readings(make_session(condition, seed))
        session.insert(0, "session_file", session_file)
        frames.append(session)
    attempts = pd.DataFrame(
        {
            "attempt_id": ["novo-bebida", "novo-perfume"],
            "session_file": ["nova_bebida.csv", "nova_perfume.csv"],
            "blow_start_s": [BLOW_START_S, BLOW_START_S],
        }
    )
    predictions, _ = predict_attempts(pd.concat(frames), attempts, tmp_path / "sob_efeito.joblib")
    assert dict(zip(predictions["attempt_id"], predictions["prediction"])) == {
        "novo-bebida": "sob_efeito",
        "novo-perfume": "sem_efeito",
    }
    assert {"prob_sob_efeito", "prob_sem_efeito"} <= set(predictions.columns)
