"""Figuras da avaliação. Dados de ``conftest``: as curvas não são desempenho real."""

from __future__ import annotations

import pandas as pd

from src import figuras
from src.features import feature_columns
from src.splitting import apply_split, update_split
from src.train import model_specs, run_experiment
from tests.conftest import make_feature_dataset

_PNG = b"\x89PNG"


def _e_png(path) -> bool:
    return path.exists() and path.read_bytes()[:4] == _PNG


def test_matriz_de_confusao_e_roc(tmp_path):
    matriz = figuras.matriz_confusao(["sem_efeito", "sob_efeito"], [[8, 2], [1, 4]], tmp_path / "matriz.png")
    y = pd.Series(["sem_efeito", "sem_efeito", "sob_efeito", "sob_efeito"])
    roc = figuras.curva_roc(y, [0.1, 0.6, 0.4, 0.9], tmp_path / "roc.png")

    assert _e_png(matriz) and _e_png(roc)


def test_roc_sem_as_duas_classes_nao_gera_arquivo(tmp_path):
    assert figuras.curva_roc(pd.Series(["sem_efeito"] * 3), [0.1, 0.2, 0.3], tmp_path / "roc.png") is None


def test_barras_treino_validacao_e_curva_de_aprendizado(tmp_path):
    dataset = make_feature_dataset(n_participants=8, repetitions=1)
    split, _ = update_split(dataset, existing=None)
    train, _ = apply_split(dataset, split)
    results, folds = run_experiment(
        train, sensor_sets=["mq3", "mq3+mq135"], models=model_specs(n_estimators=5), return_folds=True
    )

    barras = figuras.barras_por_modelo(results, tmp_path / "f1.png")
    treino_val = figuras.treino_vs_validacao(folds, tmp_path / "treino_val.png")
    spec = model_specs(n_estimators=5)["knn"]
    curva = figuras.curva_aprendizado(
        spec.pipeline,
        train[feature_columns("mq3")],
        train["target"],
        train["participant_id"],
        tmp_path / "aprendizado.png",
        n_splits=3,
    )

    assert _e_png(barras) and _e_png(treino_val) and _e_png(curva)
