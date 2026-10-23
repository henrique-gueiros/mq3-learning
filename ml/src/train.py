"""Treino, comparação de modelos e experimento por conjunto de sensores.

Para cada tarefa (``3classes``, ``etapa1`` ou ``etapa2``), cada conjunto de
sensores e cada modelo, o desempenho é estimado com **validação cruzada
aninhada por grupo**, usando só o treino:

- o laço externo (``GroupKFold``) separa participantes/sessões para avaliar;
- o laço interno (``GridSearchCV`` com ``GroupKFold``) escolhe os hiperparâmetros
  usando apenas os grupos de treino daquela rodada.

Assim nenhuma pessoa avaliada participa da escolha dos hiperparâmetros. O
conjunto de teste só é usado uma vez, para o melhor modelo de cada tarefa.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src.features import SENSOR_SETS, feature_columns, task_target

MIN_GROUPS = 3


@dataclass
class ModelSpec:
    """Um modelo candidato e a grade de hiperparâmetros a testar."""

    pipeline: Pipeline
    grid: dict


def model_specs(seed: int = 42, n_estimators: int = 100) -> dict[str, ModelSpec]:
    """Modelos comparados. ``baseline`` sempre prevê a classe mais comum.

    Todos começam com ``SimpleImputer`` porque o MQ-135 e o DHT11 podem ter
    leituras vazias. ``class_weight="balanced"`` compensa classes desbalanceadas.
    """
    imputer = ("imputer", SimpleImputer(strategy="median", keep_empty_features=True))
    return {
        "baseline": ModelSpec(Pipeline([imputer, ("clf", DummyClassifier(strategy="most_frequent"))]), {}),
        "logistic_regression": ModelSpec(
            Pipeline(
                [
                    imputer,
                    ("scaler", StandardScaler()),
                    ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
                ]
            ),
            {"clf__C": [0.1, 1.0, 10.0]},
        ),
        "decision_tree": ModelSpec(
            Pipeline([imputer, ("clf", DecisionTreeClassifier(class_weight="balanced", random_state=seed))]),
            {"clf__max_depth": [2, 3, 5, None], "clf__min_samples_leaf": [1, 3]},
        ),
        "random_forest": ModelSpec(
            Pipeline(
                [
                    imputer,
                    (
                        "clf",
                        RandomForestClassifier(
                            n_estimators=n_estimators, class_weight="balanced", random_state=seed
                        ),
                    ),
                ]
            ),
            {"clf__max_depth": [3, None], "clf__min_samples_leaf": [1, 3]},
        ),
    }


def compute_metrics(y_true: pd.Series, y_pred: pd.Series, labels: list[str]) -> dict:
    """F1 macro, acurácia balanceada e precisão/recall de cada classe."""
    metrics = {
        "f1_macro": f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
    }
    recalls = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    precisions = precision_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    for label, recall, precision in zip(labels, recalls, precisions):
        metrics[f"recall_{label}"] = float(recall)
        metrics[f"precision_{label}"] = float(precision)
    return {key: float(value) for key, value in metrics.items()}


def fit_with_search(
    spec: ModelSpec, X: pd.DataFrame, y: pd.Series, groups: pd.Series, n_inner: int, scoring: str
) -> tuple[Pipeline, dict]:
    """Ajusta o modelo escolhendo hiperparâmetros por validação cruzada por grupo."""
    n_inner = min(n_inner, groups.nunique())
    if not spec.grid or n_inner < 2:
        return clone(spec.pipeline).fit(X, y), {}
    search = GridSearchCV(clone(spec.pipeline), spec.grid, scoring=scoring, cv=GroupKFold(n_splits=n_inner))
    search.fit(X, y, groups=groups)
    return search.best_estimator_, search.best_params_


def nested_cv_predict(
    spec: ModelSpec,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    n_outer: int = 5,
    n_inner: int = 3,
    scoring: str = "f1_macro",
) -> tuple[pd.Series, list[dict]]:
    """Previsões fora da amostra para cada tentativa, via validação cruzada aninhada."""
    n_outer = min(n_outer, groups.nunique())
    predictions = pd.Series(index=y.index, dtype=object)
    chosen_params: list[dict] = []
    for train_idx, test_idx in GroupKFold(n_splits=n_outer).split(X, y, groups):
        model, params = fit_with_search(
            spec, X.iloc[train_idx], y.iloc[train_idx], groups.iloc[train_idx], n_inner, scoring
        )
        predictions.iloc[test_idx] = model.predict(X.iloc[test_idx])
        chosen_params.append(params)
    return predictions.astype(str), chosen_params


def run_experiment(
    train: pd.DataFrame,
    task: str,
    group_by: str = "participant_id",
    sensor_sets: list[str] | None = None,
    scoring: str = "f1_macro",
    seed: int = 42,
    models: dict[str, ModelSpec] | None = None,
) -> pd.DataFrame:
    """Compara modelos e conjuntos de sensores com validação cruzada aninhada.

    Args:
        models: modelos a comparar (padrão: ``model_specs(seed)``).

    Returns:
        Uma linha por (conjunto de sensores, modelo) com as métricas de validação cruzada.
    """
    subset, y = task_target(train, task)
    groups = subset[group_by].astype(str)
    if groups.nunique() < MIN_GROUPS:
        raise ValueError(
            f"a tarefa {task} precisa de pelo menos {MIN_GROUPS} valores de {group_by} no treino "
            f"(há {groups.nunique()}); colete mais ou use --group-by session_id"
        )
    if y.nunique() < 2:
        raise ValueError(f"a tarefa {task} precisa de pelo menos 2 classes no treino (há {sorted(y.unique())})")

    labels = sorted(y.unique())
    models = models or model_specs(seed)
    rows: list[dict] = []
    for sensor_set in sensor_sets or list(SENSOR_SETS):
        X = subset[feature_columns(sensor_set)]
        for model_name, spec in models.items():
            predictions, params = nested_cv_predict(spec, X, y, groups, scoring=scoring)
            rows.append(
                {
                    "task": task,
                    "sensor_set": sensor_set,
                    "model": model_name,
                    "n_attempts": len(y),
                    "n_groups": groups.nunique(),
                    **compute_metrics(y, predictions, labels),
                    "chosen_params": json.dumps(params, default=str),
                }
            )
    return pd.DataFrame(rows)


def train_final_model(
    train: pd.DataFrame,
    test: pd.DataFrame,
    task: str,
    sensor_set: str,
    model_name: str,
    group_by: str = "participant_id",
    scoring: str = "f1_macro",
    seed: int = 42,
) -> tuple[Pipeline, dict]:
    """Treina o modelo escolhido em todo o treino e avalia uma vez no teste.

    Returns:
        ``(modelo, metadados)``; os metadados têm features, classes,
        hiperparâmetros, métricas de teste e matriz de confusão.
    """
    subset, y = task_target(train, task)
    columns = feature_columns(sensor_set)
    spec = model_specs(seed)[model_name]
    model, params = fit_with_search(spec, subset[columns], y, subset[group_by].astype(str), 5, scoring)

    metadata = {
        "task": task,
        "sensor_set": sensor_set,
        "model": model_name,
        "features": columns,
        "classes": [str(c) for c in model.classes_],
        "best_params": params,
        "n_train_attempts": len(y),
    }
    test_subset, y_test = task_target(test, task)
    if len(y_test):
        predictions = pd.Series(model.predict(test_subset[columns]), dtype=str)
        labels = sorted(set(y) | set(y_test))
        metadata["n_test_attempts"] = len(y_test)
        metadata["test_metrics"] = compute_metrics(y_test, predictions, labels)
        metadata["confusion_matrix"] = {
            "labels": labels,
            "matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        }
    return model, metadata


def choose_best(results: pd.DataFrame, select_by: str) -> pd.Series:
    """Melhor combinação pela métrica de validação cruzada (empate: a primeira da lista)."""
    if select_by not in results.columns:
        options = [c for c in results.columns if c.startswith(("f1", "balanced", "recall", "precision"))]
        raise ValueError(f"métrica {select_by} não existe nesta tarefa; use uma de {options}")
    candidates = results[results["model"] != "baseline"]
    return candidates.loc[candidates[select_by].astype(float).idxmax()]


def save_model(model: Pipeline, metadata: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    path.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8"
    )


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    return str(value)
