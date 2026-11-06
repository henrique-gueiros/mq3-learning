"""Estado de uma rodada de coleta: um caso, um participante, um CSV.

Esta classe não lê a serial nem grava arquivos; só decide o que cada evento
significa. Assim as regras (reinício da placa, sopros, duração) ficam testáveis.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Optional, Union

from coleta.serial_proto import ArquivoNovo, Leitura

LEITURA = "leitura"
IGNORAR = "ignorar"
REINICIOU = "reiniciou"


@dataclass
class Sopro:
    """Um sopro marcado pelo operador, em ``t_ms`` da placa."""

    inicio_ms: int
    fim_ms: Optional[int] = None


class Rodada:
    """Uma rodada em andamento."""

    def __init__(self, caso: str, participante: str, duracao_s: Optional[float]):
        self.id = str(uuid.uuid4())
        self.caso = caso
        self.participante = participante
        self.duracao_s = duracao_s
        self.leituras = 0
        self.sopros: List[Sopro] = []
        self.ultimo_t_ms: Optional[int] = None
        self._primeiro_t_ms: Optional[int] = None
        self._ultima_amostra: Optional[int] = None

    def receber(self, evento: Union[Leitura, ArquivoNovo]) -> str:
        """Classifica um evento da serial.

        Devolve ``"leitura"`` (gravar), ``"ignorar"`` ou ``"reiniciou"``: a placa
        reiniciou no meio da rodada, que deve ser encerrada e substituída.
        """
        if isinstance(evento, ArquivoNovo):
            return IGNORAR if self.leituras == 0 else REINICIOU
        if self._ultima_amostra is not None and evento.amostra <= self._ultima_amostra:
            return REINICIOU
        if self._primeiro_t_ms is None:
            self._primeiro_t_ms = evento.t_ms
        self._ultima_amostra = evento.amostra
        self.ultimo_t_ms = evento.t_ms
        self.leituras += 1
        return LEITURA

    def marcar_inicio_sopro(self) -> Optional[Sopro]:
        """Marca um sopro no ``t_ms`` da última leitura; ``None`` se ainda não houve leitura."""
        if self.ultimo_t_ms is None:
            return None
        sopro = Sopro(self.ultimo_t_ms)
        self.sopros.append(sopro)
        return sopro

    def marcar_fim_sopro(self) -> Optional[Sopro]:
        """Fecha o último sopro; ``None`` se não houver sopro aberto."""
        if not self.sopros or self.sopros[-1].fim_ms is not None or self.ultimo_t_ms is None:
            return None
        self.sopros[-1].fim_ms = self.ultimo_t_ms
        return self.sopros[-1]

    def terminou(self) -> bool:
        """``True`` quando a duração pedida já foi coberta pelas leituras."""
        if self.duracao_s is None or self._primeiro_t_ms is None:
            return False
        return self.ultimo_t_ms - self._primeiro_t_ms >= self.duracao_s * 1000
