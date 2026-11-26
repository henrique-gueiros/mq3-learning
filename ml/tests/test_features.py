from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data_validation import validate_readings
from src.features import (
    SENSOR_SETS,
    all_feature_columns,
    assign_phases,
    build_dataset,
    compute_features,
    feature_columns,
    selecionar_sem_sobreposicao,
    subidas_contra_o_comeco,
)
from tests.conftest import make_dataset, make_session


def _simple_session() -> pd.DataFrame:
    """MQ-3: 100 antes, pico 300 um segundo depois do início do sopro (t = 20 s)."""
    t_s = [17, 18, 19, 20, 21, 22, 23, 24]
    df = validate_readings(
        pd.DataFrame(
            {
                "t_ms": [t * 1000 for t in t_s],
                "mq3_raw": [100, 100, 100, 200, 300, 250, 150, 120],
                "mq135_raw": [200, 200, 200, 210, 250, 240, 220, 210],
                "temperature_c": [25.0] * 8,
                "humidity_pct": [50, 50, 50, 70, 90, 80, 60, 55],
            }
        )
    )
    df.insert(0, "session_file", "s1.csv")
    return df


def _attempt(start_s: float = 20, end_s: float = 22, attempt_id: str = "a1") -> pd.DataFrame:
    return pd.DataFrame(
        {"attempt_id": [attempt_id], "session_file": ["s1.csv"], "blow_start_s": [start_s], "blow_end_s": [end_s]}
    )


def test_phases_follow_blow_start():
    phased, warnings = assign_phases(_simple_session(), _attempt())

    assert warnings == []
    assert list(phased["phase"]) == ["before"] * 3 + ["blow"] * 3 + ["after"] * 2
    assert set(phased["attempt_id"]) == {"a1"}


def test_features_of_a_simple_attempt():
    phased, _ = assign_phases(_simple_session(), _attempt())
    features, warnings = compute_features(phased)
    row = features.iloc[0]

    assert warnings == []
    assert row["mq3_before"] == 100
    assert row["mq3_peak"] == 300
    assert row["mq3_rise"] == 200
    assert row["mq3_peak_time_s"] == 1
    assert row["mq3_recovery_s"] == 2
    assert row["mq135_mq3_rise_ratio"] == pytest.approx(50 / 200)
    assert row["mq3_humidity_peak_lag_s"] == 0


def test_blow_start_outside_the_session_is_skipped():
    phased, warnings = assign_phases(_simple_session(), _attempt(start_s=500, end_s=505))
    features, _ = compute_features(phased)

    assert features.empty
    assert "blow_start_s" in warnings[0]


def test_subida_contra_o_comeco_nao_usa_o_ar_ja_contaminado():
    # Os primeiros 20 s são o ar da sala (MQ-3 100, umidade 40).
    # Perto do sopro o MQ-3 já está em 250; no sopro chega a 400.
    t_s = [1, 10, 19, 40, 50, 51, 52, 60]
    readings = pd.DataFrame(
        {
            "session_file": ["s1.csv"] * len(t_s),
            "t_ms": [t * 1000 for t in t_s],
            "mq3_raw": [100, 100, 100, 250, 400, 380, 300, 250],
            "mq135_raw": [50, 50, 50, 80, 200, 180, 100, 80],
            "humidity_pct": [40, 40, 40, 55, 70, 68, 60, 50],
        }
    )
    attempts = pd.DataFrame(
        {
            "attempt_id": ["a1"],
            "session_file": ["s1.csv"],
            "blow_start_s": [50.0],
            "blow_end_s": [52.0],
        }
    )

    subidas = subidas_contra_o_comeco(readings, attempts).iloc[0]

    assert subidas["mq3_rise_comeco"] == 300
    assert subidas["humidity_rise_comeco"] == 30
    assert subidas["mq135_rise_comeco"] == 150


def test_janelas_sobrepostas_ficam_de_fora():
    # Janela: 15 s antes e 30 s depois. A próxima só entra quando o "antes"
    # dela não pega o "depois" da anterior (fim 12 + 30 + 15 = 57 s).
    attempts = pd.DataFrame(
        {
            "attempt_id": ["a1", "a2", "a3", "b1"],
            "session_file": ["s1.csv", "s1.csv", "s1.csv", "s2.csv"],
            "blow_start_s": [10.0, 40.0, 57.0, 10.0],
            "blow_end_s": [12.0, 42.0, 59.0, 12.0],
        }
    )

    escolhidas, avisos = selecionar_sem_sobreposicao(attempts)

    assert list(escolhidas["attempt_id"]) == ["a1", "a3", "b1"]
    assert any("s1.csv" in aviso for aviso in avisos)


def test_attempts_too_close_in_the_same_session_warn():
    session = validate_readings(make_session("clean"))
    session.insert(0, "session_file", "s1.csv")
    attempts = pd.concat([_attempt(10, 12, "a1"), _attempt(30, 32, "a2")])
    _, warnings = assign_phases(session, attempts)
    assert "a2" in warnings[0]


def test_missing_dht11_readings_do_not_break_features():
    readings = _simple_session()
    readings["humidity_pct"] = np.nan
    phased, _ = assign_phases(readings, _attempt())
    features, _ = compute_features(phased)

    assert features["humidity_rise"].isna().all()
    assert features["mq3_humidity_peak_lag_s"].isna().all()
    assert features["mq3_rise"].notna().all()


def test_every_sensor_set_uses_mq3_and_the_full_set_uses_everything():
    for sensor_set in SENSOR_SETS:
        assert any(coluna.startswith("mq3_rise") for coluna in feature_columns(sensor_set))
    assert feature_columns("mq3+mq135+dht11") == all_feature_columns()
    assert "humidity_rise" not in feature_columns("mq3+mq135")
    with pytest.raises(ValueError):
        feature_columns("mq7")


def test_firmware_columns_derived_from_mq3_are_never_features():
    assert not {"ppm", "alcool", "amostra", "mq135_mv"} & set(all_feature_columns())


def test_temperature_is_not_a_feature():
    # A temperatura não distingue hálito de ambiente e, num carro, varia com o clima.
    assert not [c for c in all_feature_columns() if c.startswith("temperature")]


def test_target_is_only_alcohol_or_not():
    readings, attempts = make_dataset(n_participants=2, repetitions=1)
    phased, _ = assign_phases(readings, attempts)
    features, _ = compute_features(phased)
    dataset = build_dataset(features, attempts)

    assert set(dataset["target"]) == {"sem_efeito", "sob_efeito"}
    assert set(dataset.loc[dataset["condition"].isin(["clean", "perfume"]), "target"]) == {"sem_efeito"}
    assert set(dataset.loc[dataset["condition"] == "drink", "target"]) == {"sob_efeito"}
