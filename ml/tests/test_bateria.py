"""Bateria de treino: mesma quantidade de cada classe, arquivo inteiro de um lado."""

from __future__ import annotations

import pandas as pd
import pytest

from src.bateria import montar_bateria, tirar_arquivos_fora
from src.splitting import GroupSplit


def _dataset(arquivos: dict[str, tuple[str, int]], participante: str = "equipe") -> pd.DataFrame:
    linhas = []
    for nome, (classe, quantidade) in arquivos.items():
        for indice in range(quantidade):
            linhas.append(
                {
                    "attempt_id": f"{nome}-{indice:03d}",
                    "session_file": nome,
                    "participant_id": participante,
                    "target": classe,
                }
            )
    return pd.DataFrame(linhas)


def _coleta() -> pd.DataFrame:
    return _dataset(
        {
            "grande.csv": ("sem_efeito", 100),
            "a.csv": ("sem_efeito", 10),
            "b.csv": ("sem_efeito", 10),
            "c.csv": ("sem_efeito", 10),
            "s1.csv": ("sob_efeito", 30),
            "s2.csv": ("sob_efeito", 30),
            "s3.csv": ("sob_efeito", 30),
            "s4.csv": ("sob_efeito", 30),
        }
    )


def test_bateria_equilibra_os_lados_e_nao_parte_arquivo():
    split, treino, teste, _ = montar_bateria(
        _coleta(), existing=None, group_by="session_file", test_size=0.25, seed=42, n_por_classe=20
    )

    assert split.group_by == "session_file"
    assert treino["target"].value_counts().to_dict() == {"sem_efeito": 15, "sob_efeito": 15}
    assert teste["target"].value_counts().to_dict() == {"sem_efeito": 5, "sob_efeito": 5}
    assert not set(treino["session_file"]) & set(teste["session_file"])
    for lado in (treino, teste):
        sem_efeito = lado[lado["target"] == "sem_efeito"]
        assert sem_efeito["session_file"].nunique() >= 2
        assert int((sem_efeito["session_file"] == "grande.csv").sum()) < len(sem_efeito)


def test_bateria_repete_com_a_mesma_semente_e_o_manifesto_segura_os_grupos():
    dataset = _coleta().sample(frac=1, random_state=1)
    split, treino, teste, _ = montar_bateria(
        dataset, existing=None, group_by="session_file", test_size=0.25, seed=42, n_por_classe=20
    )
    de_novo, treino_de_novo, _, avisos = montar_bateria(
        dataset, existing=split, group_by="session_file", test_size=0.25, seed=99, n_por_classe=20
    )

    assert list(treino_de_novo["attempt_id"]) == list(treino["attempt_id"])
    assert set(de_novo.test_groups) == set(split.test_groups)
    assert set(de_novo.train_groups) == set(split.train_groups)
    assert any("manifesto existente" in aviso for aviso in avisos)
    assert set(teste["session_file"]) <= set(split.test_groups)


def test_bateria_deixa_os_arquivos_descartados_de_fora():
    dataset = pd.concat(
        [_coleta(), _dataset({"leituras_bebida1.csv": ("sem_efeito", 8), "leituras_conversa1.csv": ("sem_efeito", 4)})],
        ignore_index=True,
    )

    _, treino, teste, avisos = montar_bateria(
        dataset, existing=None, group_by="session_file", test_size=0.25, seed=1, n_por_classe=20
    )

    usados = set(treino["session_file"]) | set(teste["session_file"])
    assert "leituras_bebida1.csv" not in usados
    assert "leituras_conversa1.csv" not in usados
    assert any("leituras_bebida1.csv" in aviso for aviso in avisos)


def test_bateria_tira_do_manifesto_o_arquivo_que_ficou_de_fora():
    existente = GroupSplit(
        "session_file",
        ["grande.csv", "leituras_bebida1.csv"],
        ["a.csv"],
        test_size=0.25,
        seed=1,
        n_por_classe=20,
    )

    split, treino, teste, _ = montar_bateria(
        _coleta(), existing=existente, group_by="session_file", test_size=0.25, seed=1, n_por_classe=20
    )

    assert "leituras_bebida1.csv" not in set(split.train_groups) | set(split.test_groups)
    assert "leituras_bebida1.csv" not in set(treino["session_file"]) | set(teste["session_file"])
    assert "grande.csv" in split.train_groups
    assert "a.csv" in split.test_groups


def test_bateria_avisa_quando_so_ha_um_participante():
    split, _, _, avisos = montar_bateria(
        _coleta(), existing=None, group_by="participant_id", test_size=0.25, seed=1, n_por_classe=20
    )

    assert split.group_by == "session_file"
    assert any("arquivo de sessão" in aviso for aviso in avisos)


def test_bateria_sem_cota_equilibra_cada_lado_com_o_que_cabe():
    coleta = _coleta()
    split, treino, teste, _ = montar_bateria(
        coleta, existing=None, group_by="session_file", test_size=0.25, seed=42, n_por_classe=None
    )

    assert split.n_por_classe is None
    assert not set(treino["session_file"]) & set(teste["session_file"])
    for lado, grupos in ((treino, split.train_groups), (teste, split.test_groups)):
        bloco = coleta[coleta["session_file"].isin(grupos)]
        esperado = min(int((bloco["target"] == classe).sum()) for classe in ("sem_efeito", "sob_efeito"))
        assert int((lado["target"] == "sem_efeito").sum()) == esperado
        assert int((lado["target"] == "sob_efeito").sum()) == esperado
        assert esperado >= 1


def test_bateria_recusa_cota_maior_que_os_dados():
    with pytest.raises(ValueError, match="bateria"):
        montar_bateria(_coleta(), existing=None, group_by="session_file", n_por_classe=500)


def test_tira_extrato_antigo_e_copia_quando_o_original_esta_junto():
    dataset = _dataset(
        {
            "leituras_28_ambiente.csv": ("sem_efeito", 3),
            "2026-11-14_equipe_clean_5.csv": ("sem_efeito", 4),
            "2026-11-12_equipe_drink_1.csv": ("sob_efeito", 5),
            "leituras_11_alcool.csv": ("sob_efeito", 2),
        }
    )

    limpo, avisos = tirar_arquivos_fora(dataset)

    assert set(limpo["session_file"]) == {"leituras_28_ambiente.csv", "leituras_11_alcool.csv"}
    assert any("2026-11-12_equipe_drink_1.csv" in aviso for aviso in avisos)
    assert any("2026-11-14_equipe_clean_5.csv" in aviso for aviso in avisos)


def test_tirar_arquivos_fora_reconhece_a_lista_da_coleta():
    dataset = _dataset(
        {
            "leituras_11_alcool.csv": ("sob_efeito", 2),
            "leituras_bebida2.csv": ("sem_efeito", 2),
            "leituras_20_sensor_Instavel.csv": ("sem_efeito", 1),
            "leituras_novos_acima_08.csv": ("sem_efeito", 1),
            "leituras_ambiente.csv": ("sem_efeito", 2),
        }
    )

    limpo, avisos = tirar_arquivos_fora(dataset)

    assert set(limpo["session_file"]) == {"leituras_11_alcool.csv", "leituras_ambiente.csv"}
    assert any("leituras_bebida2.csv" in aviso for aviso in avisos)
    assert any("leituras_novos_acima_08.csv" in aviso for aviso in avisos)
