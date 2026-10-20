from __future__ import annotations

import pandas as pd
import pytest

from src.data_generation import generate_synthetic
from src.preprocessing import build_train_test, to_xy
from tests.conftest import make_fake_real, make_params


def _real_train_test():
    df = make_fake_real(n_sessions=4)
    test_ids = {"real-0001", "real-0002"}
    return df[~df["session_id"].isin(test_ids)], df[df["session_id"].isin(test_ids)]


def test_synthetic_goes_only_to_train():
    real_train, real_test = _real_train_test()
    synthetic = generate_synthetic(make_params())
    train, test, _ = build_train_test(real_train, real_test, synthetic)

    assert set(train["source"]) == {"real", "synthetic"}
    assert set(test["source"]) == {"real"}
    assert len(train) == len(real_train) + len(synthetic)


def test_test_set_with_synthetic_rows_is_rejected():
    real_train, real_test = _real_train_test()
    real_test = real_test.copy()
    real_test.loc[real_test.index[0], "source"] = "synthetic"
    with pytest.raises(ValueError, match="teste"):
        build_train_test(real_train, real_test)


def test_session_id_collision_is_rejected():
    real_train, real_test = _real_train_test()
    synthetic = generate_synthetic(make_params())
    synthetic["session_id"] = real_train["session_id"].iloc[0]
    with pytest.raises(ValueError, match="session_id"):
        build_train_test(real_train, real_test, synthetic)


def test_didactic_synthetic_produces_warning():
    real_train, real_test = _real_train_test()
    synthetic = generate_synthetic(make_params())
    _, _, warnings = build_train_test(real_train, real_test, synthetic)
    assert any("didáticos" in w for w in warnings)


def test_synthetic_majority_produces_warning():
    real_train, real_test = _real_train_test()
    synthetic = generate_synthetic(make_params(n_sessions=10))
    _, _, warnings = build_train_test(real_train, real_test, synthetic)
    assert any("mais leituras sintéticas" in w for w in warnings)


def test_unlabeled_rows_are_dropped():
    real_train, real_test = _real_train_test()
    real_train = real_train.copy()
    real_train.loc[real_train.index[:3], "label"] = pd.NA
    train, _, warnings = build_train_test(real_train, real_test)

    assert train["label"].notna().all()
    assert any("sem rótulo" in w for w in warnings)


def test_to_xy_returns_features_labels_and_groups():
    df = make_fake_real(n_sessions=2)
    X, y, groups = to_xy(df)

    assert list(X.columns) == ["sensor_raw"]
    assert set(y.unique()) == {0, 1}
    assert len(X) == len(y) == len(groups)
