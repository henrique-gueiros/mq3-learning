"""Copia e importa um lote de CSVs de sessão listados num manifesto.

Uso (de dentro de ``applications/``)::

    python -m coleta.lote                          # lote de 2026-11
    python -m coleta.lote --manifesto dados/outro.csv

O manifesto (``origem,sessao,caso,participante``) diz qual CSV de
``esp32-esp8266/leituras/`` vira qual sessão em ``applications/ml/data/raw/sessions/`` e com que caso
e participante ele entra no banco. Rodar de novo é seguro: arquivo já copiado
com o mesmo conteúdo é aceito e sessão já importada é só contada.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from coleta.casos import validar_caso

RAIZ = Path(__file__).resolve().parents[2]
MANIFESTO = RAIZ / "applications" / "dados" / "lote-2026-11.csv"
PASTA_FIRMWARE = RAIZ / "esp32-esp8266" / "leituras"
PASTA_SESSOES = RAIZ / "applications" / "ml" / "data" / "raw" / "sessions"


@dataclass(frozen=True)
class Entrada:
    origem: str
    sessao: str
    caso: str
    participante: str


@dataclass
class Resumo:
    importadas: List[str] = field(default_factory=list)
    ja_importadas: List[str] = field(default_factory=list)


def ler_manifesto(caminho: Path) -> List[Entrada]:
    entradas: List[Entrada] = []
    nomes = set()
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            entrada = Entrada(linha["origem"], linha["sessao"], validar_caso(linha["caso"]), linha["participante"])
            if entrada.sessao in nomes:
                raise ValueError(f"nome de sessão repetido no manifesto: {entrada.sessao}")
            nomes.add(entrada.sessao)
            entradas.append(entrada)
    return entradas


def copiar_sessoes(entradas: List[Entrada], pasta_origem: Path, pasta_destino: Path) -> None:
    """Copia cada CSV com o nome da sessão, sem nunca sobrescrever um arquivo diferente."""
    for entrada in entradas:
        origem = pasta_origem / entrada.origem
        if not origem.exists():
            raise ValueError(f"CSV de origem não encontrado: {origem}")
        destino = pasta_destino / entrada.sessao
        if destino.exists():
            if destino.read_bytes() != origem.read_bytes():
                raise ValueError(f"{destino.name} já existe com conteúdo diferente de {entrada.origem}")
            continue
        pasta_destino.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origem, destino)


def executar(
    entradas: List[Entrada],
    pasta_origem: Path,
    pasta_destino: Path,
    importar: Callable[[Path, str, str], object],
) -> Resumo:
    """Copia os CSVs e chama ``importar(caminho, caso, participante)`` para cada um."""
    copiar_sessoes(entradas, pasta_origem, pasta_destino)
    resumo = Resumo()
    for entrada in entradas:
        try:
            importar(pasta_destino / entrada.sessao, entrada.caso, entrada.participante)
        except ValueError as erro:
            if "já importado" not in str(erro):
                raise
            resumo.ja_importadas.append(entrada.sessao)
        else:
            resumo.importadas.append(entrada.sessao)
    return resumo


def main(argv: Optional[List[str]] = None) -> int:
    import psycopg

    from coleta.arquivos import ARQUIVO_ATTEMPTS
    from coleta.config import Config
    from coleta.importador import importar

    parser = argparse.ArgumentParser(prog="python -m coleta.lote", description=__doc__.split("\n\n")[0])
    parser.add_argument("--manifesto", type=Path, default=MANIFESTO)
    parser.add_argument("--origem", type=Path, default=PASTA_FIRMWARE)
    parser.add_argument("--sessoes", type=Path, default=PASTA_SESSOES)
    args = parser.parse_args(argv)

    config = Config.do_ambiente()
    try:
        entradas = ler_manifesto(args.manifesto)
        with psycopg.connect(config.pg_dsn) as con:
            resumo = executar(
                entradas,
                args.origem,
                args.sessoes,
                lambda caminho, caso, participante: importar(
                    con, caminho, caso, participante, config.placa, ARQUIVO_ATTEMPTS
                ),
            )
    except (ValueError, OSError, psycopg.OperationalError) as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"Importadas: {len(resumo.importadas)}; já estavam no banco: {len(resumo.ja_importadas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
