"""Validação deixando um arquivo (ou um dia) de fora, com variações de treino.

Para cada grupo de teste (um CSV de sessão, ou um dia de coleta), o modelo é
ajustado só com os outros. O grid search escolhe os hiperparâmetros dentro
deles, por ``GroupKFold`` por arquivo, e o teste roda no grupo que ficou de
fora. Nenhuma leitura do grupo testado, nem as cópias dela, entra no ajuste.

O **teste nunca é reamostrado**: cada arquivo entra inteiro, com a proporção
real de classes. Só o treino muda entre as variações:

- ``FEATURES``: ``todas`` (níveis e variações) ou ``variacao`` (sem os níveis
  absolutos ``*_before`` e ``*_peak``, que mudam com o dia e o ambiente);
- treino:
  - ``grid``: o grid escolhe o peso da bebida (nenhum, 2x, 4x ou balanceado), que é o padrão do pipeline;
  - ``sem_peso``: peso fixo em nenhum;
  - ``corte``: no máximo ``CORTE_POR_ARQUIVO`` tentativas ``sem_efeito`` por arquivo, espaçadas no tempo, depois o grid;
  - ``sem_peso_limiar``: sem peso e com o limiar escolhido no treino;
  - ``limiar``: o grid e, em seguida, o limiar de probabilidade escolhido no próprio treino (validação cruzada por arquivo). É o limiar de maior recall de bebida que mantém o acerto ``sem_efeito`` em pelo menos ``MINIMO_SEM_EFEITO``.

Uso, de dentro de ``ml/`` e com o ``prepare`` já rodado::

    python -m src.por_arquivo
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from src.features import SENSOR_SET_EXECUCAO, feature_columns
from src.limiar import (
    MINIMO_SEM_EFEITO,
    escolher_limiar,
    limiar_no_treino,
    probabilidade_sob_efeito,
)
from src.train import compute_metrics, fit_with_search, model_specs

MODELOS_PADRAO = ("knn", "decision_tree", "random_forest")
BALANCEAMENTOS = ("grid", "sem_peso", "corte", "limiar", "sem_peso_limiar")
CORTE_POR_ARQUIVO = 300
_limiar_no_treino = limiar_no_treino
_prob_sob = probabilidade_sob_efeito

_TODAS = feature_columns(SENSOR_SET_EXECUCAO)
FEATURES = {
    "todas": _TODAS,
    "variacao": [c for c in _TODAS if not (c.endswith("_before") or c.endswith("_peak"))],
}


def _ordem(attempt_id: str) -> int:
    achado = re.search(r"_s(\d+)$", str(attempt_id))
    return int(achado.group(1)) if achado else 0


def cortar_por_arquivo(treino: pd.DataFrame, maximo: int = CORTE_POR_ARQUIVO) -> pd.DataFrame:
    """Limita as tentativas ``sem_efeito`` de cada arquivo a ``maximo``.

    As que ficam são espaçadas ao longo do arquivo (do começo ao fim), e não
    sorteadas: amostras vizinhas são quase iguais, então o espaçamento guarda
    mais variedade. ``sob_efeito`` fica inteiro.
    """
    partes = []
    for (_, alvo), parte in treino.groupby(["session_file", treino["target"].astype(str)], sort=False):
        if alvo != "sem_efeito" or len(parte) <= maximo:
            partes.append(parte)
            continue
        ordenada = parte.iloc[np.argsort(parte["attempt_id"].map(_ordem).to_numpy(), kind="stable")]
        posicoes = np.unique(np.linspace(0, len(ordenada) - 1, maximo).round().astype(int))
        partes.append(ordenada.iloc[posicoes])
    return pd.concat(partes).sort_index()


def _grupo(dataset: pd.DataFrame, grupo: str) -> pd.Series:
    if grupo == "arquivo":
        return dataset["session_file"].astype(str)
    if grupo == "dia":
        return dataset["session_file"].astype(str).str.slice(0, 10)
    raise ValueError(f"grupo desconhecido: {grupo}; use 'arquivo' ou 'dia'")


def avaliar_por_arquivo(
    dataset: pd.DataFrame,
    modelos: list[str] | tuple[str, ...] = MODELOS_PADRAO,
    colunas: list[str] | None = None,
    balanceamento: str = "grid",
    grupo: str = "arquivo",
    seed: int = 42,
    n_estimators: int = 100,
    n_inner: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Testa cada grupo (arquivo ou dia) com um modelo ajustado só nos outros.

    Returns:
        ``(por_grupo, previsoes)``: uma linha por (modelo, grupo de fora,
        arquivo, classe real) com acertos e hiperparâmetros; e a previsão de
        cada tentativa, uma vez por modelo.
    """
    if balanceamento not in BALANCEAMENTOS:
        raise ValueError(f"balanceamento desconhecido: {balanceamento}; use um de {BALANCEAMENTOS}")
    colunas = colunas or FEATURES["todas"]
    specs = model_specs(seed, n_estimators=n_estimators)
    grupos = _grupo(dataset, grupo)
    linhas: list[dict] = []
    previsoes: list[pd.DataFrame] = []
    for nome in modelos:
        spec = specs[nome]
        if balanceamento in ("sem_peso", "sem_peso_limiar") and "clf__class_weight" in spec.grid:
            spec = replace(spec, grid={**spec.grid, "clf__class_weight": [None]})
        for de_fora in sorted(grupos.unique()):
            treino = dataset[grupos != de_fora]
            teste = dataset[grupos == de_fora]
            if balanceamento == "corte":
                treino = cortar_por_arquivo(treino)
            if treino["target"].nunique() < 2:
                continue
            modelo, params = fit_with_search(
                spec,
                treino[colunas],
                treino["target"].astype(str),
                treino["session_file"].astype(str),
                n_inner,
                "f1_macro",
            )
            if balanceamento in ("limiar", "sem_peso_limiar"):
                limiar = _limiar_no_treino(modelo, treino, colunas, n_inner)
                params = {**params, "limiar": limiar}
                prob = _prob_sob(modelo, teste[colunas])
                pred = pd.Series(np.where(prob >= limiar, "sob_efeito", "sem_efeito"), index=teste.index)
            else:
                pred = pd.Series(modelo.predict(teste[colunas]), index=teste.index).astype(str)
            previsoes.append(
                pd.DataFrame(
                    {
                        "modelo": nome,
                        "grupo_de_fora": de_fora,
                        "session_file": teste["session_file"],
                        "attempt_id": teste["attempt_id"],
                        "target": teste["target"].astype(str),
                        "prediction": pred,
                    }
                )
            )
            chaves = [teste["session_file"].astype(str), teste["target"].astype(str)]
            for (arquivo, classe), parte in teste.groupby(chaves):
                acertos = int((pred.loc[parte.index] == classe).sum())
                linhas.append(
                    {
                        "modelo": nome,
                        "grupo_de_fora": de_fora,
                        "arquivo_de_fora": arquivo if grupo == "arquivo" else de_fora,
                        "arquivo": arquivo,
                        "classe_real": classe,
                        "n": len(parte),
                        "acertos": acertos,
                        "acerto": acertos / len(parte),
                        "n_treino": len(treino),
                        "parametros": json.dumps(params, default=str),
                        "arquivos_no_treino": sorted(treino["session_file"].unique()),
                    }
                )
    return pd.DataFrame(linhas), pd.concat(previsoes, ignore_index=True)


def resumo_por_modelo(previsoes: pd.DataFrame) -> pd.DataFrame:
    """Métricas juntando as previsões de todos os grupos de fora, por modelo."""
    linhas = []
    for nome, parte in previsoes.groupby("modelo"):
        labels = sorted(parte["target"].unique())
        linhas.append({"modelo": nome, "n": len(parte), **compute_metrics(parte["target"], parte["prediction"], labels)})
    return pd.DataFrame(linhas)


def resumo_por_arquivo(por_arquivo: pd.DataFrame) -> pd.DataFrame:
    """Média do acerto por arquivo (cada arquivo pesa igual) e o pior arquivo, por modelo.

    É o critério de escolha: com 7.724 linhas de um só arquivo de ambiente, o
    F1 que junta tudo esconde um arquivo pequeno (perfume) que o modelo erra.
    """
    chave = "arquivo" if "arquivo" in por_arquivo.columns else "arquivo_de_fora"
    linhas = []
    for nome, parte in por_arquivo.groupby("modelo"):
        pior = parte.loc[parte["acerto"].idxmin()]
        linhas.append(
            {
                "modelo": nome,
                "media_por_arquivo": float(parte["acerto"].mean()),
                "pior_arquivo": pior[chave],
                "pior_acerto": float(pior["acerto"]),
            }
        )
    return pd.DataFrame(linhas)


def comparar_variacoes(
    dataset: pd.DataFrame,
    modelos: list[str] | tuple[str, ...] = MODELOS_PADRAO,
    grupos: tuple[str, ...] = ("arquivo", "dia"),
    n_estimators: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Roda todas as combinações de grupo, features e balanceamento.

    Returns:
        ``(tabela, detalhes)``: uma linha por combinação e modelo com as
        métricas gerais, a média por arquivo e o pior arquivo; e o acerto de
        cada arquivo em cada combinação.
    """
    tabelas, detalhes = [], []
    for grupo in grupos:
        for features, colunas in FEATURES.items():
            for balanceamento in BALANCEAMENTOS:
                por_arquivo, previsoes = avaliar_por_arquivo(
                    dataset, modelos, colunas, balanceamento, grupo, n_estimators=n_estimators
                )
                rotulo = {"teste": f"{grupo} de fora", "features": features, "balanceamento": balanceamento}
                tabela = resumo_por_modelo(previsoes).merge(resumo_por_arquivo(por_arquivo), on="modelo")
                tabelas.append(tabela.assign(**rotulo))
                detalhes.append(por_arquivo.drop(columns="arquivos_no_treino").assign(**rotulo))
    return pd.concat(tabelas, ignore_index=True), pd.concat(detalhes, ignore_index=True)


def main() -> None:
    """Junta treino e teste do ``prepare``, compara as variações e grava em ``reports/``."""
    from src.paths import ProjectPaths

    paths = ProjectPaths(Path(__file__).resolve().parents[1])
    dataset = pd.concat([pd.read_csv(paths.train), pd.read_csv(paths.test)], ignore_index=True)
    tabela, detalhes = comparar_variacoes(dataset)
    tabela.to_csv(paths.reports_dir / "variacoes.csv", index=False)
    detalhes.to_csv(paths.reports_dir / "variacoes_por_arquivo.csv", index=False)
    colunas = ["teste", "features", "balanceamento", "modelo", "f1_macro", "recall_sob_efeito",
               "precision_sob_efeito", "media_por_arquivo", "pior_arquivo", "pior_acerto"]
    print(tabela[colunas].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
