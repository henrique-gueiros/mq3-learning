"""Casos aceitos numa rodada.

A lista é a mesma do pipeline de ML (``CONDITIONS`` em
``applications/ml/src/data_validation.py``), lida de lá para não existir uma cópia que
possa ficar desatualizada.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_VALIDACAO_ML = Path(__file__).resolve().parents[1] / "ml" / "src" / "data_validation.py"


def _carregar_casos() -> frozenset[str]:
    spec = importlib.util.spec_from_file_location("_ml_data_validation", _VALIDACAO_ML)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return frozenset(modulo.CONDITIONS)


CASOS = _carregar_casos()


def validar_caso(caso: str) -> str:
    """Devolve o caso se ele for conhecido; senão explica quais são aceitos."""
    if caso not in CASOS:
        raise ValueError(f"caso desconhecido: {caso!r}; use um de {sorted(CASOS)}")
    return caso
