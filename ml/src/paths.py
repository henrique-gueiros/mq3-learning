"""Caminhos padrão do projeto, sempre relativos à pasta ``ml/``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProjectPaths:
    """Onde cada etapa do pipeline lê e grava arquivos."""

    root: Path = ML_ROOT

    @property
    def raw_dir(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def synthetic_dir(self) -> Path:
        return self.root / "data" / "synthetic"

    @property
    def processed_dir(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    @property
    def split_manifest(self) -> Path:
        return self.config_dir / "split_sessions.json"

    @property
    def didactic_params(self) -> Path:
        return self.config_dir / "synthetic_didactic.json"

    @property
    def estimated_params(self) -> Path:
        return self.config_dir / "synthetic_estimated.json"

    @property
    def real_train(self) -> Path:
        return self.processed_dir / "real_train.csv"

    @property
    def real_test(self) -> Path:
        return self.processed_dir / "real_test.csv"

    @property
    def train(self) -> Path:
        return self.processed_dir / "train.csv"

    @property
    def test(self) -> Path:
        return self.processed_dir / "test.csv"
