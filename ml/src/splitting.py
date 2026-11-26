"""Separação treino/teste por participante (ou por sessão).

Tentativas da mesma pessoa se parecem entre si. Se uma pessoa aparecesse no
treino e no teste, o modelo poderia aprender a reconhecer a pessoa, e não o
álcool (vazamento de dados). Por isso a separação é feita por grupo:
``participant_id`` por padrão, ou ``session_file`` (o CSV do firmware) quando há
poucos participantes.

A separação fica gravada em ``config/split.json``, versionado no Git. Quando
chegam grupos novos, os antigos continuam do mesmo lado e só os novos são sorteados.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

GROUP_COLUMNS = ("participant_id", "session_file")


@dataclass
class GroupSplit:
    """Quais grupos (participantes ou sessões) são de treino e quais são de teste."""

    group_by: str = "participant_id"
    train_groups: list[str] = field(default_factory=list)
    test_groups: list[str] = field(default_factory=list)
    test_size: float = 0.25
    seed: int = 42
    n_por_classe: int | None = None

    def to_dict(self) -> dict:
        dados = {
            "note": (
                "Grupos de teste são reservados para a avaliação final: "
                "não use para treinar nem para escolher hiperparâmetros."
            ),
            "group_by": self.group_by,
            "test_size": self.test_size,
            "seed": self.seed,
            "train_groups": sorted(self.train_groups),
            "test_groups": sorted(self.test_groups),
        }
        if self.n_por_classe is not None:
            dados["n_por_classe"] = self.n_por_classe
        return dados

    @classmethod
    def from_dict(cls, data: dict) -> GroupSplit:
        split = cls(
            group_by=str(data["group_by"]),
            train_groups=list(data["train_groups"]),
            test_groups=list(data["test_groups"]),
            test_size=float(data["test_size"]),
            seed=int(data["seed"]),
            n_por_classe=None if data.get("n_por_classe") is None else int(data["n_por_classe"]),
        )
        overlap = set(split.train_groups) & set(split.test_groups)
        if overlap:
            raise ValueError(f"manifesto inválido: grupos em treino e teste ao mesmo tempo: {sorted(overlap)}")
        return split


def load_split(path: Path) -> GroupSplit | None:
    """Lê o manifesto, ou devolve ``None`` se ele ainda não existe."""
    path = Path(path)
    if not path.exists():
        return None
    return GroupSplit.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_split(split: GroupSplit, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(split.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_split(
    dataset: pd.DataFrame,
    existing: GroupSplit | None,
    group_by: str = "participant_id",
    test_size: float = 0.25,
    seed: int = 42,
) -> tuple[GroupSplit, list[str]]:
    """Mantém a separação existente e sorteia apenas os grupos novos.

    Se já existe manifesto, ``group_by``, ``test_size`` e ``seed`` dele prevalecem.
    Se uma classe ficou só de um lado e existe em pelo menos dois grupos, um
    desses grupos muda de lado. Treino e teste passam a ter as duas classes.

    Returns:
        ``(separação, avisos)``. Há aviso quando alguma classe ficou fora do
        treino ou do teste.
    """
    if group_by not in GROUP_COLUMNS:
        raise ValueError(f"group_by deve ser um de {list(GROUP_COLUMNS)}")
    if not 0 < test_size < 1:
        raise ValueError("test_size deve estar entre 0 e 1")

    warnings: list[str] = []
    if existing is not None:
        if (existing.group_by, existing.test_size, existing.seed) != (group_by, test_size, seed):
            warnings.append(
                f"usando group_by={existing.group_by}, test_size={existing.test_size} e "
                f"seed={existing.seed} do manifesto existente (apague config/split.json para refazer)"
            )
        split = GroupSplit(
            existing.group_by,
            list(existing.train_groups),
            list(existing.test_groups),
            existing.test_size,
            existing.seed,
            existing.n_por_classe,
        )
    else:
        split = GroupSplit(group_by=group_by, test_size=test_size, seed=seed)

    groups = sorted(str(g) for g in dataset[split.group_by].unique())
    known = set(split.train_groups) | set(split.test_groups)
    new_groups = [g for g in groups if g not in known]
    if new_groups:
        if len(new_groups) < 2:
            warnings.append(f"só 1 {split.group_by} novo ({new_groups[0]}); ele foi para o treino")
            split.train_groups.extend(new_groups)
        else:
            rng = np.random.default_rng(split.seed)
            shuffled = [str(g) for g in rng.permutation(new_groups)]
            n_test = min(max(1, int(round(len(shuffled) * split.test_size))), len(shuffled) - 1)
            split.test_groups.extend(shuffled[:n_test])
            split.train_groups.extend(shuffled[n_test:])

    warnings.extend(_garantir_classes(dataset, split))

    train, test = apply_split(dataset, split)
    for name, part in (("treino", train), ("teste", test)):
        missing = sorted(set(dataset["target"]) - set(part["target"]))
        if missing:
            warnings.append(f"classes ausentes no {name}: {missing}")
    return split, warnings


def _garantir_classes(dataset: pd.DataFrame, split: GroupSplit) -> list[str]:
    """Move um grupo quando uma classe existe em dois ou mais e falta de um lado."""
    alvo = dataset["target"].astype(str)
    coluna = dataset[split.group_by].astype(str)
    rng = np.random.default_rng(split.seed)
    avisos: list[str] = []
    for classe in sorted(alvo.unique()):
        grupos = sorted(coluna[alvo == classe].unique())
        if len(grupos) < 2:
            avisos.append(
                f"classe {classe} está em só 1 {split.group_by}; não dá para colocá-la no treino e no teste"
            )
            continue
        no_treino = [grupo for grupo in grupos if grupo in split.train_groups]
        no_teste = [grupo for grupo in grupos if grupo in split.test_groups]
        if no_treino and no_teste:
            continue
        if not no_teste and len(no_treino) >= 2:
            escolhido = str(rng.permutation(no_treino)[0])
            split.train_groups.remove(escolhido)
            split.test_groups.append(escolhido)
            avisos.append(f"{escolhido} foi para o teste para a classe {classe} aparecer nos dois lados")
        elif not no_treino and len(no_teste) >= 2:
            escolhido = str(rng.permutation(no_teste)[0])
            split.test_groups.remove(escolhido)
            split.train_groups.append(escolhido)
            avisos.append(f"{escolhido} foi para o treino para a classe {classe} aparecer nos dois lados")
    return avisos


def apply_split(dataset: pd.DataFrame, split: GroupSplit) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve ``(treino, teste)`` conforme a separação."""
    groups = dataset[split.group_by].astype(str)
    train = dataset[groups.isin(split.train_groups)].reset_index(drop=True)
    test = dataset[groups.isin(split.test_groups)].reset_index(drop=True)
    return train, test
