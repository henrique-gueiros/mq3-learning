from pathlib import Path

import pytest

from coleta.importador import ler_csv_sessao
from coleta.lote import MANIFESTO, Entrada, copiar_sessoes, executar, ler_manifesto

REPO = Path(__file__).resolve().parents[3]


def _manifesto(pasta: Path, *linhas: str) -> Path:
    caminho = pasta / "lote.csv"
    caminho.write_text("origem,sessao,caso,participante\n" + "".join(l + "\n" for l in linhas))
    return caminho


def test_le_o_manifesto(tmp_path):
    caminho = _manifesto(tmp_path, "a.csv,2026-11-12_equipe_clean_1.csv,clean,equipe")
    assert ler_manifesto(caminho) == [Entrada("a.csv", "2026-11-12_equipe_clean_1.csv", "clean", "equipe")]


def test_caso_desconhecido_e_recusado(tmp_path):
    caminho = _manifesto(tmp_path, "a.csv,s.csv,cerveja,equipe")
    with pytest.raises(ValueError, match="caso desconhecido"):
        ler_manifesto(caminho)


def test_nome_de_sessao_repetido_e_recusado(tmp_path):
    caminho = _manifesto(tmp_path, "a.csv,s.csv,clean,equipe", "b.csv,s.csv,drink,equipe")
    with pytest.raises(ValueError, match="repetido"):
        ler_manifesto(caminho)


def test_copia_com_o_nome_da_sessao(tmp_path):
    origem, destino = tmp_path / "o", tmp_path / "d"
    origem.mkdir()
    (origem / "a.csv").write_text("conteudo")
    copiar_sessoes([Entrada("a.csv", "s.csv", "clean", "equipe")], origem, destino)
    assert (destino / "s.csv").read_text() == "conteudo"


def test_copia_repetida_do_mesmo_arquivo_e_aceita(tmp_path):
    origem, destino = tmp_path / "o", tmp_path / "d"
    origem.mkdir()
    (origem / "a.csv").write_text("conteudo")
    entrada = Entrada("a.csv", "s.csv", "clean", "equipe")
    copiar_sessoes([entrada], origem, destino)
    copiar_sessoes([entrada], origem, destino)
    assert (destino / "s.csv").read_text() == "conteudo"


def test_nao_sobrescreve_um_arquivo_diferente(tmp_path):
    origem, destino = tmp_path / "o", tmp_path / "d"
    origem.mkdir()
    destino.mkdir()
    (origem / "a.csv").write_text("novo")
    (destino / "s.csv").write_text("antigo")
    with pytest.raises(ValueError, match="já existe"):
        copiar_sessoes([Entrada("a.csv", "s.csv", "clean", "equipe")], origem, destino)
    assert (destino / "s.csv").read_text() == "antigo"


def test_origem_inexistente_e_recusada(tmp_path):
    with pytest.raises(ValueError, match="não encontrado"):
        copiar_sessoes([Entrada("falta.csv", "s.csv", "clean", "equipe")], tmp_path, tmp_path / "d")


def test_executar_importa_cada_sessao_e_conta_as_repetidas(tmp_path):
    origem, destino = tmp_path / "o", tmp_path / "d"
    origem.mkdir()
    (origem / "a.csv").write_text("a")
    (origem / "b.csv").write_text("b")
    entradas = [
        Entrada("a.csv", "sa.csv", "clean", "equipe"),
        Entrada("b.csv", "sb.csv", "drink", "equipe"),
    ]
    chamadas = []

    def importar(caminho, caso, participante):
        chamadas.append((caminho.name, caso, participante))
        if caminho.name == "sb.csv":
            raise ValueError("sb.csv já importado como rodada x")

    resumo = executar(entradas, origem, destino, importar)

    assert chamadas == [("sa.csv", "clean", "equipe"), ("sb.csv", "drink", "equipe")]
    assert resumo.importadas == ["sa.csv"]
    assert resumo.ja_importadas == ["sb.csv"]


def test_executar_nao_esconde_outros_erros(tmp_path):
    origem = tmp_path / "o"
    origem.mkdir()
    (origem / "a.csv").write_text("a")

    def importar(caminho, caso, participante):
        raise ValueError("a.csv: cabeçalho diferente do firmware")

    with pytest.raises(ValueError, match="cabeçalho"):
        executar([Entrada("a.csv", "s.csv", "clean", "equipe")], origem, tmp_path / "d", importar)


def test_manifesto_do_repositorio_aponta_para_csvs_validos():
    entradas = ler_manifesto(MANIFESTO)
    assert len(entradas) == 12
    for entrada in entradas:
        assert ler_csv_sessao(REPO / "esp32-esp8266" / entrada.origem), entrada.origem
