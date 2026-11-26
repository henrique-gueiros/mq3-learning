"""Avaliação por fold: desvio entre folds, treino vs validação, ROC e grupos sem vazamento.

As curvas vêm de ``conftest`` e não representam o sensor: os números aqui
não são desempenho real.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.splitting import apply_split, update_split
from src.train import (
    checar_sessoes_nos_grupos,
    model_specs,
    nested_cv_predict,
    run_experiment,
    scores_sob_efeito,
    train_final_model,
)
from src.features import feature_columns
from tests.conftest import make_feature_dataset


def _treino() -> pd.DataFrame:
    dataset = make_feature_dataset(n_participants=8, repetitions=2)
    split, _ = update_split(dataset, existing=None)
    return apply_split(dataset, split)[0]


def test_nested_cv_guarda_metricas_de_cada_fold_e_probabilidades():
    train = _treino()
    spec = model_specs(n_estimators=5)["knn"]
    X = train[feature_columns("mq3")]
    resultado = nested_cv_predict(spec, X, train["target"], train["participant_id"], n_outer=4)

    assert len(resultado.folds) == 4
    for fold in resultado.folds:
        assert {"fold", "n_validacao", "f1_macro", "f1_macro_treino", "recall_sob_efeito"} <= set(fold)
        assert 0.0 <= fold["f1_macro_treino"] <= 1.0
    assert resultado.predictions.index.equals(train.index)
    assert resultado.scores.between(0, 1).all()


def test_baseline_sem_probabilidade_util_nao_gera_auc():
    train = _treino()
    results = run_experiment(train, sensor_sets=["mq3"], models={"baseline": model_specs()["baseline"]})
    assert np.isnan(results.loc[0, "roc_auc"]) or results.loc[0, "roc_auc"] == pytest.approx(0.5)


def test_experimento_tem_desvio_entre_folds_e_f1_de_treino():
    train = _treino()
    results, folds = run_experiment(
        train, sensor_sets=["mq3"], models=model_specs(n_estimators=5), return_folds=True
    )

    for coluna in ("f1_macro_std", "balanced_accuracy_std", "recall_sob_efeito_std", "f1_macro_treino", "roc_auc"):
        assert coluna in results.columns
    assert (results["f1_macro_std"] >= 0).all()
    assert set(folds["model"]) == set(model_specs())
    assert {"sensor_set", "model", "fold", "f1_macro", "f1_macro_treino"} <= set(folds.columns)
    media = folds.groupby("model")["f1_macro_treino"].mean()
    assert results.set_index("model")["f1_macro_treino"].to_dict() == pytest.approx(media.to_dict())


def test_sessao_partida_entre_grupos_e_recusada():
    """Amostras da mesma sessão compartilham leituras: não podem cair em grupos diferentes."""
    train = _treino()
    checar_sessoes_nos_grupos(train, "participant_id")
    checar_sessoes_nos_grupos(train, "session_file")

    sessao = train["session_file"].iloc[0]
    vizinha = train.iloc[[0]].assign(attempt_id="amostra_vizinha", participant_id="outra_pessoa")
    quebrado = pd.concat([train, vizinha], ignore_index=True)
    with pytest.raises(ValueError, match=sessao):
        checar_sessoes_nos_grupos(quebrado, "participant_id")
    with pytest.raises(ValueError, match=sessao):
        run_experiment(quebrado, sensor_sets=["mq3"], models={"baseline": model_specs()["baseline"]})


def test_modelo_final_tem_auc_no_teste_quando_ha_probabilidade():
    dataset = make_feature_dataset(n_participants=8, repetitions=2)
    split, _ = update_split(dataset, existing=None)
    train, test = apply_split(dataset, split)
    model, metadata = train_final_model(train, test, "mq3", "knn")

    assert 0.0 <= metadata["test_metrics"]["roc_auc"] <= 1.0
    scores = scores_sob_efeito(model, test[feature_columns("mq3")])
    assert scores is not None and len(scores) == len(test)
