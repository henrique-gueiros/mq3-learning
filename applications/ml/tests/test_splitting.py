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


def test_warns_when_a_class_is_missing_from_test():
    dataset = _dataset(n_participants=4)
    split, _ = update_split(dataset, existing=None)
    only_clean_in_test = dataset[
        ~dataset["participant_id"].isin(split.test_groups) | (dataset["target"] == "sem_efeito")
    ]
    _, warnings = update_split(only_clean_in_test, existing=split)
    assert any("classes ausentes no teste" in w for w in warnings)


def test_invalid_group_column():
    with pytest.raises(ValueError, match="group_by"):
        update_split(_dataset(4), existing=None, group_by="condition")


def test_manifest_round_trip(tmp_path):
    split = GroupSplit("participant_id", ["a", "b"], ["c"], test_size=0.3, seed=1)
    save_split(split, tmp_path / "split.json")
    assert load_split(tmp_path / "split.json") == split
    assert load_split(tmp_path / "missing.json") is None
