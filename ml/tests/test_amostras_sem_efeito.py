"""Arquivos sem álcool: umidade alta vira sopro de 3 amostras; o resto, uma por linha."""

from __future__ import annotations

import pandas as pd

from src.amostras_sem_efeito import UMIDADE_MINIMA_SOPRO, tentativas_sem_efeito


def _amostras(valores: list[tuple[int, float | None]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "t_ms": [t for t, _ in valores],
            "humidity_pct": [umidade for _, umidade in valores],
        }
    )


def test_limiar_separa_sopro_de_amostra_avulsa():
    amostras = _amostras(
        [
            (1000, 50),
            (2000, 61),
            (3000, 62),
            (4000, 63),
            (5000, 64),
            (6000, 40),
        ]
    )

    linhas = tentativas_sem_efeito(amostras, "leituras_ambiente.csv", "equipe", "clean")

    assert list(linhas["condition"]) == ["sem_efeito", "sem_efeito", "sem_efeito", "sem_efeito"]
    assert list(linhas["blow_start_s"]) == [1.0, 2.0, 5.0, 6.0]
    assert list(linhas["blow_end_s"]) == [1.001, 4.0, 5.001, 6.001]
    assert "3 amostras" in linhas["notes"].iloc[1]
    assert "uma amostra" in linhas["notes"].iloc[0]
    assert linhas["attempt_id"].tolist() == [
        "leituras_ambiente_s1",
        "leituras_ambiente_s2",
        "leituras_ambiente_s3",
        "leituras_ambiente_s4",
    ]


def test_umidade_no_limiar_entra_no_sopro():
    amostras = _amostras([(1000, UMIDADE_MINIMA_SOPRO), (2000, UMIDADE_MINIMA_SOPRO), (3000, UMIDADE_MINIMA_SOPRO)])

    linhas = tentativas_sem_efeito(amostras, "leituras_listerine.csv", "equipe", "mouthwash")

    assert len(linhas) == 1
    assert linhas["condition"].iloc[0] == "sem_efeito"
    assert linhas["blow_end_s"].iloc[0] == 3.0


def test_umidade_vazia_fica_uma_amostra():
    amostras = _amostras([(1000, None), (2000, 70), (3000, 71)])

    linhas = tentativas_sem_efeito(amostras, "ar.csv", "equipe", "perfume")

    assert len(linhas) == 3
    assert linhas["condition"].tolist() == ["sem_efeito", "sem_efeito", "sem_efeito"]


def test_sem_arquivo_de_alcool_nao_reescreve_attempts(tmp_path):
    from src.amostras_sem_efeito import reorganizar_amostras_sem_efeito
    from src.paths import ProjectPaths

    paths = ProjectPaths(tmp_path)
    paths.raw_sessions_dir.mkdir(parents=True)
    original = (
        "attempt_id,session_file,participant_id,condition,blow_start_s,blow_end_s,reference_mg_l,notes\n"
        "p1_clean_0_s1,p1_clean_0.csv,p1,clean,20,25,,sintetico\n"
    )
    paths.raw_attempts.write_text(original, encoding="utf-8")

    assert reorganizar_amostras_sem_efeito(paths) == []
    assert paths.raw_attempts.read_text(encoding="utf-8") == original


def test_reorganizar_troca_o_arquivo_sem_alcool_e_preserva_o_de_bebida(tmp_path):
    from src.amostras_sem_efeito import reorganizar_amostras_sem_efeito
    from src.paths import ProjectPaths

    paths = ProjectPaths(tmp_path)
    paths.raw_sessions_dir.mkdir(parents=True)
    (paths.raw_sessions_dir / "leituras_11_alcool.csv").write_text("t_ms,ppm\n1000,1\n", encoding="utf-8")
    pd.DataFrame(
        {"t_ms": [1000, 2000, 3000], "humidity_pct": [40, 41, 42], "mq3_raw": [1, 1, 1]}
    ).to_csv(paths.raw_sessions_dir / "leituras_ambiente.csv", index=False)
    paths.raw_attempts.write_text(
        "attempt_id,session_file,participant_id,condition,blow_start_s,blow_end_s,reference_mg_l,notes\n"
        "alcool_s1,leituras_11_alcool.csv,equipe,drink,1,4,,fica\n"
        "antigo,leituras_ambiente.csv,equipe,clean,1,4,,um sopro so\n",
        encoding="utf-8",
    )

    reorganizar_amostras_sem_efeito(paths)
    texto = paths.raw_attempts.read_text(encoding="utf-8")

    assert "leituras_11_alcool.csv" in texto
    assert "antigo" not in texto
    assert texto.count("leituras_ambiente_s") == 3
