"""Sopros de bebida: 3 amostras, e o grupo sai se algum PPM fica abaixo de 0,6."""

from __future__ import annotations

import pandas as pd

from src.sopros_bebida import e_arquivo_bebida, sopros_de_bebida


def _amostras(valores: list[tuple[int, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "t_ms": [t for t, _ in valores],
            "ppm": [ppm for _, ppm in valores],
        }
    )


def test_arquivo_de_bebida_e_o_que_tem_alcool_no_nome():
    assert e_arquivo_bebida("leituras_11_alcool2.csv")
    assert e_arquivo_bebida("leituras_14_Alcool3.csv")
    assert not e_arquivo_bebida("leituras_bebida1.csv")
    assert not e_arquivo_bebida("2026-11-14_equipe_clean_1.csv")


def test_cada_tres_amostras_viram_um_sopro_se_o_ppm_nao_cai():
    amostras = _amostras(
        [
            (1000, 0.7),
            (2000, 0.8),
            (3000, 0.6),
            (4000, 0.5),
            (5000, 0.9),
            (6000, 0.9),
            (7000, 1.1),
        ]
    )

    sopros = sopros_de_bebida(amostras, "leituras_11_alcool.csv", "equipe")

    assert list(sopros["attempt_id"]) == ["leituras_11_alcool_s1"]
    assert list(sopros["condition"]) == ["sob_efeito"]
    assert list(sopros["blow_start_s"]) == [1.0]
    assert list(sopros["blow_end_s"]) == [3.0]
    assert "ppm" in sopros["notes"].iloc[0]


def test_amostras_que_sobram_fora_do_trio_nao_viram_sopro():
    amostras = _amostras([(1000, 0.9), (2000, 0.9)])

    sopros = sopros_de_bebida(amostras, "leituras_17_Alcool.csv", "equipe")

    assert sopros.empty


def test_lote_reconhece_a_copia_renomeada_do_arquivo_de_alcool(tmp_path):
    from src.sopros_bebida import arquivos_bebida

    sessoes = tmp_path / "sessions"
    sessoes.mkdir()
    (sessoes / "2026-11-12_equipe_drink_1.csv").write_text("t_ms,ppm\n", encoding="utf-8")
    (sessoes / "leituras_bebida1.csv").write_text("t_ms,ppm\n", encoding="utf-8")
    lote = tmp_path / "lote.csv"
    lote.write_text(
        "origem,sessao,caso,participante\n"
        "leituras_11_alcool.csv,2026-11-12_equipe_drink_1.csv,drink,equipe\n"
        "leituras_bebida1.csv,leituras_bebida1.csv,drink,equipe\n",
        encoding="utf-8",
    )

    nomes = [path.name for path in arquivos_bebida(sessoes, lote)]

    assert nomes == ["2026-11-12_equipe_drink_1.csv"]


def test_reorganizar_troca_os_sopros_de_alcool_e_deixa_o_resto(tmp_path):
    from src.paths import ProjectPaths
    from src.sopros_bebida import reorganizar_sopros_de_bebida

    paths = ProjectPaths(tmp_path)
    paths.raw_sessions_dir.mkdir(parents=True)
    _gravar_sessao(
        paths.raw_sessions_dir / "leituras_11_alcool.csv",
        [(1000, 0.7), (2000, 0.8), (3000, 0.9), (4000, 0.4), (5000, 0.9), (6000, 0.9)],
    )
    paths.raw_attempts.write_text(
        "attempt_id,session_file,participant_id,condition,blow_start_s,blow_end_s,reference_mg_l,notes\n"
        "antigo,leituras_11_alcool.csv,p01,drink,1,4,,um sopro so\n"
        "bebida,leituras_bebida1.csv,equipe,drink,1,4,,nome sem alcool\n"
        "perfume,leituras_perfume.csv,equipe,perfume,2,5,,fica\n",
        encoding="utf-8",
    )

    avisos = reorganizar_sopros_de_bebida(paths)
    texto = paths.raw_attempts.read_text(encoding="utf-8")

    assert "leituras_11_alcool_s1" in texto
    assert "antigo" not in texto
    assert "leituras_bebida1.csv" not in texto
    assert "leituras_perfume.csv" in texto
    assert any("ppm" in aviso for aviso in avisos)


def test_sem_arquivo_de_alcool_o_attempts_nao_muda(tmp_path):
    from src.paths import ProjectPaths
    from src.sopros_bebida import reorganizar_sopros_de_bebida

    paths = ProjectPaths(tmp_path)
    paths.raw_sessions_dir.mkdir(parents=True)
    original = (
        "attempt_id,session_file,participant_id,condition,blow_start_s,blow_end_s,reference_mg_l,notes\n"
        "p1_drink_0_s1,p1_drink_0.csv,p1,drink,20,25,,sintetico\n"
    )
    paths.raw_attempts.write_text(original, encoding="utf-8")

    assert reorganizar_sopros_de_bebida(paths) == []
    assert paths.raw_attempts.read_text(encoding="utf-8") == original


def _gravar_sessao(path, valores: list[tuple[int, float]]) -> None:
    linhas = ["t_ms,ppm"]
    linhas.extend(f"{t},{ppm}" for t, ppm in valores)
    path.write_text("\n".join(linhas) + "\n", encoding="utf-8")
