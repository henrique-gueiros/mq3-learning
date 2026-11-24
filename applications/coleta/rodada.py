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

    def marcar_inicio_sopro(self, t_ms: Optional[int] = None) -> Optional[Sopro]:
        """Marca um sopro no ``t_ms`` dado (botão da placa) ou no da última leitura (Enter).

        Sem ``t_ms``, precisa de pelo menos uma leitura (Enter). Com ``t_ms`` do
        ``CSV_EVENTO``, o instante da placa vale mesmo antes da primeira linha.
        ``None`` se faltar instante ou se já há um sopro nesse mesmo instante.
        """
        if t_ms is None and self.ultimo_t_ms is None:
            return None
        instante = self.ultimo_t_ms if t_ms is None else t_ms
        if self.sopros and self.sopros[-1].inicio_ms == instante:
            return None
        sopro = Sopro(instante)
        self.sopros.append(sopro)
        return sopro

    def marcar_fim_sopro(self, t_ms: Optional[int] = None) -> Optional[Sopro]:
        """Fecha o último sopro no ``t_ms`` dado (botão da placa) ou no da última leitura.

        ``None`` se não houver sopro aberto, se faltar instante (Enter sem
        leitura) ou se o fim não for posterior ao início.
        """
        if not self.sopros or self.sopros[-1].fim_ms is not None:
            return None
        if t_ms is None and self.ultimo_t_ms is None:
            return None
        sopro = self.sopros[-1]
        instante = self.ultimo_t_ms if t_ms is None else t_ms
        if instante <= sopro.inicio_ms:
            return None
        sopro.fim_ms = instante
        return sopro

    def terminou(self) -> bool:
        """``True`` quando a duração pedida já foi coberta pelas leituras."""
        if self.duracao_s is None or self._primeiro_t_ms is None:
            return False
        return self.ultimo_t_ms - self._primeiro_t_ms >= self.duracao_s * 1000
