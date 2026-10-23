"""Classificação de tentativas novas com um modelo treinado."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from src.features import compute_features


def load_model(path: Path):
    """Carrega o modelo (``.joblib``) e os metadados (``.json`` ao lado)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"modelo não encontrado: {path}; rode 'train' antes")
    metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    return joblib.load(path), metadata


def predict_attempts(readings: pd.DataFrame, model_path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Classifica cada tentativa das leituras (já validadas).

    O cálculo de features é o mesmo do treino, e o pré-processamento fica
    dentro do ``Pipeline`` salvo.

    Returns:
        ``(previsões, avisos)``: uma linha por tentativa com ``prediction`` e,
        quando o modelo permite, ``prob_<classe>``.
    """
    model, metadata = load_model(model_path)
    features, warnings = compute_features(readings)
    if features.empty:
        return pd.DataFrame(columns=["attempt_id", "prediction"]), warnings

    X = features[metadata["features"]]
    result = pd.DataFrame({"attempt_id": features["attempt_id"], "prediction": model.predict(X)})
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X)
        for index, label in enumerate(model.classes_):
            result[f"prob_{label}"] = probabilities[:, index]
    return result, warnings
