import pytest

from coleta.arquivos import REPO
from coleta.simulador import eventos_de_sopro, instantes_de_sopro, validar_origem
from coleta.tests.ajuda import leitura


def test_sopro_marcado_na_primeira_leitura_depois_do_instante():
    leituras = [leitura(1, 19000), leitura(2, 20500), leitura(3, 21500), leitura(4, 80100)]
    assert instantes_de_sopro(leituras, [20.4, 80.0]) == {1: 20500, 3: 80100}


def test_sopro_depois_do_fim_e_ignorado():
    assert instantes_de_sopro([leitura(1, 1000)], [99.0]) == {}


def test_recusa_dados_processados():
    with pytest.raises(ValueError):
        validar_origem(REPO / "ml" / "data" / "processed" / "train.csv")


def test_cada_sopro_ganha_inicio_e_fim():
    leituras = [leitura(i, i * 1000) for i in range(1, 100)]
    eventos = eventos_de_sopro(leituras, [20.0, 80.0], duracao_s=5.0)
    assert eventos == {
        19: [("sopro_inicio", 20000)],
        24: [("sopro_fim", 25000)],
        79: [("sopro_inicio", 80000)],
        84: [("sopro_fim", 85000)],
    }


def test_sopro_no_fim_da_sessao_fica_sem_fim():
    leituras = [leitura(1, 1000), leitura(2, 2000)]
    assert eventos_de_sopro(leituras, [2.0], duracao_s=5.0) == {1: [("sopro_inicio", 2000)]}
