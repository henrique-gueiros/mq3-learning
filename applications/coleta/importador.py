"""Importa para o banco um CSV de sessão gravado sem a ponte.

Uso (de dentro de ``applications/``)::

    python -m coleta.importador ../ml/data/raw/sessions/2026-11-05_p01_perfume_1.csv --caso perfume --participante p01

Os sopros vêm do ``attempts.csv`` (linhas com o mesmo ``session_file``). Um
arquivo já importado (mesmo SHA-256) é recusado, assim como um arquivo que o
``attempts.csv`` associa a outra condição.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set, Tuple

from coleta import banco
from coleta.arquivos import ARQUIVO_ATTEMPTS
from coleta.casos import validar_caso
from coleta.serial_proto import CABECALHO_CSV, Leitura, ler_campos

Sopros = List[Tuple[int, Optional[int]]]


def ler_csv_sessao(caminho: Path) -> List[Leitura]:
    """Leituras de um CSV no formato do firmware; ``ValueError`` aponta a linha ruim."""
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    if not linhas or linhas[0].strip() != CABECALHO_CSV.strip():
        raise ValueError(f"{caminho.name}: cabeçalho diferente do firmware ({CABECALHO_CSV.strip()})")
    leituras = []
    for numero, linha in enumerate(linhas[1:], start=2):
        if not linha.strip():
            continue
        leitura = ler_campos(linha.strip())
        if leitura is None:
            raise ValueError(f"{caminho.name}, linha {numero}: leitura inválida: {linha!r}")
        leituras.append(leitura)
    return leituras


def sopros_do_attempts(attempts: Path, arquivo: str) -> Tuple[Set[str], Sopros]:
    """Condições e sopros (em ms) que o ``attempts.csv`` registra para um arquivo de sessão."""
    if not attempts.exists():
        return set(), []
    condicoes: Set[str] = set()
    sopros: Sopros = []
    with attempts.open(encoding="utf-8", newline="") as entrada:
        for linha in csv.DictReader(entrada):
            if linha["session_file"] != arquivo:
                continue
            condicoes.add(linha["condition"])
            fim = linha.get("blow_end_s") or ""
            sopros.append((_ms(linha["blow_start_s"]), _ms(fim) if fim else None))
    return condicoes, sopros


def importar(con, caminho: Path, caso: str, participante: str, placa: str, attempts: Path) -> str:
    """Grava a sessão como uma rodada de origem ``importador`` e devolve o id."""
    validar_caso(caso)
    leituras = ler_csv_sessao(caminho)
    condicoes, sopros = sopros_do_attempts(attempts, caminho.name)
    if condicoes and condicoes != {caso}:
        raise ValueError(
            f"{caminho.name} aparece no attempts.csv com {sorted(condicoes)}, não só {caso!r}; "
            "uma rodada tem um único caso"
        )
    sha = hashlib.sha256(caminho.read_bytes()).hexdigest()
    existente = banco.rodada_por_sha(con, sha)
    if existente:
        raise ValueError(f"{caminho.name} já importado como rodada {existente}")
    rodada = {
        "rodada_id": str(uuid.uuid4()),
        "placa": placa,
        "caso": caso,
        "participante": participante,
        "inicio": datetime.now(timezone.utc).isoformat(),
        "arquivo_sessao": caminho.name,
        "origem": "importador",
        "sha256": sha,
    }
    return banco.importar_rodada(con, rodada, [l.como_dict() for l in leituras], sopros)


def _ms(segundos: str) -> int:
    return round(float(segundos) * 1000)


def main(argv: Optional[List[str]] = None) -> int:
    import psycopg

    from coleta.config import Config

    parser = argparse.ArgumentParser(prog="python -m coleta.importador", description=__doc__.split("\n\n")[0])
    parser.add_argument("csv", type=Path, help="CSV de sessão no formato do firmware")
    parser.add_argument("--caso", required=True)
    parser.add_argument("--participante", required=True)
    parser.add_argument("--placa", help="padrão: PLACA ou placa01")
    parser.add_argument("--attempts", type=Path, default=ARQUIVO_ATTEMPTS)
    args = parser.parse_args(argv)

    config = Config.do_ambiente()
    try:
        with psycopg.connect(config.pg_dsn) as con:
            rodada_id = importar(con, args.csv, args.caso, args.participante, args.placa or config.placa, args.attempts)
    except (ValueError, OSError, psycopg.OperationalError) as erro:
        print(erro, file=sys.stderr)
        return 1
    print(f"Importado: {args.csv.name} → rodada {rodada_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
