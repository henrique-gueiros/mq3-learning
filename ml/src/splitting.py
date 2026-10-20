"""Separação treino/teste por sessão experimental.

Leituras da mesma sessão são muito parecidas entre si. Se parte de uma sessão
fosse para o treino e parte para o teste, o modelo "veria" o teste durante o
treino (vazamento de dados). Por isso a separação é feita por ``session_id``.

A separação fica gravada em um manifesto JSON versionado no Git. Quando chegam
sessões novas, as antigas mantêm o lado em que estavam e só as novas são sorteadas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class SessionSplit:
    """Quais sessões são de treino e quais são de teste."""

    train_sessions: list[str] = field(default_factory=list)
    test_sessions: list[str] = field(default_factory=list)
    test_size: float = 0.25
    seed: int = 42

    def to_dict(self) -> dict:
        return {
            "note": (
                "Sessões de teste são reservadas para a avaliação final: "
                "não use para treinar nem para estimar o gerador sintético."
            ),
            "test_size": self.test_size,
            "seed": self.seed,
            "train_sessions": sorted(self.train_sessions),
            "test_sessions": sorted(self.test_sessions),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionSplit:
        split = cls(
            train_sessions=list(data["train_sessions"]),
            test_sessions=list(data["test_sessions"]),
            test_size=float(data["test_size"]),
            seed=int(data["seed"]),
        )
        overlap = set(split.train_sessions) & set(split.test_sessions)
        if overlap:
            raise ValueError(f"manifesto inválido: sessões em treino e teste ao mesmo tempo: {sorted(overlap)}")
        return split


def load_split(path: Path) -> SessionSplit | None:
    """Lê o manifesto, ou devolve ``None`` se ele ainda não existe."""
    path = Path(path)
    if not path.exists():
        return None
    return SessionSplit.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_split(split: SessionSplit, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(split.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def session_classes(df: pd.DataFrame) -> pd.Series:
    """Classe de cada sessão rotulada: 1 se tem alguma leitura com álcool, senão 0."""
    labeled = df.dropna(subset=["label"])
    return labeled.groupby("session_id")["label"].max().astype(int)


def split_sessions(
    classes: pd.Series, test_size: float = 0.25, seed: int = 42
) -> tuple[list[str], list[str], list[str]]:
    """Sorteia sessões para teste, separadamente para cada classe (estratificado).

    Args:
        classes: classe de cada sessão, indexada por ``session_id``.
        test_size: fração aproximada de sessões de cada classe que vai para teste.
        seed: semente do sorteio, para o resultado ser reproduzível.

    Returns:
        ``(sessões de treino, sessões de teste, avisos)``.
    """
    if not 0 < test_size < 1:
        raise ValueError("test_size deve estar entre 0 e 1")

    rng = np.random.default_rng(seed)
    train: list[str] = []
    test: list[str] = []
    warnings: list[str] = []
    for cls in sorted(classes.unique()):
        ids = sorted(str(s) for s in classes[classes == cls].index)
        if len(ids) < 2:
            warnings.append(
                f"classe {cls} tem só {len(ids)} sessão; ela foi para o treino e "
                "o teste ficou sem essa classe"
            )
            train.extend(ids)
            continue
        n_test = min(max(1, int(round(len(ids) * test_size))), len(ids) - 1)
        shuffled = [str(s) for s in rng.permutation(ids)]
        test.extend(shuffled[:n_test])
        train.extend(shuffled[n_test:])
    return sorted(train), sorted(test), warnings


def update_split(
    df: pd.DataFrame,
    existing: SessionSplit | None,
    test_size: float = 0.25,
    seed: int = 42,
) -> tuple[SessionSplit, list[str]]:
    """Mantém a separação existente e sorteia apenas as sessões novas.

    Se já existe manifesto, ``test_size`` e ``seed`` do manifesto prevalecem.
    Sessões sem nenhum rótulo ficam de fora (não dá para estratificar nem avaliar).
    """
    warnings: list[str] = []
    if existing is not None:
        if (existing.test_size, existing.seed) != (test_size, seed):
            warnings.append(
                f"usando test_size={existing.test_size} e seed={existing.seed} do manifesto existente"
            )
        test_size, seed = existing.test_size, existing.seed
        split = SessionSplit(list(existing.train_sessions), list(existing.test_sessions), test_size, seed)
    else:
        split = SessionSplit(test_size=test_size, seed=seed)

    all_sessions = set(df["session_id"].unique())
    classes = session_classes(df)
    unlabeled = sorted(all_sessions - set(classes.index))
    if unlabeled:
        warnings.append(f"sessões sem rótulo ignoradas na separação: {unlabeled}")

    known = set(split.train_sessions) | set(split.test_sessions)
    missing = sorted(known - all_sessions)
    if missing:
        warnings.append(f"sessões do manifesto que não estão mais nos dados: {missing}")

    new_classes = classes[~classes.index.isin(known)]
    if not new_classes.empty:
        new_train, new_test, split_warnings = split_sessions(new_classes, test_size, seed)
        split.train_sessions.extend(new_train)
        split.test_sessions.extend(new_test)
        warnings.extend(split_warnings)
    return split, warnings


def apply_split(df: pd.DataFrame, split: SessionSplit) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve ``(treino, teste)`` com as leituras de cada lado da separação."""
    train = df[df["session_id"].isin(split.train_sessions)].reset_index(drop=True)
    test = df[df["session_id"].isin(split.test_sessions)].reset_index(drop=True)
    return train, test
