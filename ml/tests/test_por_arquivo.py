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
    por_arquivo, previsoes = avaliar_por_arquivo(dataset, ["knn"], n_estimators=5)

    assert sorted(por_arquivo["arquivo_de_fora"].unique()) == sorted(dataset["session_file"].unique())
    assert len(previsoes) == len(dataset)  # cada tentativa prevista exatamente uma vez
    for linha in por_arquivo.to_dict(orient="records"):
        assert linha["arquivo_de_fora"] not in linha["arquivos_no_treino"]


def test_resumo_por_arquivo_tem_acerto_e_hiperparametros():
    por_arquivo, _ = avaliar_por_arquivo(_dataset(), ["knn"], n_estimators=5)
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
    por_grupo, previsoes = avaliar_por_arquivo(dataset, ["knn"], n_estimators=5, grupo="dia")
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


def test_limiar_escolhido_no_treino_maximiza_recall_mantendo_o_sem_efeito():
    import numpy as np
    import pandas as pd

    from src.por_arquivo import escolher_limiar

    y = pd.Series(["sem_efeito"] * 6 + ["sob_efeito"] * 4)
    prob = np.array([0.05, 0.1, 0.2, 0.3, 0.35, 0.6, 0.4, 0.45, 0.7, 0.9])
    # 0,4 pega as 4 bebidas e só erra 1 de 6 sem efeito (acerto 0,83); com mínimo 0,8 vale
    assert escolher_limiar(y, prob, minimo_sem_efeito=0.8) == 0.4
    # exigindo 1,0 no sem efeito, o limiar sobe acima de 0,6
    assert escolher_limiar(y, prob, minimo_sem_efeito=1.0) > 0.6


def test_variantes_de_treino_rodam():
    from src.por_arquivo import BALANCEAMENTOS

    assert set(BALANCEAMENTOS) == {"grid", "sem_peso", "corte", "limiar", "sem_peso_limiar"}
    for balanceamento in BALANCEAMENTOS:
        por_arquivo, _ = avaliar_por_arquivo(_dataset(), ["decision_tree"], n_estimators=5, balanceamento=balanceamento)
        assert not por_arquivo.empty


def test_limiar_aguenta_fold_interno_sem_bebida():
    """Com peso fixo da bebida, um fold interno só com sem_efeito não pode derrubar o limiar."""
    import pandas as pd

    from src.por_arquivo import _limiar_no_treino
    from src.features import feature_columns
    from src.train import model_specs

    dataset = _dataset()
    # bebida só em dois arquivos: com 3 folds, algum fica sem bebida no treino interno
    sob = dataset["target"] == "sob_efeito"
    arquivos = sorted(dataset["session_file"].unique())
    dataset.loc[sob & ~dataset["session_file"].isin(arquivos[:2]), "target"] = "sem_efeito"
    modelo = model_specs(n_estimators=5)["decision_tree"].pipeline.set_params(
        clf__class_weight={"sem_efeito": 1, "sob_efeito": 2}
    )
    colunas = feature_columns("mq3+mq135+dht11")
    modelo.fit(dataset[colunas], dataset["target"])
    limiar = _limiar_no_treino(modelo, dataset, colunas, n_inner=3)
    assert 0.0 <= limiar <= 1.0
