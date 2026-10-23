"""Tentativas montadas à mão para testar o código. Não representam o sensor real."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_validation import validate_attempts, validate_readings

PHASE_SECONDS = {"before": 10, "blow": 5, "after": 15}
SHAPES = {
    "clean": {"mq3": (100, 5), "mq135": (200, 3)},
    "perfume": {"mq3": (400, 10), "mq135": (300, 40)},
    "drink": {"mq3": (100, 400), "mq135": (200, 60)},
}


def make_attempt(attempt_id: str, condition: str, start: str, seed: int = 0) -> pd.DataFrame:
    """Uma tentativa com 10 s antes, 5 s de sopro e 15 s depois, uma leitura por segundo."""
    rng = np.random.default_rng(seed)
    phases = [phase for phase, seconds in PHASE_SECONDS.items() for _ in range(seconds)]
    n = len(phases)
    t = np.arange(n)
    blow_start = PHASE_SECONDS["before"]
    pulse = np.clip(1 - np.abs(t - (blow_start + 3)) / 6, 0, None)

    shape = SHAPES[condition]
    mq3 = shape["mq3"][0] + shape["mq3"][1] * pulse + rng.normal(0, 2, n)
    mq135 = shape["mq135"][0] + shape["mq135"][1] * pulse + rng.normal(0, 2, n)
    humidity = 50 + 30 * np.clip(1 - np.abs(t - (blow_start + 4)) / 6, 0, None)
    temperature = 25 + 2 * pulse
    humidity[1::2] = np.nan
    temperature[1::2] = np.nan

    return pd.DataFrame(
        {
            "timestamp": pd.date_range(pd.Timestamp(start), periods=n, freq="1s"),
            "attempt_id": attempt_id,
            "phase": phases,
            "mq3_raw": mq3,
            "mq135_raw": mq135,
            "temperature_c": temperature,
            "humidity_pct": humidity,
        }
    )


def make_dataset(n_participants: int = 6, repetitions: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leituras e tentativas validadas: cada participante faz clean, perfume e drink."""
    frames, attempts = [], []
    start = pd.Timestamp("2026-10-20T14:00:00-03:00")
    seed = 0
    for p in range(1, n_participants + 1):
        for condition in SHAPES:
            for r in range(repetitions):
                seed += 1
                attempt_id = f"p{p}-{condition}-{r}"
                frames.append(make_attempt(attempt_id, condition, (start + pd.Timedelta(minutes=seed)).isoformat(), seed))
                attempts.append(
                    {
                        "attempt_id": attempt_id,
                        "participant_id": f"p{p}",
                        "session_id": f"p{p}-s{r}",
                        "condition": condition,
                    }
                )
    readings = validate_readings(pd.concat(frames, ignore_index=True))
    return readings, validate_attempts(pd.DataFrame(attempts))
