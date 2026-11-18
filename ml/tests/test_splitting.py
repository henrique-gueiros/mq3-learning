from __future__ import annotations

import pandas as pd
import pytest

from src.splitting import GroupSplit, apply_split, load_split, save_split, update_split
from tests.conftest import make_feature_dataset


def _dataset(n_participants: int = 8) -> pd.DataFrame:
    return make_feature_dataset(n_participants=n_participants, repetitions=1)


def test_no_participant_in_both_sides():
    dataset = _dataset()
    split, warnings = update_split(dataset, existing=None)
    train, test = apply_split(dataset, split)

    assert not set(train["participant_id"]) & set(test["participant_id"])
    assert len(train) + len(test) == len(dataset)
    assert len(split.test_groups) == 2
    assert warnings == []


def test_split_by_session():
    dataset = _dataset(n_participants=4)
    split, _ = update_split(dataset, existing=None, group_by="session_file")
    train, test = apply_split(dataset, split)
    assert not set(train["session_file"]) & set(test["session_file"])


def test_existing_assignment_is_kept_when_new_participants_arrive():
    old = _dataset(n_participants=4)
    first, _ = update_split(old, existing=None)

    new = _dataset(n_participants=8)
    second, warnings = update_split(new, existing=first, seed=99)

    assert set(first.test_groups) <= set(second.test_groups)
    assert set(first.train_groups) <= set(second.train_groups)
    assert len(second.train_groups) + len(second.test_groups) == 8
    assert any("manifesto existente" in w for w in warnings)


def test_classe_ausente_no_teste_recebe_um_grupo_do_treino():
    dataset = pd.DataFrame(
        {
            "session_file": ["a.csv", "b.csv", "c.csv", "d.csv"],
            "participant_id": ["p", "p", "p", "p"],
            "target": ["sob_efeito", "sob_efeito", "sem_efeito", "sem_efeito"],
            "attempt_id": ["a", "b", "c", "d"],
        }
    )
    existente = GroupSplit(
        "session_file",
        ["a.csv", "b.csv", "c.csv"],
        ["d.csv"],
        test_size=0.25,
        seed=42,
    )

    split, warnings = update_split(dataset, existing=existente, group_by="session_file")
    train, test = apply_split(dataset, split)

    assert set(train["target"]) == {"sem_efeito", "sob_efeito"}
    assert set(test["target"]) == {"sem_efeito", "sob_efeito"}
    assert any("sob_efeito" in aviso for aviso in warnings)


def test_avisa_quando_a_classe_so_existe_em_um_grupo():
    dataset = pd.DataFrame(
        {
            "session_file": ["a.csv", "c.csv"],
            "participant_id": ["p", "p"],
            "target": ["sob_efeito", "sem_efeito"],
            "attempt_id": ["a", "c"],
        }
    )
    existente = GroupSplit("session_file", ["a.csv"], ["c.csv"], test_size=0.25, seed=42)

    _, warnings = update_split(dataset, existing=existente, group_by="session_file")

    assert any("classes ausentes no teste" in aviso for aviso in warnings)


def test_invalid_group_column():
    with pytest.raises(ValueError, match="group_by"):
        update_split(_dataset(4), existing=None, group_by="condition")


def test_manifest_round_trip(tmp_path):
    split = GroupSplit("participant_id", ["a", "b"], ["c"], test_size=0.3, seed=1)
    save_split(split, tmp_path / "split.json")
    assert load_split(tmp_path / "split.json") == split
    assert load_split(tmp_path / "missing.json") is None
