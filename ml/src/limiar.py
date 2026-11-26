"""Limiar de P(sob_efeito) escolhido só com o treino.

O corte padrão do scikit-learn é 0,5. Com muito mais linhas ``sem_efeito`` do
que ``sob_efeito``, esse corte empurra vapor (perfume, álcool no ar) para
``sob_efeito``. O limiar fica no maior recall de bebida que ainda acerta pelo
menos ``MINIMO_SEM_EFEITO`` das linhas ``sem_efeito``, medido fora da amostra
do próprio treino: um arquivo de cada vez.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold

MINIMO_SEM_EFEITO = 0.95
POSITIVE = "sob_efeito"


def probabilidade_sob_efeito(modelo, X: pd.DataFrame) -> np.ndarray:
    """Coluna de ``predict_proba`` da classe ``sob_efeito``."""
    classes = [str(c) for c in modelo.classes_]
    return modelo.predict_proba(X)[:, classes.index(POSITIVE)]


def escolher_limiar(
    y: pd.Series, prob_sob: np.ndarray, minimo_sem_efeito: float = MINIMO_SEM_EFEITO
) -> float:
    """Limiar de ``P(sob_efeito)`` com maior recall de bebida e acerto ``sem_efeito`` >= ``minimo``.

    Empate no recall: fica o maior limiar (menos alarme falso). Sem nenhum que
    cumpra o mínimo, devolve 0,5 (o padrão do scikit-learn).
    """
    y = np.asarray(pd.Series(y).astype(str))
    prob_sob = np.asarray(prob_sob, dtype=float)
    sob, sem = prob_sob[y == "sob_efeito"], prob_sob[y == "sem_efeito"]
    melhor, melhor_recall = 0.5, -1.0
    for limiar in sorted(set(np.round(prob_sob, 6))):
        if sem.size and (sem < limiar).mean() < minimo_sem_efeito:
            continue
        recall = (sob >= limiar).mean() if sob.size else 0.0
        if recall > melhor_recall or (recall == melhor_recall and limiar > melhor):
            melhor, melhor_recall = float(limiar), recall
    return melhor


def classe_pelo_limiar(prob_sob: np.ndarray, limiar: float) -> np.ndarray:
    """``sob_efeito`` quando ``P(sob_efeito) >= limiar``; senão ``sem_efeito``."""
    return np.where(np.asarray(prob_sob, dtype=float) >= limiar, POSITIVE, "sem_efeito")


def limiar_no_treino(modelo, treino: pd.DataFrame, colunas: list[str], n_inner: int) -> float:
    """Limiar com probabilidades fora da amostra do próprio treino (``GroupKFold`` por arquivo).

    Fold interno cujo treino tem uma classe só (por exemplo, sem bebida) não
    dá probabilidade: as linhas dele ficam de fora da escolha do limiar.
    """
    grupos = treino["session_file"].astype(str)
    y = treino["target"].astype(str)
    n = min(n_inner, grupos.nunique())
    if n < 2:
        return 0.5
    prob = pd.Series(np.nan, index=treino.index)
    for idx_treino, idx_validacao in GroupKFold(n_splits=n).split(treino, y, grupos):
        y_fold = y.iloc[idx_treino]
        if y_fold.nunique() < 2:
            continue
        ajustado = clone(modelo).fit(treino[colunas].iloc[idx_treino], y_fold)
        prob.iloc[idx_validacao] = probabilidade_sob_efeito(ajustado, treino[colunas].iloc[idx_validacao])
    validas = prob.notna()
    if not validas.any():
        return 0.5
    return escolher_limiar(y[validas], prob[validas].to_numpy())
