"""Validação deixando um arquivo de fora (leave-one-file-out).

Para cada CSV de sessão, o modelo é ajustado com todos os outros (o grid search
escolhe os hiperparâmetros só com eles, por ``GroupKFold`` por arquivo) e testa
no arquivo que ficou de fora. Assim nenhuma leitura do arquivo testado, nem as
cópias dela, aparece no ajuste.

Uso, de dentro de ``ml/`` e com o ``prepare`` já rodado::

    python -m src.por_arquivo
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.features import SENSOR_SET_EXECUCAO, feature_columns
from src.train import compute_metrics, fit_with_search, model_specs

MODELOS_PADRAO = ("logistic_regression", "decision_tree", "random_forest")


def avaliar_por_arquivo(
    dataset: pd.DataFrame,
    modelos: list[str] | tuple[str, ...] = MODELOS_PADRAO,
    sensor_set: str = SENSOR_SET_EXECUCAO,
    seed: int = 42,
    n_estimators: int = 100,
    n_inner: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Testa cada arquivo com um modelo ajustado só nos outros.

    Returns:
        ``(por_arquivo, previsoes)``: uma linha por (modelo, arquivo de fora,
        classe real) com acertos e hiperparâmetros; e a previsão de cada
        tentativa, uma vez por modelo.
    """
    specs = model_specs(seed, n_estimators=n_estimators)
    colunas = feature_columns(sensor_set)
    linhas: list[dict] = []
    previsoes: list[pd.DataFrame] = []
    for nome in modelos:
        for arquivo in sorted(dataset["session_file"].unique()):
            treino = dataset[dataset["session_file"] != arquivo]
            teste = dataset[dataset["session_file"] == arquivo]
            if treino["target"].nunique() < 2:
                continue
            modelo, params = fit_with_search(
                specs[nome],
                treino[colunas],
                treino["target"].astype(str),
                treino["session_file"].astype(str),
                n_inner,
                "f1_macro",
            )
            pred = pd.Series(modelo.predict(teste[colunas]), index=teste.index).astype(str)
            previsoes.append(
                pd.DataFrame(
                    {
                        "modelo": nome,
                        "session_file": arquivo,
                        "attempt_id": teste["attempt_id"],
                        "target": teste["target"].astype(str),
                        "prediction": pred,
                    }
                )
            )
            for classe, parte in teste.groupby(teste["target"].astype(str)):
                acertos = int((pred.loc[parte.index] == classe).sum())
                linhas.append(
                    {
                        "modelo": nome,
                        "arquivo_de_fora": arquivo,
                        "classe_real": classe,
                        "n": len(parte),
                        "acertos": acertos,
                        "acerto": acertos / len(parte),
                        "parametros": json.dumps(params, default=str),
                        "arquivos_no_treino": sorted(treino["session_file"].unique()),
                    }
                )
    return pd.DataFrame(linhas), pd.concat(previsoes, ignore_index=True)


def resumo_por_modelo(previsoes: pd.DataFrame) -> pd.DataFrame:
    """Métricas juntando as previsões de todos os arquivos de fora, por modelo."""
    linhas = []
    for nome, parte in previsoes.groupby("modelo"):
        labels = sorted(parte["target"].unique())
        linhas.append({"modelo": nome, "n": len(parte), **compute_metrics(parte["target"], parte["prediction"], labels)})
    return pd.DataFrame(linhas)


def main() -> None:
    """Junta treino e teste do ``prepare``, avalia e grava em ``reports/``."""
    from src.paths import ProjectPaths

    paths = ProjectPaths(Path(__file__).resolve().parents[1])
    dataset = pd.concat([pd.read_csv(paths.train), pd.read_csv(paths.test)], ignore_index=True)
    por_arquivo, previsoes = avaliar_por_arquivo(dataset)
    resumo = resumo_por_modelo(previsoes)
    saida = paths.reports_dir
    por_arquivo.drop(columns="arquivos_no_treino").to_csv(saida / "por_arquivo.csv", index=False)
    resumo.to_csv(saida / "por_arquivo_resumo.csv", index=False)
    print(resumo.round(3).to_string(index=False))
    print(por_arquivo.drop(columns=["arquivos_no_treino", "parametros"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
