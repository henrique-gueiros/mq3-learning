from __future__ import annotations

import pandas as pd
import pytest

from src.data_generation import ClassParams, SyntheticParams, generate_synthetic


def make_params(n_sessions: int = 4, samples: int = 20, seed: int = 0) -> SyntheticParams:
    return SyntheticParams(
        classes={
            0: ClassParams(n_sessions, samples, level_mean=100.0, level_std=10.0, noise_std=5.0),
            1: ClassParams(n_sessions, samples, level_mean=200.0, level_std=10.0, noise_std=5.0),
        },
        seed=seed,
    )


def make_fake_real(n_sessions: int = 4, samples: int = 20, seed: int = 0) -> pd.DataFrame:
    """Leituras no formato real, geradas pelo simulador, só para testar o pipeline."""
    df = generate_synthetic(make_params(n_sessions, samples, seed))
    df["session_id"] = df["session_id"].str.replace("syn-", "real-", regex=False)
    df["source"] = "real"
    df["notes"] = "teste"
    return df


@pytest.fixture
def raw_csv_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-10-20T14:00:00-03:00",
                "2026-10-20T14:00:01-03:00",
                "2026-10-20T15:00:00-03:00",
            ],
            "session_id": ["s1", "s1", "s2"],
            "sensor_raw": ["512", "530.5", "900"],
            "label": [0, None, 1],
            "source": ["real", "real", "real"],
        }
    )
