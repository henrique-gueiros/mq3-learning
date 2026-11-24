from pathlib import Path

from coleta.serial_proto import CABECALHO_COM_RS, CABECALHO_CSV, ArquivoNovo, Leitura, ler_linha

REPO = Path(__file__).resolve().parents[3]
LINHA = "CSV_LINHA,leituras_3.csv,40,2940,1232,0.4,451,525,36.3,49.4,0"
LINHA_COM_RS = "CSV_LINHA,leituras_3.csv,40,2940,1232,0.4,1.87,1.01,451,525,36.3,49.4,0,1745.00,1761.00"


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
    linhas = (REPO / "esp32-esp8266" / "leituras.csv").read_text().splitlines()[1:]
    assert linhas
    for linha in linhas:
        leitura = ler_linha(f"CSV_LINHA,leituras_1.csv,{linha}")
        assert leitura is not None, linha
        assert leitura.como_linha_csv() == linha


def test_leitura_no_formato_com_rs():
    assert ler_linha(LINHA_COM_RS) == Leitura(40, 2940, 1232, 0.4, 451, 525, 36.3, 49.4, 0)


def test_formato_com_rs_ida_e_volta():
    leitura = ler_linha(LINHA_COM_RS)
    assert leitura.como_linha_csv() == "40,2940,1232,0.4,1.87,1.01,451,525,36.3,49.4,0,1745.00,1761.00"


def test_cabecalho_acompanha_o_formato():
    assert ler_linha(LINHA).cabecalho_csv == CABECALHO_CSV
    assert ler_linha(LINHA_COM_RS).cabecalho_csv == CABECALHO_COM_RS


def test_numero_de_campos_estranho_e_ignorado():
    assert ler_linha("CSV_LINHA,leituras_3.csv,40,2940,1232,0.4,1.87,1.01,451,525") is None


def test_campo_extra_ilegivel_invalida_a_linha():
    assert ler_linha(LINHA_COM_RS.replace("1745.00", "17x5")) is None


def test_evento_do_botao_da_placa():
    from coleta.serial_proto import EventoPlaca

    assert ler_linha("CSV_EVENTO,leituras_3.csv,sopro_inicio,41230\r\n") == EventoPlaca(
        "leituras_3.csv", "sopro_inicio", 41230
    )
    assert ler_linha("CSV_EVENTO,leituras_3.csv,sopro_fim,46000") == EventoPlaca("leituras_3.csv", "sopro_fim", 46000)
    for lixo in ["CSV_EVENTO,a.csv,outro,1", "CSV_EVENTO,a.csv,sopro_fim,x", "CSV_EVENTO,a.csv,sopro_fim"]:
        assert ler_linha(lixo) is None, lixo
