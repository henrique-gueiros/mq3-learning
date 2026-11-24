"""Registro de experimentos no MLflow.

Só fica ativo quando a variável ``MLFLOW_TRACKING_URI`` está definida (por
exemplo ``http://mlflow:5000`` no docker-compose, ou ``file:./mlruns`` para
testar sem servidor). Sem ela, todas as funções não fazem nada, e o pipeline
roda como antes.

- ``registrar_experimento``: um *run* por linha do ``run_experiment`` (conjunto
  de sensores x modelo), dentro de um run pai que guarda as figuras e os folds;
- ``registrar_final``: o modelo final, as métricas de teste e as figuras.
"""

from __future__ import annotations

import functools
import json
import math
import os
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

EXPERIMENTO_PADRAO = "sopro-seguro"
_PARAMS = ("sensor_set", "model", "chosen_params")
_NAO_METRICAS = {"sensor_set", "model", "chosen_params"}


def ativo() -> bool:
    """Verdadeiro se há um servidor ou pasta de rastreio configurado."""
    return bool(os.environ.get("MLFLOW_TRACKING_URI"))


def _tolerante(funcao):
    """O MLflow é auxiliar: se o servidor falhar, avisa e deixa o treino seguir."""

    @functools.wraps(funcao)
    def envolvida(*args, **kwargs):
        try:
            return funcao(*args, **kwargs)
        except Exception as erro:  # noqa: BLE001
            print(f"Aviso: não foi possível registrar no MLflow ({type(erro).__name__}: {erro})", file=sys.stderr)
            return None

    return envolvida


@_tolerante
def registrar_experimento(
    resultados: pd.DataFrame,
    folds: pd.DataFrame | None = None,
    figuras: Iterable[Path] = (),
    experimento: str = EXPERIMENTO_PADRAO,
) -> str | None:
    """Grava um run por linha de ``resultados`` e devolve o id do run pai.

    Os params são ``sensor_set``, ``model`` e ``chosen_params``; as métricas são
    todas as colunas numéricas (inclusive ``*_std``, ``f1_macro_treino`` e ``roc_auc``).
    """
    if not ativo():
        return None
    mlflow = _mlflow(experimento)
    with mlflow.start_run(run_name="comparacao_de_modelos") as pai:
        mlflow.log_param("n_runs", len(resultados))
        for linha in resultados.to_dict(orient="records"):
            with mlflow.start_run(run_name=f"{linha['sensor_set']}|{linha['model']}", nested=True):
                mlflow.log_params({nome: str(linha[nome]) for nome in _PARAMS if nome in linha})
                mlflow.log_metrics(_metricas(linha))
        if folds is not None and not folds.empty:
            _log_dataframe(mlflow, folds, "folds.csv")
        _log_dataframe(mlflow, resultados, "experiment.csv")
        for figura in figuras:
            mlflow.log_artifact(str(figura))
        return pai.info.run_id


@_tolerante
def registrar_final(
    metadata: dict,
    modelo,
    figuras: Iterable[Path] = (),
    experimento: str = EXPERIMENTO_PADRAO,
) -> str | None:
    """Grava o modelo final, as métricas de teste (prefixo ``teste_``) e as figuras."""
    if not ativo():
        return None
    mlflow = _mlflow(experimento)
    with mlflow.start_run(run_name="modelo_final") as run:
        mlflow.log_params(
            {
                "sensor_set": metadata.get("sensor_set"),
                "model": metadata.get("model"),
                "best_params": json.dumps(metadata.get("best_params", {}), default=str),
                "selected_by": metadata.get("selected_by"),
                "n_train_attempts": metadata.get("n_train_attempts"),
                "n_test_attempts": metadata.get("n_test_attempts"),
            }
        )
        metricas = {f"teste_{nome}": valor for nome, valor in metadata.get("test_metrics", {}).items()}
        if "cv_score" in metadata:
            metricas["cv_score"] = metadata["cv_score"]
        mlflow.log_metrics(_so_finitas(metricas))
        for figura in figuras:
            mlflow.log_artifact(str(figura))
        mlflow.sklearn.log_model(modelo, "model")
        return run.info.run_id


def _mlflow(experimento: str):
    import mlflow
    import mlflow.sklearn  # noqa: F401  (registra o sabor sklearn)

    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(experimento)
    return mlflow


def _metricas(linha: dict) -> dict[str, float]:
    numericas = {
        nome: valor
        for nome, valor in linha.items()
        if nome not in _NAO_METRICAS and isinstance(valor, (int, float)) and not isinstance(valor, bool)
    }
    return _so_finitas(numericas)


def _so_finitas(valores: dict) -> dict[str, float]:
    return {nome: float(v) for nome, v in valores.items() if v is not None and math.isfinite(float(v))}


def _log_dataframe(mlflow, quadro: pd.DataFrame, nome: str) -> None:
    mlflow.log_text(quadro.to_csv(index=False), nome)
