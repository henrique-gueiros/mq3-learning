"""A inferência usa o limiar gravado no JSON; sem ele, vale o predict do modelo."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.pipeline import Pipeline

from src.data_validation import validate_readings
from src.features import feature_columns
from src.inference import predict_attempts
from src.train import save_model
from tests.conftest import BLOW_START_S, make_session


class _ChanceFixa(BaseEstimator, ClassifierMixin):
    """Probabilidade 0,3 de sob_efeito. O predict padrão (corte 0,5) diz sem_efeito."""

    def fit(self, X, y):
        self.classes_ = np.array(["sem_efeito", "sob_efeito"])
        self.n_features_in_ = np.asarray(X).shape[1]
        return self

    def predict_proba(self, X):
        n = len(X)
        return np.column_stack([np.full(n, 0.7), np.full(n, 0.3)])

    def predict(self, X):
        return np.array(["sem_efeito"] * len(X))


def _gravar(tmp_path, limiar: float | None):
    session = validate_readings(make_session("drink", seed=3))
    session.insert(0, "session_file", "nova.csv")
    attempts = pd.DataFrame(
        {"attempt_id": ["t1"], "session_file": ["nova.csv"], "blow_start_s": [BLOW_START_S]}
    )
    columns = feature_columns("mq3+mq135+dht11")
    model = Pipeline([("clf", _ChanceFixa())])
    model.fit(np.zeros((2, len(columns))), ["sem_efeito", "sob_efeito"])
    metadata = {"features": columns, "classes": ["sem_efeito", "sob_efeito"]}
    if limiar is not None:
        metadata["limiar"] = limiar
    save_model(model, metadata, tmp_path / "sob_efeito.joblib")
    return session, attempts


def test_limiar_baixo_classifica_probabilidade_0_3_como_sob_efeito(tmp_path):
    """Quebra se a inferência ignorar o limiar e usar o predict (corte 0,5)."""
    session, attempts = _gravar(tmp_path, limiar=0.2)
    predictions, _ = predict_attempts(session, attempts, tmp_path / "sob_efeito.joblib")
    assert predictions.loc[0, "prediction"] == "sob_efeito"


def test_sem_limiar_no_json_usa_o_predict(tmp_path):
    """Modelo antigo, sem a chave, continua no corte padrão do scikit-learn."""
    session, attempts = _gravar(tmp_path, limiar=None)
    predictions, _ = predict_attempts(session, attempts, tmp_path / "sob_efeito.joblib")
    assert predictions.loc[0, "prediction"] == "sem_efeito"
