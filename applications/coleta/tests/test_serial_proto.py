from pathlib import Path

from coleta.serial_proto import ArquivoNovo, Leitura, ler_linha

REPO = Path(__file__).resolve().parents[3]
LINHA = "CSV_LINHA,leituras_3.csv,40,2940,1232,0.4,451,525,36.3,49.4,0"


def test_leitura_completa():
    assert ler_linha(LINHA) == Leitura(40, 2940, 1232, 0.4, 451, 525, 36.3, 49.4, 0)


def test_dht_vazio_vira_none():
    leitura = ler_linha("CSV_LINHA,leituras_3.csv,38,811,1222,0.4,462,514,,,0")
    assert leitura.temperature_c is None
    assert leitura.humidity_pct is None


def test_arquivo_novo():
    assert ler_linha("CSV_ARQUIVO,leituras_4.csv\r\n") == ArquivoNovo("leituras_4.csv")


def test_linhas_ignoradas():
    lixo = [
        "Leitura: 1232  ppm: 0.4",
        "",
        "CSV_LINHA,leituras_3.csv,40,29",
        b"\xff\xfe\x00",
        "CSV_LINHA,x.csv,a,b,c,d,e,f,g,h,i",
        "CSV_ARQUIVO,",
    ]
    for linha in lixo:
        assert ler_linha(linha) is None, linha


def test_bytes_aceitos():
    assert ler_linha(LINHA.encode()) == ler_linha(LINHA)


def test_ida_e_volta_csv():
    leitura = ler_linha("CSV_LINHA,leituras_3.csv,38,811,1222,0.4,462,514,,,0")
    assert leitura.como_linha_csv() == "38,811,1222,0.4,462,514,,,0"


def test_amostra_real_ida_e_volta():
    linhas = (REPO / "firmware" / "leituras.csv").read_text().splitlines()[1:]
    assert linhas
    for linha in linhas:
        leitura = ler_linha(f"CSV_LINHA,leituras_1.csv,{linha}")
        assert leitura is not None, linha
        assert leitura.como_linha_csv() == linha
