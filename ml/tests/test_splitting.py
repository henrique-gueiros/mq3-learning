from __future__ import annotations

import pandas as pd

from src.splitting import (
    SessionSplit,
    apply_split,
    load_split,
    save_split,
    session_classes,
    split_sessions,
    update_split,
)
from tests.conftest import make_fake_real


def test_split_has_no_session_in_both_sides_and_covers_all():
    df = make_fake_real(n_sessions=8)
    split, _ = update_split(df, existing=None)

    assert not set(split.train_sessions) & set(split.test_sessions)
    assert set(split.train_sessions) | set(split.test_sessions) == set(df["session_id"])


def test_split_is_stratified_by_session_class():
    df = make_fake_real(n_sessions=8)
    classes = session_classes(df)
    _, test, _ = split_sessions(classes, test_size=0.25)

    assert sorted(classes[test].unique()) == [0, 1]
    assert len(test) == 4


def test_split_is_deterministic():
    classes = session_classes(make_fake_real(n_sessions=8))
    assert split_sessions(classes, seed=7) == split_sessions(classes, seed=7)


def test_single_session_class_goes_to_train_with_warning():
    classes = pd.Series({"a": 0, "b": 0, "c": 0, "d": 1})
    train, test, warnings = split_sessions(classes)

    assert "d" in train
    assert any("classe 1" in w for w in warnings)


def test_update_keeps_existing_assignment_and_adds_new_sessions():
    old = make_fake_real(n_sessions=4, seed=1)
    first, _ = update_split(old, existing=None)

    new = make_fake_real(n_sessions=4, seed=2)
    new["session_id"] = new["session_id"].str.replace("real-", "new-", regex=False)
    second, _ = update_split(pd.concat([old, new]), existing=first)

    assert set(first.test_sessions) <= set(second.test_sessions)
    assert set(first.train_sessions) <= set(second.train_sessions)
    assert any(s.startswith("new-") for s in second.test_sessions)


def test_unlabeled_sessions_are_left_out():
    df = make_fake_real(n_sessions=4)
    df.loc[df["session_id"] == "real-0001", "label"] = pd.NA
    split, warnings = update_split(df, existing=None)

    assert "real-0001" not in split.train_sessions + split.test_sessions
    assert any("sem rótulo" in w for w in warnings)


def test_manifest_round_trip(tmp_path):
    split = SessionSplit(["a", "b"], ["c"], test_size=0.3, seed=1)
    save_split(split, tmp_path / "split.json")
    assert load_split(tmp_path / "split.json") == split
    assert load_split(tmp_path / "missing.json") is None


def test_apply_split():
    df = make_fake_real(n_sessions=4)
    split, _ = update_split(df, existing=None)
    train, test = apply_split(df, split)

    assert len(train) + len(test) == len(df)
    assert set(test["session_id"]) == set(split.test_sessions)
