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
    def raw_sessions_dir(self) -> Path:
        return self.raw_dir / "sessions"

    @property
    def raw_attempts(self) -> Path:
        return self.raw_dir / "attempts.csv"

    @property
    def processed_dir(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def features_all(self) -> Path:
        return self.processed_dir / "features_all.csv"

    @property
    def train(self) -> Path:
        return self.processed_dir / "train.csv"

    @property
    def test(self) -> Path:
        return self.processed_dir / "test.csv"

    @property
    def disponivel(self) -> Path:
        """Manifesto que declara o dataset pronto para o treino."""
        return self.processed_dir / "disponivel.json"

    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    @property
    def split_manifest(self) -> Path:
        return self.config_dir / "split.json"

    @property
    def models_dir(self) -> Path:
        return self.root / "models"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"
