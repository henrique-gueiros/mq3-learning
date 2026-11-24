"""Leitura das linhas que o firmware escreve na serial.

O firmware manda duas linhas que interessam:

- ``CSV_ARQUIVO,<nome>``: a placa ligou (ou reiniciou) e abriu um CSV novo;
- ``CSV_LINHA,<nome>,<campos>``: uma leitura, com os mesmos campos do CSV;
- ``CSV_EVENTO,<nome>,<tipo>,<t_ms>``: o botão da placa marcou ``sopro_inicio``,
  ``sopro_fim`` ou ``rodada_fim`` no relógio dela (firmware com FreeRTOS).

Todo o resto (mensagens de depuração, lixo do boot, linhas cortadas) é ignorado.

O firmware já teve três formatos de CSV: o de 9 colunas, o de 11 (acrescenta ``rs``
e ``rs_rsar``) e o de 13 (acrescenta ainda ``tensao_atual_mv`` e
``tensao_referencia_mv``). Todos são aceitos; o formato é reconhecido pelo número
de campos. Só as 9 colunas
originais são guardadas na ``Leitura``; a linha bruta preserva o resto.
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

COLUNAS_COM_RS_11 = (
    "amostra",
    "t_ms",
    "mq3_raw",
    "ppm",
    "rs",
    "rs_rsar",
    "mq135_raw",
    "mq135_mv",
    "temperature_c",
    "humidity_pct",
    "alcool",
)
COLUNAS_COM_RS = COLUNAS_COM_RS_11 + ("tensao_atual_mv", "tensao_referencia_mv")
CABECALHO_COM_RS = ",".join(COLUNAS_COM_RS) + "\n"

FORMATOS = {len(colunas): colunas for colunas in (COLUNAS_FIRMWARE, COLUNAS_COM_RS_11, COLUNAS_COM_RS)}
CABECALHOS_ACEITOS = frozenset(",".join(colunas) for colunas in FORMATOS.values())

_PREFIXO_LINHA = "CSV_LINHA,"
_PREFIXO_ARQUIVO = "CSV_ARQUIVO,"
_PREFIXO_EVENTO = "CSV_EVENTO,"
TIPOS_EVENTO_PLACA = ("sopro_inicio", "sopro_fim", "rodada_fim")


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
    colunas: tuple = field(default=COLUNAS_FIRMWARE, compare=False, repr=False)

    @property
    def cabecalho_csv(self) -> str:
        """O cabeçalho do formato em que a placa mandou esta leitura."""
        return ",".join(self.colunas) + "\n"

    def como_linha_csv(self) -> str:
        """A linha do CSV, idêntica à que o firmware mandou quando ela é conhecida."""
        if self.bruta:
            return self.bruta
        return ",".join("" if valor is None else str(valor) for valor in self._valores())

    def como_dict(self) -> dict:
        """Os campos do firmware, sem a linha bruta."""
        dados = asdict(self)
        dados.pop("bruta")
        dados.pop("colunas")
        return dados

    def _valores(self) -> list:
        return [getattr(self, nome) for nome in COLUNAS_FIRMWARE]


@dataclass(frozen=True)
class ArquivoNovo:
    """A placa abriu um CSV novo: ela ligou ou reiniciou."""

    nome: str


@dataclass(frozen=True)
class EventoPlaca:
    """O botão da placa marcou um evento, no ``t_ms`` do relógio dela."""

    arquivo: str
    tipo: str
    t_ms: int


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
    "rs": float,
    "rs_rsar": float,
    "tensao_atual_mv": float,
    "tensao_referencia_mv": float,
}
_GUARDADAS = set(COLUNAS_FIRMWARE)
_OBRIGATORIOS = {"amostra", "t_ms", "mq3_raw"}


def ler_linha(bruta: Union[bytes, str]) -> Union[Leitura, ArquivoNovo, EventoPlaca, None]:
    """Interpreta uma linha da serial; devolve ``None`` para o que não for dado."""
    texto = bruta.decode("utf-8", errors="replace") if isinstance(bruta, bytes) else bruta
    texto = texto.strip()
    if "�" in texto:
        return None
    if texto.startswith(_PREFIXO_ARQUIVO):
        nome = texto[len(_PREFIXO_ARQUIVO):]
        return ArquivoNovo(nome) if nome else None
    if texto.startswith(_PREFIXO_EVENTO):
        partes = texto[len(_PREFIXO_EVENTO):].split(",")
        if len(partes) != 3 or partes[1] not in TIPOS_EVENTO_PLACA:
            return None
        try:
            return EventoPlaca(partes[0], partes[1], int(partes[2]))
        except ValueError:
            return None
    if texto.startswith(_PREFIXO_LINHA):
        _, _, campos = texto[len(_PREFIXO_LINHA):].partition(",")
        return ler_campos(campos)
    return None


def ler_campos(campos: str) -> Optional[Leitura]:
    """Converte os campos de uma linha do CSV do firmware; ``None`` se forem inválidos."""
    partes = campos.split(",")
    colunas = FORMATOS.get(len(partes))
    if colunas is None:
        return None
    valores = {}
    for nome, parte in zip(colunas, partes):
        if parte == "":
            if nome in _OBRIGATORIOS:
                return None
            if nome in _GUARDADAS:
                valores[nome] = None
            continue
        try:
            convertido = _CONVERSORES[nome](parte)
        except ValueError:
            return None
        if nome in _GUARDADAS:
            valores[nome] = convertido
    return Leitura(**valores, bruta=campos, colunas=colunas)

