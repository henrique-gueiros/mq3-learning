"""Rastreio no MLflow: só liga com MLFLOW_TRACKING_URI; sem a variável não faz nada."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src import figuras, rastreio
from src.features import feature_columns
from src.splitting import apply_split, update_split
from src.train import model_specs, run_experiment, train_final_model
from tests.conftest import make_feature_dataset


@pytest.fixture
def dados():
    dataset = make_feature_dataset(n_participants=8, repetitions=1)
    split, _ = update_split(dataset, existing=None)
    return apply_split(dataset, split)


def test_sem_variavel_e_no_op(monkeypatch, tmp_path, dados):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    train, _ = dados
    resultados = run_experiment(train, sensor_sets=["mq3"], models={"baseline": model_specs()["baseline"]})

    assert rastreio.ativo() is False
    assert rastreio.registrar_experimento(resultados) is None
    assert rastreio.registrar_final({"test_metrics": {}}, object(), []) is None
    assert not (tmp_path / "mlruns").exists()


def test_registra_um_run_por_linha_do_experimento(monkeypatch, tmp_path, dados):
    import mlflow

    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file:{tmp_path / 'mlruns'}")
    train, _ = dados
    resultados, folds = run_experiment(
        train, sensor_sets=["mq3", "mq3+mq135"], models=model_specs(n_estimators=5), return_folds=True
    )
    grafico = figuras.barras_por_modelo(resultados, tmp_path / "f1.png")

    rastreio.registrar_experimento(resultados, folds=folds, figuras=[grafico], experimento="teste")

    experimento = mlflow.get_experiment_by_name("teste")
    runs = mlflow.search_runs([experimento.experiment_id])
    runs = runs[runs["tags.mlflow.parentRunId"].notna()]
    assert len(runs) == len(resultados)
    linha = resultados.iloc[0]
    run = runs[(runs["params.sensor_set"] == linha["sensor_set"]) & (runs["params.model"] == linha["model"])].iloc[0]
    assert run["metrics.f1_macro"] == pytest.approx(linha["f1_macro"])
    assert run["metrics.f1_macro_std"] == pytest.approx(linha["f1_macro_std"])
    assert run["params.chosen_params"] == linha["chosen_params"]
    pai = mlflow.search_runs([experimento.experiment_id])
    pai = pai[pai["tags.mlflow.parentRunId"].isna()].iloc[0]
    arquivos = [a.path for a in mlflow.MlflowClient().list_artifacts(pai["run_id"])]
    assert "f1.png" in arquivos and "folds.csv" in arquivos


def test_registra_modelo_final_com_metricas_e_figuras(monkeypatch, tmp_path, dados):
    import mlflow

    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file:{tmp_path / 'mlruns'}")
    train, test = dados
    modelo, metadata = train_final_model(train, test, "mq3", "decision_tree")
    matriz = figuras.matriz_confusao(
        metadata["confusion_matrix"]["labels"], metadata["confusion_matrix"]["matrix"], tmp_path / "matriz.png"
    )

    rastreio.registrar_final(metadata, modelo, [matriz], experimento="teste")

    experimento = mlflow.get_experiment_by_name("teste")
    run = mlflow.search_runs([experimento.experiment_id]).iloc[0]
    assert run["metrics.teste_f1_macro"] == pytest.approx(metadata["test_metrics"]["f1_macro"])
    assert run["params.model"] == "decision_tree"
    assert run["params.best_params"] == json.dumps(metadata["best_params"])
    arquivos = [a.path for a in mlflow.MlflowClient().list_artifacts(run["run_id"])]
    assert "matriz.png" in arquivos and "model" in arquivos


def test_servidor_fora_do_ar_nao_derruba_o_treino(monkeypatch, capsys):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:1")
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_TIMEOUT", "2")

    assert rastreio.registrar_experimento(pd.DataFrame([{"sensor_set": "mq3", "model": "m", "chosen_params": "[]"}])) is None
    assert "Aviso: não foi possível registrar no MLflow" in capsys.readouterr().err
