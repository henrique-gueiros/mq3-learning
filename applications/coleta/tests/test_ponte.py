import argparse
import csv

import pytest

from coleta.ponte import Coleta
from coleta.publicador import Publicador
from coleta.serial_proto import ArquivoNovo
from coleta.tests.ajuda import leitura


@pytest.fixture
def coleta(tmp_path):
    args = argparse.Namespace(
        caso="perfume", participante="p01", duracao=None,
        sessoes=tmp_path / "sessions", attempts=tmp_path / "attempts.csv",
    )
    publicador = Publicador("127.0.0.1", 1, "placa01")
    coleta = Coleta(args, publicador)
    coleta.abrir_rodada()
    return coleta


def test_broker_fora_do_ar_mantem_csv_e_attempts(capsys, coleta, tmp_path):
    coleta.receber(leitura(1, 20000))
    coleta.comando("")
    coleta.receber(leitura(2, 21000))
    coleta.encerrar_rodada()

    [sessao] = (tmp_path / "sessions").iterdir()
    assert len(sessao.read_text().splitlines()) == 3
    with (tmp_path / "attempts.csv").open() as arquivo:
        [linha] = list(csv.DictReader(arquivo))
    assert linha["session_file"] == sessao.name
    assert linha["blow_start_s"] == "20.0"
    saida = capsys.readouterr().out
    assert saida.count("Broker fora do ar") == 1


def test_reinicio_abre_rodada_nova(coleta, tmp_path):
    primeira = coleta.rodada.id
    coleta.receber(leitura(5, 9000))
    coleta.receber(ArquivoNovo("leituras_2.csv"))
    coleta.receber(leitura(1, 800))
    coleta.encerrar_rodada()

    assert coleta.rodada.id != primeira
    nomes = sorted(p.name for p in (tmp_path / "sessions").iterdir())
    assert len(nomes) == 2
    assert nomes[1].endswith("_2.csv")


def test_sopro_antes_de_leitura_avisa(coleta, capsys):
    coleta.comando("")
    assert coleta.rodada.sopros == []
    assert "nenhuma leitura" in capsys.readouterr().out
