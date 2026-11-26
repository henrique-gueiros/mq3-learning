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


def test_features_de_variacao_tiram_os_niveis_absolutos():
    from src.por_arquivo import FEATURES

    variacao = FEATURES["variacao"]
    assert not any(c.endswith("_before") or c.endswith("_peak") for c in variacao)
    assert {"mq3_rise", "humidity_rise", "mq135_mq3_rise_ratio", "mq3_humidity_peak_lag_s"} <= set(variacao)
    assert set(variacao) < set(FEATURES["todas"])


def test_corte_por_arquivo_limita_so_o_sem_efeito_e_espalha_no_tempo():
    import pandas as pd

    from src.por_arquivo import cortar_por_arquivo

    linhas = [{"attempt_id": f"a_s{i}", "session_file": "a.csv", "target": "sem_efeito"} for i in range(1, 101)]
    linhas += [{"attempt_id": f"b_s{i}", "session_file": "b.csv", "target": "sob_efeito"} for i in range(1, 51)]
    cortado = cortar_por_arquivo(pd.DataFrame(linhas), maximo=10)

    a = cortado[cortado["session_file"] == "a.csv"]["attempt_id"].tolist()
    assert len(a) == 10
    assert a[0] == "a_s1" and a[-1] == "a_s100"  # pega o arquivo inteiro, não o começo
    assert (cortado["session_file"] == "b.csv").sum() == 50  # bebida intacta


def test_avalia_deixando_um_dia_de_fora():
    dataset = _dataset()
    dataset["session_file"] = ["2026-11-12_x.csv" if i % 2 else "2026-11-14_y.csv" for i in range(len(dataset))]
    por_grupo, previsoes = avaliar_por_arquivo(dataset, ["logistic_regression"], n_estimators=5, grupo="dia")
    assert sorted(por_grupo["arquivo_de_fora"].unique()) == ["2026-11-12", "2026-11-14"]
    assert len(previsoes) == len(dataset)


def test_resumo_por_arquivo_pega_o_pior():
    import pandas as pd

    from src.por_arquivo import resumo_por_arquivo

    por_arquivo = pd.DataFrame(
        {"modelo": ["m"] * 3, "arquivo_de_fora": ["a", "b", "c"], "classe_real": ["sem_efeito"] * 2 + ["sob_efeito"],
         "n": [10, 10, 10], "acertos": [10, 2, 9], "acerto": [1.0, 0.2, 0.9]}
    )
    resumo = resumo_por_arquivo(por_arquivo).iloc[0]
    assert resumo["pior_arquivo"] == "b"
    assert round(resumo["pior_acerto"], 2) == 0.2
    assert round(resumo["media_por_arquivo"], 2) == 0.7
