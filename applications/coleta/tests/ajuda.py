"""Leituras montadas à mão para os testes; não representam o sensor real."""

from __future__ import annotations

from coleta.serial_proto import Leitura


def leitura(amostra: int, t_ms: int, mq3_raw: int = 1200) -> Leitura:
    return Leitura(amostra, t_ms, mq3_raw, 0.4, 450, 520, 30.0, 50.0, 0)
