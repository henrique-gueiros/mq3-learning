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


def test_modelos_comparados_sem_regressao_logistica():
    """A disciplina não deu regressão logística: baseline, KNN, árvore e floresta."""
    from src.train import model_specs

    specs = model_specs(n_estimators=5)
    assert set(specs) == {"baseline", "knn", "decision_tree", "random_forest"}
    assert "clf__n_neighbors" in specs["knn"].grid


def test_peso_da_bebida_entra_no_grid_das_arvores():
    """O grid escolhe, só no treino, entre nenhum peso, pesos intermediários e o balanceado."""
    from src.train import model_specs

    specs = model_specs(n_estimators=5)
    for nome in ("decision_tree", "random_forest"):
        pesos = specs[nome].grid["clf__class_weight"]
        assert None in pesos and "balanced" in pesos
        assert {"sem_efeito": 1, "sob_efeito": 2} in pesos


def test_spec_final_da_floresta_busca_so_peso_nenhum():
    """A comparação continua com o grid de pesos; o modelo gravado não."""
    from src.train import model_specs, spec_final

    final = spec_final("random_forest", n_estimators=5)
    assert final.grid["clf__class_weight"] == [None]
    assert "balanced" in model_specs(n_estimators=5)["random_forest"].grid["clf__class_weight"]


def test_producao_fica_na_floresta_mesmo_que_o_f1_escolha_outro():
    from src.train import choose_best, fixar_producao, modelo_de_producao

    results = pd.DataFrame(
        {
            "sensor_set": ["mq3+mq135+dht11", "mq3+mq135+dht11"],
            "model": ["knn", "random_forest"],
            "f1_macro": [0.99, 0.40],
            "n_attempts": [10, 10],
            "chosen_params": ["[]", "[]"],
        }
    )
    assert choose_best(results, "f1_macro")["model"] == "knn"
    assert modelo_de_producao(results, "f1_macro")["model"] == "random_forest"
    assert fixar_producao({"modelo": "knn", "sensor_set": "mq3"})["modelo"] == "random_forest"


def test_floresta_final_grava_limiar_e_peso_nenhum(tmp_path):
    """O JSON do modelo servido traz o limiar do treino e a floresta sem class_weight."""
    import json

    train, test = _train_test()
    model, metadata = train_final_model(train, test, "mq3+mq135+dht11", "random_forest")

    assert model.named_steps["clf"].class_weight is None
    assert metadata["best_params"]["clf__class_weight"] is None
    assert isinstance(metadata["limiar"], float)
    assert 0.0 < metadata["limiar"] <= 1.0

    save_model(model, metadata, tmp_path / "sob_efeito.joblib")
    gravado = json.loads((tmp_path / "sob_efeito.json").read_text(encoding="utf-8"))
    assert gravado["limiar"] == metadata["limiar"]
