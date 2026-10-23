from __future__ import annotations

import pandas as pd
import pytest

from src.features import SENSOR_SETS, build_dataset, compute_features
from src.inference import predict_attempts
from src.splitting import apply_split, update_split
from src.train import choose_best, compute_metrics, model_specs, run_experiment, save_model, train_final_model
from tests.conftest import make_attempt, make_dataset


def _train_test() -> tuple[pd.DataFrame, pd.DataFrame]:
    readings, attempts = make_dataset(n_participants=8, repetitions=2)
    features, _ = compute_features(readings)
    dataset = build_dataset(features, attempts)
    split, _ = update_split(dataset, existing=None)
    return apply_split(dataset, split)


def test_metrics():
    y_true = pd.Series(["bebida", "bebida", "externo", "sem_alcool"])
    y_pred = pd.Series(["bebida", "externo", "externo", "sem_alcool"])
    metrics = compute_metrics(y_true, y_pred, ["bebida", "externo", "sem_alcool"])

    assert metrics["recall_bebida"] == 0.5
    assert metrics["precision_externo"] == 0.5
    assert metrics["recall_sem_alcool"] == 1.0


def test_experiment_covers_every_sensor_set_and_model():
    train, _ = _train_test()
    results = run_experiment(train, "3classes", models=model_specs(n_estimators=10))

    assert len(results) == len(SENSOR_SETS) * len(model_specs())
    assert {"recall_bebida", "recall_externo", "recall_sem_alcool"} <= set(results.columns)
    by_model = results.groupby("model")["f1_macro"].max()
    assert by_model["random_forest"] > by_model["baseline"]


def test_experiment_requires_enough_groups():
    train, _ = _train_test()
    two_people = train[train["participant_id"].isin(sorted(train["participant_id"].unique())[:2])]
    with pytest.raises(ValueError, match="pelo menos 3"):
        run_experiment(two_people, "etapa1")


def test_choose_best_ignores_baseline():
    results = pd.DataFrame(
        {"sensor_set": ["mq3", "mq3"], "model": ["baseline", "decision_tree"], "f1_macro": [0.9, 0.5]}
    )
    assert choose_best(results, "f1_macro")["model"] == "decision_tree"
    with pytest.raises(ValueError, match="recall_bebida"):
        choose_best(results, "recall_bebida")


def test_final_model_is_evaluated_on_test_and_used_for_inference(tmp_path):
    train, test = _train_test()
    model, metadata = train_final_model(train, test, "etapa2", "mq3+mq135+dht11", "random_forest")

    assert metadata["classes"] == ["bebida", "externo"]
    assert metadata["n_test_attempts"] == (test["target"] != "sem_alcool").sum()
    assert set(metadata["confusion_matrix"]["labels"]) == {"bebida", "externo"}

    save_model(model, metadata, tmp_path / "etapa2.joblib")
    readings = pd.concat(
        [
            make_attempt("novo-bebida", "drink", "2026-10-21T14:00:00Z", seed=100),
            make_attempt("novo-perfume", "perfume", "2026-10-21T15:00:00Z", seed=101),
        ]
    )
    predictions, _ = predict_attempts(readings, tmp_path / "etapa2.joblib")
    assert dict(zip(predictions["attempt_id"], predictions["prediction"])) == {
        "novo-bebida": "bebida",
        "novo-perfume": "externo",
    }
    assert {"prob_bebida", "prob_externo"} <= set(predictions.columns)
