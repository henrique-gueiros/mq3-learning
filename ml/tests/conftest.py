"""Sessões montadas à mão, no formato do firmware, para testar o código.

As curvas são simples e não representam o sensor real.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_validation import validate_attempts, validate_readings
from src.features import assign_phases, build_dataset, compute_features

BLOW_START_S = 20
SESSION_SECONDS = 60
SHAPES = {
    "clean": {"mq3": (1200, 10), "mq135": (450, 5)},
    "perfume": {"mq3": (1700, 30), "mq135": (700, 120)},
    "drink": {"mq3": (1200, 800), "mq135": (450, 300)},
}


def make_session(condition: str, seed: int = 0, blow_start_s: float = BLOW_START_S) -> pd.DataFrame:
    """Um CSV de sessão como o do firmware: uma leitura a cada ~1,08 s, DHT11 a cada 2 s."""
    rng = np.random.default_rng(seed)
    t_ms = np.cumsum(rng.integers(1050, 1110, SESSION_SECONDS)) - 1000
    t_s = t_ms / 1000
    pulse = np.clip(1 - np.abs(t_s - (blow_start_s + 4)) / 8, 0, None)

    shape = SHAPES[condition]
    mq3 = shape["mq3"][0] + shape["mq3"][1] * pulse + rng.normal(0, 10, SESSION_SECONDS)
    mq135 = shape["mq135"][0] + shape["mq135"][1] * pulse + rng.normal(0, 5, SESSION_SECONDS)
    humidity = 50 + 18 * np.clip(1 - np.abs(t_s - (blow_start_s + 5)) / 8, 0, None)
    temperature = 30 + 1.5 * pulse
    dht = pd.DataFrame({"temperature_c": temperature, "humidity_pct": humidity}).round(1)
    dht.iloc[1::2] = np.nan
    dht = dht.ffill()
    dht.iloc[:2] = np.nan

    return pd.DataFrame(
        {
            "amostra": np.arange(1, SESSION_SECONDS + 1),
            "t_ms": t_ms,
            "mq3_raw": mq3.round().astype(int),
            "ppm": 0.4,
            "mq135_raw": mq135.round().astype(int),
            "mq135_mv": 500,
            "temperature_c": dht["temperature_c"],
            "humidity_pct": dht["humidity_pct"],
            "alcool": (mq3 > 1500).astype(int),
        }
    )


def make_dataset(n_participants: int = 6, repetitions: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leituras e tentativas validadas: cada participante faz clean, perfume e drink.

    Cada tentativa fica num arquivo de sessão próprio, com o sopro em ``BLOW_START_S``.
    """
    frames, attempts = [], []
    seed = 0
    for p in range(1, n_participants + 1):
        for condition in SHAPES:
            for r in range(repetitions):
                seed += 1
                session_file = f"p{p}_{condition}_{r}.csv"
                session = validate_readings(make_session(condition, seed))
                session.insert(0, "session_file", session_file)
                frames.append(session)
                attempts.append(
                    {
                        "attempt_id": f"p{p}-{condition}-{r}",
                        "session_file": session_file,
                        "participant_id": f"p{p}",
                        "condition": condition,
                        "blow_start_s": BLOW_START_S,
                    }
                )
    readings = pd.concat(frames, ignore_index=True)
    readings["session_file"] = readings["session_file"].astype("string")
    return readings, validate_attempts(pd.DataFrame(attempts))


def make_feature_dataset(n_participants: int = 6, repetitions: int = 2) -> pd.DataFrame:
    """Tabela de features por tentativa, como a gerada pelo ``prepare``."""
    readings, attempts = make_dataset(n_participants, repetitions)
    phased, _ = assign_phases(readings, attempts)
    features, _ = compute_features(phased)
    return build_dataset(features, attempts)
