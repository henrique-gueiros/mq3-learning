from pathlib import Path

import pytest

from coleta.importador import importar, ler_csv_sessao, sopros_do_attempts
from coleta.serial_proto import CABECALHO_CSV

REPO = Path(__file__).resolve().parents[3]
CABECALHO_ATTEMPTS = "attempt_id,session_file,participant_id,condition,blow_start_s,blow_end_s,reference_mg_l,notes\n"


def _sessao(pasta: Path, nome: str = "s.csv") -> Path:
    caminho = pasta / nome
    caminho.write_text(CABECALHO_CSV + "1,1000,1200,0.4,450,520,,,0\n2,21000,1600,0.4,600,530,30.0,60.0,0\n")
    return caminho


def _attempts(pasta: Path, *linhas: str) -> Path:
    caminho = pasta / "attempts.csv"
    caminho.write_text(CABECALHO_ATTEMPTS + "".join(linha + "\n" for linha in linhas))
    return caminho


def test_le_amostra_real():
    leituras = ler_csv_sessao(REPO / "esp32-esp8266" / "leituras.csv")
    assert leituras and leituras[0].amostra == 38


def test_linha_invalida_diz_onde(tmp_path):
    caminho = tmp_path / "s.csv"
    caminho.write_text(CABECALHO_CSV + "1,1000,1200,0.4,450,520,,,0\n2,abc\n")
    with pytest.raises(ValueError, match="linha 3"):
        ler_csv_sessao(caminho)


def test_cabecalho_errado(tmp_path):
    caminho = tmp_path / "s.csv"
    caminho.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="cabeçalho"):
        ler_csv_sessao(caminho)


def test_sopros_do_attempts(tmp_path):
    attempts = _attempts(
        tmp_path,
        "a1,s.csv,p01,perfume,20.4,25.5,,",
        "a2,s.csv,p01,perfume,80,,,",
        "a3,outro.csv,p01,clean,10,,,",
    )
    assert sopros_do_attempts(attempts, "s.csv") == ({"perfume"}, [(20400, 25500), (80000, None)])
    assert sopros_do_attempts(tmp_path / "nao_existe.csv", "s.csv") == (set(), [])


@pytest.mark.integracao
def test_importa_sopros_como_eventos(pg, tmp_path):
    attempts = _attempts(tmp_path, "a1,s.csv,p01,perfume,20,,,")
    importar(pg, _sessao(tmp_path), "perfume", "p01", "placa01", attempts)
    assert pg.execute("select inicio_ms, origem from v_sopros").fetchall() == [(20000, "importador")]
    assert pg.execute("select count(*) from leituras").fetchone() == (2,)


@pytest.mark.integracao
def test_importar_duas_vezes_recusa(pg, tmp_path):
    sessao = _sessao(tmp_path)
    attempts = tmp_path / "vazio.csv"
    importar(pg, sessao, "perfume", "p01", "placa01", attempts)
    with pytest.raises(ValueError, match="já importado"):
        importar(pg, sessao, "perfume", "p01", "placa01", attempts)


@pytest.mark.integracao
def test_condicoes_misturadas_recusa(pg, tmp_path):
    attempts = _attempts(tmp_path, "a1,s.csv,p01,perfume,20,,,", "a2,s.csv,p01,clean,80,,,")
    with pytest.raises(ValueError, match="clean"):
        importar(pg, _sessao(tmp_path), "perfume", "p01", "placa01", attempts)
    assert pg.execute("select count(*) from rodadas").fetchone() == (0,)


@pytest.mark.integracao
def test_caso_divergente_do_attempts_recusa(pg, tmp_path):
    attempts = _attempts(tmp_path, "a1,s.csv,p01,clean,20,,,")
    with pytest.raises(ValueError):
        importar(pg, _sessao(tmp_path), "perfume", "p01", "placa01", attempts)


def test_caso_desconhecido_recusa(tmp_path):
    with pytest.raises(ValueError, match="caso desconhecido"):
        importar(None, _sessao(tmp_path), "vodka", "p01", "placa01", tmp_path / "a.csv")


def test_le_csv_no_formato_com_rs(tmp_path):
    caminho = tmp_path / "s.csv"
    caminho.write_text(
        "amostra,t_ms,mq3_raw,ppm,rs,rs_rsar,mq135_raw,mq135_mv,temperature_c,humidity_pct,alcool,tensao_atual_mv,tensao_referencia_mv\n"
        "1,1002,922,0.4,4.61,1.01,202,294,,,0,892.00,901.70\n"
    )
    leituras = ler_csv_sessao(caminho)
    assert [(l.amostra, l.mq3_raw, l.mq135_raw, l.temperature_c) for l in leituras] == [(1, 922, 202, None)]


def test_le_csv_no_formato_de_11_colunas(tmp_path):
    caminho = tmp_path / "s.csv"
    caminho.write_text(
        "amostra,t_ms,mq3_raw,ppm,rs,rs_rsar,mq135_raw,mq135_mv,temperature_c,humidity_pct,alcool\n"
        "1,1002,922,0.4,4.61,1.01,202,294,29.1,48.1,0\n"
    )
    leituras = ler_csv_sessao(caminho)
    assert [(l.mq3_raw, l.humidity_pct) for l in leituras] == [(922, 48.1)]
