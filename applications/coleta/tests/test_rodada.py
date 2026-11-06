from coleta.rodada import Rodada, Sopro
from coleta.serial_proto import ArquivoNovo
from coleta.tests.ajuda import leitura


def test_arquivo_novo_antes_da_primeira_leitura_e_ignorado():
    rodada = Rodada("perfume", "p01", None)
    assert rodada.receber(ArquivoNovo("leituras_2.csv")) == "ignorar"
    assert rodada.receber(leitura(1, 800)) == "leitura"
    assert rodada.leituras == 1


def test_reinicio_no_meio():
    rodada = Rodada("perfume", "p01", None)
    rodada.receber(leitura(10, 9000))
    assert rodada.receber(leitura(1, 800)) == "reiniciou"
    assert rodada.receber(ArquivoNovo("x.csv")) == "reiniciou"
    assert rodada.leituras == 1


def test_sopro_sem_leitura_e_ignorado():
    rodada = Rodada("perfume", "p01", None)
    assert rodada.marcar_inicio_sopro() is None
    assert rodada.sopros == []


def test_fim_sem_sopro_aberto_e_ignorado():
    rodada = Rodada("perfume", "p01", None)
    rodada.receber(leitura(1, 800))
    assert rodada.marcar_fim_sopro() is None


def test_sopro_usa_ultimo_t_ms():
    rodada = Rodada("perfume", "p01", None)
    rodada.receber(leitura(5, 20400))
    assert rodada.marcar_inicio_sopro() == Sopro(20400)
    rodada.receber(leitura(6, 25500))
    assert rodada.marcar_fim_sopro() == Sopro(20400, 25500)
    assert rodada.marcar_fim_sopro() is None


def test_duracao():
    rodada = Rodada("clean", "p01", 120)
    rodada.receber(leitura(1, 1000))
    rodada.receber(leitura(2, 120999))
    assert not rodada.terminou()
    rodada.receber(leitura(3, 121000))
    assert rodada.terminou()


def test_sem_duracao_nunca_termina_sozinha():
    rodada = Rodada("clean", "p01", None)
    rodada.receber(leitura(1, 1000))
    rodada.receber(leitura(2, 10_000_000))
    assert not rodada.terminou()


def test_ids_unicos():
    assert Rodada("clean", "p01", None).id != Rodada("clean", "p01", None).id
