"""Leitura das linhas que o firmware escreve na serial.

O firmware manda duas linhas que interessam:

- ``CSV_ARQUIVO,<nome>``: a placa ligou (ou reiniciou) e abriu um CSV novo;
- ``CSV_LINHA,<nome>,<campos>``: uma leitura, com os mesmos campos do CSV.

Todo o resto (mensagens de depuração, lixo do boot, linhas cortadas) é ignorado.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Optional, Union

COLUNAS_FIRMWARE = (
    "amostra",
    "t_ms",
    "mq3_raw",
    "ppm",
    "mq135_raw",
    "mq135_mv",
    "temperature_c",
    "humidity_pct",
    "alcool",
)
CABECALHO_CSV = ",".join(COLUNAS_FIRMWARE) + "\n"

_PREFIXO_LINHA = "CSV_LINHA,"
_PREFIXO_ARQUIVO = "CSV_ARQUIVO,"


@dataclass(frozen=True)
class Leitura:
    """Uma leitura dos sensores, como o firmware gravou."""

    amostra: int
    t_ms: int
    mq3_raw: int
    ppm: Optional[float]
    mq135_raw: Optional[int]
    mq135_mv: Optional[int]
    temperature_c: Optional[float]
    humidity_pct: Optional[float]
    alcool: Optional[int]
    bruta: str = field(default="", compare=False, repr=False)

    def como_linha_csv(self) -> str:
        """A linha do CSV, idêntica à que o firmware mandou quando ela é conhecida."""
        if self.bruta:
            return self.bruta
        return ",".join("" if valor is None else str(valor) for valor in self._valores())

    def como_dict(self) -> dict:
        """Os campos do firmware, sem a linha bruta."""
        dados = asdict(self)
        dados.pop("bruta")
        return dados

    def _valores(self) -> list:
        return [getattr(self, nome) for nome in COLUNAS_FIRMWARE]


@dataclass(frozen=True)
class ArquivoNovo:
    """A placa abriu um CSV novo: ela ligou ou reiniciou."""

    nome: str


_CONVERSORES: dict[str, Callable[[str], Union[int, float]]] = {
    "amostra": int,
    "t_ms": int,
    "mq3_raw": int,
    "ppm": float,
    "mq135_raw": int,
    "mq135_mv": int,
    "temperature_c": float,
    "humidity_pct": float,
    "alcool": int,
}
_OBRIGATORIOS = {"amostra", "t_ms", "mq3_raw"}


def ler_linha(bruta: Union[bytes, str]) -> Union[Leitura, ArquivoNovo, None]:
    """Interpreta uma linha da serial; devolve ``None`` para o que não for dado."""
    texto = bruta.decode("utf-8", errors="replace") if isinstance(bruta, bytes) else bruta
    texto = texto.strip()
    if "�" in texto:
        return None
    if texto.startswith(_PREFIXO_ARQUIVO):
        nome = texto[len(_PREFIXO_ARQUIVO):]
        return ArquivoNovo(nome) if nome else None
    if texto.startswith(_PREFIXO_LINHA):
        _, _, campos = texto[len(_PREFIXO_LINHA):].partition(",")
        return ler_campos(campos)
    return None


def ler_campos(campos: str) -> Optional[Leitura]:
    """Converte os campos de uma linha do CSV do firmware; ``None`` se forem inválidos."""
    partes = campos.split(",")
    if len(partes) != len(COLUNAS_FIRMWARE):
        return None
    valores = {}
    for nome, parte in zip(COLUNAS_FIRMWARE, partes):
        if parte == "":
            if nome in _OBRIGATORIOS:
                return None
            valores[nome] = None
            continue
        try:
            valores[nome] = _CONVERSORES[nome](parte)
        except ValueError:
            return None
    return Leitura(**valores, bruta=campos)

