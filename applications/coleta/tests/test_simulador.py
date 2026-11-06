import pytest

from coleta.arquivos import REPO
from coleta.simulador import instantes_de_sopro, validar_origem
from coleta.tests.ajuda import leitura


def test_sopro_marcado_na_primeira_leitura_depois_do_instante():
    leituras = [leitura(1, 19000), leitura(2, 20500), leitura(3, 21500), leitura(4, 80100)]
    assert instantes_de_sopro(leituras, [20.4, 80.0]) == {1: 20500, 3: 80100}


def test_sopro_depois_do_fim_e_ignorado():
    assert instantes_de_sopro([leitura(1, 1000)], [99.0]) == {}


def test_recusa_dados_processados():
    with pytest.raises(ValueError):
        validar_origem(REPO / "ml" / "data" / "processed" / "train.csv")
