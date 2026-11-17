import csv
from datetime import date
from pathlib import Path

from coleta.arquivos import CsvSessao, anexar_attempts, linha_attempt, nome_sessao
from coleta.rodada import Rodada
from coleta.serial_proto import CABECALHO_CSV, ler_linha
from coleta.tests.ajuda import leitura

REPO = Path(__file__).resolve().parents[3]
CABECALHO_ATTEMPTS = (REPO / "ml" / "templates" / "attempts_template.csv").read_text().strip().split(",")
LINHA = "CSV_LINHA,leituras_3.csv,40,2940,1232,0.4,451,525,36.3,49.4,0"
DIA = date(2026, 11, 5)


def test_nome_sessao_pula_existentes(tmp_path):
    (tmp_path / "2026-11-05_p01_perfume_1.csv").touch()
    assert nome_sessao(tmp_path, DIA, "p01", "perfume").name == "2026-11-05_p01_perfume_2.csv"


def test_csv_sessao_formato_e_hash(tmp_path):
    sessao = CsvSessao(tmp_path / "s.csv")
    sessao.escrever(ler_linha(LINHA))
    sha = sessao.fechar()
    assert (tmp_path / "s.csv").read_text() == CABECALHO_CSV + "40,2940,1232,0.4,451,525,36.3,49.4,0\n"
    assert len(sha) == 64


def test_csv_vazio_e_apagado(tmp_path):
    sessao = CsvSessao(tmp_path / "s.csv")
    assert sessao.fechar() == ""
    assert not (tmp_path / "s.csv").exists()


def _rodada_com_dois_sopros() -> Rodada:
    rodada = Rodada("perfume", "p01", None)
    rodada.receber(leitura(1, 20400))
    rodada.marcar_inicio_sopro()
    rodada.receber(leitura(2, 25500))
    rodada.marcar_fim_sopro()
    rodada.receber(leitura(3, 80000))
    rodada.marcar_inicio_sopro()
    return rodada


def _linhas(rodada):
    sessao = Path("2026-11-05_p01_perfume_1.csv")
    return [linha_attempt(rodada, k, sessao) for k in range(1, len(rodada.sopros) + 1)]


def test_linha_attempt_usa_o_nome_do_arquivo():
    linhas = _linhas(_rodada_com_dois_sopros())
    assert [linha["attempt_id"] for linha in linhas] == [
        "2026-11-05_p01_perfume_1_s1",
        "2026-11-05_p01_perfume_1_s2",
    ]
    assert linhas[0]["session_file"] == "2026-11-05_p01_perfume_1.csv"
    assert linhas[0]["blow_start_s"] == "20.4"
    assert linhas[0]["blow_end_s"] == "25.5"
    assert linhas[1]["blow_end_s"] == ""
    assert linhas[0]["condition"] == "perfume"
    assert linhas[0]["participant_id"] == "p01"
    assert set(linhas[0]) == set(CABECALHO_ATTEMPTS)


def test_attempts_cria_com_cabecalho_e_acrescenta(tmp_path):
    destino = tmp_path / "attempts.csv"
    linhas = _linhas(_rodada_com_dois_sopros())
    anexar_attempts(destino, linhas[:1])
    anexar_attempts(destino, linhas[1:])
    with destino.open() as arquivo:
        leitor = csv.DictReader(arquivo)
        assert leitor.fieldnames == CABECALHO_ATTEMPTS
        assert [linha["blow_start_s"] for linha in leitor] == ["20.4", "80.0"]


def test_attempts_sem_sopros_nao_cria_arquivo(tmp_path):
    anexar_attempts(tmp_path / "attempts.csv", [])
    assert not (tmp_path / "attempts.csv").exists()


def test_csv_sessao_usa_o_cabecalho_do_formato_da_placa(tmp_path):
    sessao = CsvSessao(tmp_path / "s.csv")
    sessao.escrever(ler_linha("CSV_LINHA,s.csv,40,2940,1232,0.4,1.87,1.01,451,525,36.3,49.4,0,1745.00,1761.00"))
    sessao.fechar()
    linhas = (tmp_path / "s.csv").read_text().splitlines()
    assert linhas[0] == "amostra,t_ms,mq3_raw,ppm,rs,rs_rsar,mq135_raw,mq135_mv,temperature_c,humidity_pct,alcool,tensao_atual_mv,tensao_referencia_mv"
    assert linhas[1] == "40,2940,1232,0.4,1.87,1.01,451,525,36.3,49.4,0,1745.00,1761.00"
