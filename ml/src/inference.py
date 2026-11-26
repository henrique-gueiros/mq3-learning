"""Classificação de tentativas novas com um modelo treinado."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from src.features import assign_phases, compute_features
from src.limiar import classe_pelo_limiar, probabilidade_sob_efeito


def load_model(path: Path):
    """Carrega o modelo (``.joblib``) e os metadados (``.json`` ao lado)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"modelo não encontrado: {path}; rode 'train' antes")
    metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    return joblib.load(path), metadata


def predict_attempts(
    readings: pd.DataFrame, attempts: pd.DataFrame, model_path: Path
) -> tuple[pd.DataFrame, list[str]]:
    """Classifica tentativas a partir das leituras de sessão já validadas.

    ``attempts`` precisa de ``attempt_id``, ``session_file`` e ``blow_start_s``
    (``blow_end_s`` é opcional); não precisa de condição. O cálculo de features é
    o mesmo do treino, e o pré-processamento fica dentro do ``Pipeline`` salvo.
    Se o JSON ao lado do modelo tiver ``limiar``, a classe é
    ``sob_efeito`` quando ``P(sob_efeito) >= limiar``. Sem essa chave, vale o
    ``predict`` do modelo (corte 0,5).

    Returns:
        ``(previsões, avisos)``: uma linha por tentativa com ``prediction`` e,
        quando o modelo permite, ``prob_<classe>``.
    """
    model, metadata = load_model(model_path)
    phased, warnings = assign_phases(readings, attempts)
    features, feature_warnings = compute_features(phased)
    warnings += feature_warnings
    if features.empty:
        return pd.DataFrame(columns=["attempt_id", "prediction"]), warnings

    X = features[metadata["features"]]
    limiar = metadata.get("limiar")
    if limiar is not None and hasattr(model, "predict_proba"):
        prediction = classe_pelo_limiar(probabilidade_sob_efeito(model, X), float(limiar))
    else:
        prediction = model.predict(X)
    result = pd.DataFrame({"attempt_id": features["attempt_id"], "prediction": prediction})
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X)
        for index, label in enumerate(model.classes_):
            result[f"prob_{label}"] = probabilities[:, index]
    return result, warnings
