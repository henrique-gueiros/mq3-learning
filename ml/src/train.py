"""Treino, comparação de modelos e experimento por conjunto de sensores.

O rótulo é binário: ``sob_efeito`` (bebeu) ou ``sem_efeito`` (não bebeu, mesmo
com perfume ou álcool em gel). Para cada conjunto de sensores
e cada modelo, o desempenho é estimado com **validação cruzada aninhada por
grupo**, usando só o treino:

- o laço externo (``GroupKFold``) separa participantes/sessões para avaliar;
- o laço interno (``GridSearchCV`` com ``GroupKFold``) escolhe os hiperparâmetros
  usando apenas os grupos de treino daquela rodada.

Assim nenhuma pessoa avaliada participa da escolha dos hiperparâmetros. O
conjunto de teste só é usado uma vez, para o melhor modelo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src.features import SENSOR_SETS, feature_columns

MIN_GROUPS = 3
# Peso da classe sob_efeito testado no grid das árvores: nenhum, 2x, 4x ou balanceado (~9x).
PESOS_BEBIDA = [None, {"sem_efeito": 1, "sob_efeito": 2}, {"sem_efeito": 1, "sob_efeito": 4}, "balanced"]
POSITIVE = "sob_efeito"


@dataclass
class ModelSpec:
    """Um modelo candidato e a grade de hiperparâmetros a testar."""

    pipeline: Pipeline
    grid: dict


def model_specs(seed: int = 42, n_estimators: int = 100) -> dict[str, ModelSpec]:
    """Modelos comparados. ``baseline`` sempre prevê a classe mais comum.

    Todos começam com ``SimpleImputer`` porque o MQ-135 e o DHT11 podem ter
    leituras vazias. Nas árvores, o peso da bebida entra no grid
    (``PESOS_BEBIDA``): peso cheio (``balanced``, ~9x) empurra casos do meio,
    como o perfume, para ``sob_efeito``; sem peso, passa mais bebida. O grid
    escolhe o meio-termo só com o treino. Regressão logística ficou de fora
    porque a disciplina não a cobriu; o KNN entra no lugar.
    """
    imputer = ("imputer", SimpleImputer(strategy="median", keep_empty_features=True))
    return {
        "baseline": ModelSpec(Pipeline([imputer, ("clf", DummyClassifier(strategy="most_frequent"))]), {}),
        "knn": ModelSpec(
            Pipeline([imputer, ("scaler", StandardScaler()), ("clf", KNeighborsClassifier())]),
            {"clf__n_neighbors": [5, 15, 31], "clf__weights": ["uniform", "distance"]},
        ),
        "decision_tree": ModelSpec(
            Pipeline([imputer, ("clf", DecisionTreeClassifier(random_state=seed))]),
            {"clf__max_depth": [2, 3, 5, None], "clf__min_samples_leaf": [1, 3], "clf__class_weight": PESOS_BEBIDA},
        ),
        "random_forest": ModelSpec(
            Pipeline(
                [
                    imputer,
                    (
                        "clf",
                        RandomForestClassifier(n_estimators=n_estimators, random_state=seed),
                    ),
                ]
            ),
            {"clf__max_depth": [3, None], "clf__min_samples_leaf": [1, 3], "clf__class_weight": PESOS_BEBIDA},
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


@dataclass
class ResultadoCV:
    """O que a validação cruzada aninhada devolve para um modelo.

    Attributes:
        predictions: classe prevista para cada tentativa, fora da amostra.
        scores: probabilidade de ``sob_efeito`` fora da amostra (vazio se o
            modelo não tem ``predict_proba``).
        chosen_params: hiperparâmetros escolhidos em cada fold externo.
        folds: uma entrada por fold externo, com as métricas de validação e o
            F1 macro no próprio treino do fold (``f1_macro_treino``). F1 de
            treino muito acima do de validação indica overfitting; os dois
            baixos indicam underfitting.
    """

    predictions: pd.Series
    scores: pd.Series
    chosen_params: list[dict] = field(default_factory=list)
    folds: list[dict] = field(default_factory=list)


def scores_sob_efeito(model, X: pd.DataFrame) -> np.ndarray | None:
    """Probabilidade de ``sob_efeito`` para cada linha, ou ``None`` se não houver."""
    if not hasattr(model, "predict_proba"):
        return None
    classes = [str(c) for c in model.classes_]
    if POSITIVE not in classes:
        return None
    return model.predict_proba(X)[:, classes.index(POSITIVE)]


def roc_auc(y_true: pd.Series, scores: pd.Series | np.ndarray | None) -> float:
    """Área sob a curva ROC com ``sob_efeito`` como positivo (NaN se não der para calcular)."""
    if scores is None:
        return float("nan")
    scores = pd.Series(np.asarray(scores, dtype=float), index=pd.Series(y_true).index)
    valid = scores.notna()
    y = (pd.Series(y_true).astype(str) == POSITIVE)[valid]
    if y.nunique() < 2:
        return float("nan")
    return float(roc_auc_score(y, scores[valid]))


def checar_sessoes_nos_grupos(train: pd.DataFrame, group_by: str) -> None:
    """Falha se uma sessão aparece em mais de um grupo.

    Nos arquivos sem álcool cada amostra vira uma tentativa, e as janelas de
    features (``BEFORE_SECONDS`` antes e ``AFTER_SECONDS`` depois) de amostras
    vizinhas compartilham leituras. Se a mesma sessão caísse em dois grupos, o
    ``GroupKFold`` poderia pôr uma amostra no treino e a vizinha na validação.
    """
    if "session_file" not in train.columns or group_by == "session_file":
        return
    grupos_por_sessao = train.groupby("session_file")[group_by].nunique()
    partidas = sorted(str(s) for s in grupos_por_sessao[grupos_por_sessao > 1].index)
    if partidas:
        raise ValueError(
            f"sessões em mais de um {group_by} (amostras vizinhas vazariam entre treino e validação): "
            f"{partidas[:10]}"
        )


def nested_cv_predict(
    spec: ModelSpec,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    n_outer: int = 5,
    n_inner: int = 3,
    scoring: str = "f1_macro",
) -> ResultadoCV:
    """Previsões fora da amostra para cada tentativa, via validação cruzada aninhada.

    Além das previsões, guarda as métricas de cada fold externo (para o desvio
    entre folds) e o F1 macro no treino de cada fold (para comparar com a validação).
    """
    y = y.astype(str)
    labels = sorted(y.unique())
    n_outer = min(n_outer, groups.nunique())
    predictions = pd.Series(index=y.index, dtype=object)
    scores = pd.Series(np.nan, index=y.index, dtype=float)
    resultado = ResultadoCV(predictions, scores)
    for fold, (train_idx, test_idx) in enumerate(GroupKFold(n_splits=n_outer).split(X, y, groups)):
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        model, params = fit_with_search(spec, X_train, y_train, groups.iloc[train_idx], n_inner, scoring)
        fold_pred = pd.Series(model.predict(X.iloc[test_idx]), index=y.index[test_idx]).astype(str)
        predictions.iloc[test_idx] = fold_pred.to_numpy()
        fold_scores = scores_sob_efeito(model, X.iloc[test_idx])
        if fold_scores is not None:
            scores.iloc[test_idx] = fold_scores
        train_pred = pd.Series(model.predict(X_train), index=y_train.index).astype(str)
        resultado.chosen_params.append(params)
        resultado.folds.append(
            {
                "fold": fold,
                "n_treino": len(train_idx),
                "n_validacao": len(test_idx),
                **compute_metrics(y.iloc[test_idx], fold_pred, labels),
                "roc_auc": roc_auc(y.iloc[test_idx], fold_scores),
                "f1_macro_treino": float(
                    f1_score(y_train, train_pred, labels=labels, average="macro", zero_division=0)
                ),
            }
        )
    resultado.predictions = predictions.astype(str)
    return resultado


def run_experiment(
    train: pd.DataFrame,
    group_by: str = "participant_id",
    sensor_sets: list[str] | None = None,
    scoring: str = "f1_macro",
    seed: int = 42,
    models: dict[str, ModelSpec] | None = None,
    return_folds: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """Compara modelos e conjuntos de sensores com validação cruzada aninhada.

    As métricas sem sufixo juntam as previsões de todos os folds. ``<métrica>_std``
    é o desvio padrão entre os folds externos (estabilidade). ``f1_macro_treino``
    é a média do F1 no treino de cada fold: compare com ``f1_macro`` para ver
    over/underfitting. ``roc_auc`` usa a probabilidade de ``sob_efeito``.

    Args:
        models: modelos a comparar (padrão: ``model_specs(seed)``).
        return_folds: devolve também uma linha por fold externo.

    Returns:
        Uma linha por (conjunto de sensores, modelo); com ``return_folds``,
        ``(resultados, folds)``.
    """
    y = train["target"].astype(str)
    groups = train[group_by].astype(str)
    if groups.nunique() < MIN_GROUPS:
        raise ValueError(
            f"o treino precisa de pelo menos {MIN_GROUPS} valores de {group_by} "
            f"(há {groups.nunique()}); colete mais ou use --group-by session_file"
        )
    if y.nunique() < 2:
        raise ValueError(f"o treino precisa das duas classes, sob_efeito e sem_efeito (há {sorted(y.unique())})")
    checar_sessoes_nos_grupos(train, group_by)

    labels = sorted(y.unique())
    models = models or model_specs(seed)
    n_sessions = int(train["session_file"].nunique()) if "session_file" in train.columns else None
    rows: list[dict] = []
    fold_rows: list[dict] = []
    for sensor_set in sensor_sets or list(SENSOR_SETS):
        X = train[feature_columns(sensor_set)]
        for model_name, spec in models.items():
            resultado = nested_cv_predict(spec, X, y, groups, scoring=scoring)
            folds = pd.DataFrame(resultado.folds)
            metrics = compute_metrics(y, resultado.predictions, labels)
            row = {
                "sensor_set": sensor_set,
                "model": model_name,
                "n_attempts": len(y),
                "n_groups": groups.nunique(),
                "n_sessions": n_sessions,
                **metrics,
                "roc_auc": roc_auc(y, resultado.scores if resultado.scores.notna().any() else None),
            }
            for name in [*metrics, "roc_auc"]:
                row[f"{name}_std"] = float(folds[name].std(ddof=0))
            row["f1_macro_treino"] = float(folds["f1_macro_treino"].mean())
            row["f1_macro_treino_std"] = float(folds["f1_macro_treino"].std(ddof=0))
            row["chosen_params"] = json.dumps(resultado.chosen_params, default=str)
            rows.append(row)
            fold_rows.extend({"sensor_set": sensor_set, "model": model_name, **f} for f in resultado.folds)
    results = pd.DataFrame(rows)
    if return_folds:
        return results, pd.DataFrame(fold_rows)
    return results


def train_final_model(
    train: pd.DataFrame,
    test: pd.DataFrame,
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
    y = train["target"].astype(str)
    columns = feature_columns(sensor_set)
    spec = model_specs(seed)[model_name]
    model, params = fit_with_search(spec, train[columns], y, train[group_by].astype(str), 5, scoring)

    metadata = {
        "sensor_set": sensor_set,
        "model": model_name,
        "features": columns,
        "classes": [str(c) for c in model.classes_],
        "best_params": params,
        "n_train_attempts": len(y),
    }
    y_test = test["target"].astype(str)
    if len(y_test):
        predictions = pd.Series(model.predict(test[columns]), dtype=str)
        labels = sorted(set(y) | set(y_test))
        metadata["n_test_attempts"] = len(y_test)
        metadata["test_metrics"] = compute_metrics(y_test, predictions, labels)
        auc = roc_auc(y_test, scores_sob_efeito(model, test[columns]))
        metadata["test_metrics"]["roc_auc"] = None if np.isnan(auc) else auc  # null, não NaN, no JSON
        metadata["confusion_matrix"] = {
            "labels": labels,
            "matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        }
    return model, metadata


def choose_best(results: pd.DataFrame, select_by: str) -> pd.Series:
    """Melhor combinação pela métrica de validação cruzada (empate: a primeira da lista)."""
    if select_by not in results.columns:
        options = [c for c in results.columns if c.startswith(("f1", "balanced", "recall", "precision"))]
        raise ValueError(f"métrica {select_by} não existe; use uma de {options}")
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
