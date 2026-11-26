"""Validação deixando um arquivo de fora (as curvas são de teste, não desempenho real)."""

from __future__ import annotations

from src.por_arquivo import avaliar_por_arquivo
from tests.conftest import make_feature_dataset


def _dataset():
    dataset = make_feature_dataset(n_participants=6, repetitions=2)
    # um arquivo por participante, para o teste
    dataset["session_file"] = dataset["participant_id"] + ".csv"
    return dataset


def test_cada_arquivo_e_testado_uma_vez_sem_ser_visto():
    dataset = _dataset()
    por_arquivo, previsoes = avaliar_por_arquivo(dataset, ["logistic_regression"], n_estimators=5)

    assert sorted(por_arquivo["arquivo_de_fora"].unique()) == sorted(dataset["session_file"].unique())
    assert len(previsoes) == len(dataset)  # cada tentativa prevista exatamente uma vez
    for linha in por_arquivo.to_dict(orient="records"):
        assert linha["arquivo_de_fora"] not in linha["arquivos_no_treino"]


def test_resumo_por_arquivo_tem_acerto_e_hiperparametros():
    por_arquivo, _ = avaliar_por_arquivo(_dataset(), ["logistic_regression"], n_estimators=5)
    assert {"modelo", "classe_real", "n", "acertos", "acerto", "parametros"} <= set(por_arquivo.columns)
    assert ((por_arquivo["acerto"] >= 0) & (por_arquivo["acerto"] <= 1)).all()
