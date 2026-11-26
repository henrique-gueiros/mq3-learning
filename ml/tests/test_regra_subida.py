"""A decisão pede subida de umidade e de MQ-3. O MQ-135 não é condição."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.regra_subida import RegraDeSubida


def _quadro() -> pd.DataFrame:
    sem = pd.DataFrame(
        {
            "humidity_rise_comeco": [0.0, -0.2, 0.4, 0.1],
            "mq135_rise_comeco": [30.0, 40.0, 10.0, 80.0],
            "mq3_rise_comeco": [20.0, 28.0, 15.0, 35.0],
            "target": ["sem_efeito"] * 4,
        }
    )
    sob = pd.DataFrame(
        {
            "humidity_rise_comeco": [3.0, 4.5, 2.5, 6.0],
            "mq135_rise_comeco": [5.0, 20.0, 200.0, 15.0],
            "mq3_rise_comeco": [120.0, 180.0, 90.0, 250.0],
            "target": ["sob_efeito"] * 4,
        }
    )
    return pd.concat([sem, sob], ignore_index=True)


def test_so_chama_sob_efeito_quando_umidade_e_mq3_sobem():
    treino = _quadro()
    colunas = ["humidity_rise_comeco", "mq135_rise_comeco", "mq3_rise_comeco"]
    modelo = RegraDeSubida().fit(treino[colunas], treino["target"])

    casos = pd.DataFrame(
        {
            "humidity_rise_comeco": [5.0, -0.3, 4.0],
            "mq135_rise_comeco": [118.0, 6.0, 20.0],
            "mq3_rise_comeco": [28.0, 150.0, 140.0],
        }
    )
    previsto = modelo.predict(casos)

    assert list(previsto) == ["sem_efeito", "sem_efeito", "sob_efeito"]
    assert modelo.limiar_umidade_ > 0.4
    assert modelo.limiar_mq3_ > 35


def test_limiares_sao_os_das_sessoes_de_treino():
    treino = _quadro()
    colunas = ["humidity_rise_comeco", "mq135_rise_comeco", "mq3_rise_comeco"]
    X = treino[colunas].to_numpy()
    modelo = RegraDeSubida().fit(X, treino["target"])

    assert modelo.limiar_umidade_ in set(treino.loc[treino["humidity_rise_comeco"] > 0, "humidity_rise_comeco"])
    assert modelo.limiar_mq3_ in set(treino.loc[treino["mq3_rise_comeco"] > 0, "mq3_rise_comeco"])
    assert np.array_equal(modelo.predict(X), modelo.predict(treino[colunas]))
