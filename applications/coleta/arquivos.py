"""Arquivos que a coleta entrega ao pipeline de ML.

- o CSV de sessão, no formato exato do firmware, em ``ml/data/raw/sessions/``;
- as linhas de ``ml/data/raw/attempts.csv``, uma por sopro marcado.
"""

from __future__ import annotations

import csv
import hashlib
import os
from datetime import date
from pathlib import Path
from typing import List

from coleta.rodada import Rodada
from coleta.serial_proto import Leitura

REPO = Path(__file__).resolve().parents[2]
PASTA_SESSOES = REPO / "ml" / "data" / "raw" / "sessions"
ARQUIVO_ATTEMPTS = REPO / "ml" / "data" / "raw" / "attempts.csv"
_TEMPLATE_ATTEMPTS = REPO / "ml" / "templates" / "attempts_template.csv"


def nome_sessao(pasta: Path, data: date, participante: str, caso: str) -> Path:
    """Primeiro nome livre ``AAAA-MM-DD_<participante>_<caso>_<n>.csv`` na pasta."""
    n = 1
    while True:
        caminho = pasta / f"{data:%Y-%m-%d}_{participante}_{caso}_{n}.csv"
        if not caminho.exists():
            return caminho
        n += 1


class CsvSessao:
    """CSV de uma rodada, gravado linha a linha para não perder nada se algo cair."""

    def __init__(self, caminho: Path):
        self.caminho = caminho
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self._arquivo = caminho.open("x", encoding="utf-8", newline="\n")
        self._leituras = 0

    def escrever(self, leitura: Leitura) -> None:
        if self._leituras == 0:
            self._arquivo.write(leitura.cabecalho_csv)
        self._arquivo.write(leitura.como_linha_csv() + "\n")
        self._arquivo.flush()
        os.fsync(self._arquivo.fileno())
        self._leituras += 1

    def fechar(self) -> str:
        """Fecha o arquivo e devolve o SHA-256; um CSV sem leituras é apagado (``""``)."""
        self._arquivo.close()
        if self._leituras == 0:
            self.caminho.unlink()
            return ""
        return hashlib.sha256(self.caminho.read_bytes()).hexdigest()


def linha_attempt(rodada: Rodada, k: int, arquivo_sessao: Path) -> dict:
    """Linha do ``attempts.csv`` para o ``k``-ésimo sopro (a partir de 1) da rodada."""
    sopro = rodada.sopros[k - 1]
    return {
        "attempt_id": f"{arquivo_sessao.stem}_s{k}",
        "session_file": arquivo_sessao.name,
        "participant_id": rodada.participante,
        "condition": rodada.caso,
        "blow_start_s": str(sopro.inicio_ms / 1000),
        "blow_end_s": "" if sopro.fim_ms is None else str(sopro.fim_ms / 1000),
        "reference_mg_l": "",
        "notes": "",
    }


def anexar_attempts(caminho: Path, linhas: List[dict]) -> None:
    """Acrescenta as linhas ao ``attempts.csv``, criando-o com o cabeçalho do template."""
    if not linhas:
        return
    colunas = _TEMPLATE_ATTEMPTS.read_text(encoding="utf-8").strip().split(",")
    novo = not caminho.exists()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, lineterminator="\n")
        if novo:
            escritor.writeheader()
        escritor.writerows(linhas)
