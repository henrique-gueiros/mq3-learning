"""Decisão pelas subidas: sopro na umidade e álcool no MQ-3.

``sob_efeito`` só quando as duas sobem. O tamanho de cada subida sai das
tentativas de treino: entre os valores observados, fica o par que mais separa
as classes (F1 macro). Empate fica com o MQ-3 mais alto e, depois, com a
umidade mais alta, para "subiu" não ser qualquer número acima de zero.

O MQ-135 entra na matriz porque a composição do ar faz parte da leitura, mas
não é condição. Há sessão de álcool em que ele quase não sobe.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import f1_score
from sklearn.utils.validation import check_is_fitted

_POSITIVO = "sob_efeito"
_NEGATIVO = "sem_efeito"
_MAX_CANDIDATOS = 40


class RegraDeSubida(BaseEstimator, ClassifierMixin):
    """Classifica pelo par de limiares de ``humidity_rise`` e ``mq3_rise``.

    Com DataFrame, lê ``humidity_rise_comeco`` e ``mq3_rise_comeco``. Com
    array, a ordem é umidade, MQ-135 e MQ-3 (a coluna do meio não entra
    na conta). As subidas são contra o começo do arquivo.
    """

    def fit(self, X, y):
        """Escolhe os dois limiares nas subidas positivas do treino."""
        umidade, mq3 = _subidas(X)
        classes = np.unique(np.asarray(y).astype(str))
        self.classes_ = classes
        self.n_features_in_ = 3 if not isinstance(X, pd.DataFrame) else X.shape[1]
        if classes.size < 2 or _POSITIVO not in set(classes):
            self.limiar_umidade_ = np.inf
            self.limiar_mq3_ = np.inf
            return self

        rotulo = np.asarray(y).astype(str)
        melhor = (-1.0, -np.inf, -np.inf)
        for limiar_umidade in _candidatos(umidade):
            umidade_ok = umidade >= limiar_umidade
            for limiar_mq3 in _candidatos(mq3):
                previsto = np.where(umidade_ok & (mq3 >= limiar_mq3), _POSITIVO, _NEGATIVO)
                nota = float(f1_score(rotulo, previsto, average="macro", zero_division=0))
                chave = (nota, float(limiar_mq3), float(limiar_umidade))
                if chave > melhor:
                    melhor = chave
        self.limiar_umidade_ = melhor[2]
        self.limiar_mq3_ = melhor[1]
        return self

    def predict(self, X):
        """``sob_efeito`` quando as duas subidas passam do limiar do treino."""
        check_is_fitted(self, ["classes_", "limiar_umidade_", "limiar_mq3_"])
        umidade, mq3 = _subidas(X)
        if not np.isfinite(self.limiar_umidade_) or not np.isfinite(self.limiar_mq3_):
            constante = str(self.classes_[0])
            return np.full(len(umidade), constante, dtype=object)
        sob = (umidade >= self.limiar_umidade_) & (mq3 >= self.limiar_mq3_)
        return np.where(sob, _POSITIVO, _NEGATIVO).astype(object)

    def predict_proba(self, X):
        """1 na classe prevista e 0 na outra, na ordem de ``classes_``."""
        check_is_fitted(self, "classes_")
        previsto = self.predict(X)
        probabilidades = np.zeros((len(previsto), len(self.classes_)))
        for indice, classe in enumerate(self.classes_):
            probabilidades[:, indice] = (previsto == classe).astype(float)
        return probabilidades


def _subidas(X) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(X, pd.DataFrame):
        faltam = [coluna for coluna in ("humidity_rise_comeco", "mq3_rise_comeco") if coluna not in X.columns]
        if faltam:
            raise ValueError(f"faltam colunas de subida: {faltam}")
        return (
            X["humidity_rise_comeco"].to_numpy(dtype=float),
            X["mq3_rise_comeco"].to_numpy(dtype=float),
        )
    matriz = np.asarray(X, dtype=float)
    if matriz.ndim != 2 or matriz.shape[1] < 3:
        raise ValueError(
            "a regra de subida espera humidity_rise_comeco, mq135_rise_comeco e mq3_rise_comeco, nesta ordem"
        )
    return matriz[:, 0], matriz[:, 2]


def _candidatos(valores: np.ndarray) -> np.ndarray:
    """Valores positivos observados. Acima de 40, fica uma grade de quantis."""
    positivos = np.unique(valores[np.isfinite(valores) & (valores > 0)])
    if positivos.size == 0:
        return np.array([np.inf])
    if positivos.size > _MAX_CANDIDATOS:
        positivos = np.unique(np.quantile(positivos, np.linspace(0, 1, _MAX_CANDIDATOS)))
    return positivos
