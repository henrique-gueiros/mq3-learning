"""Leitura e gravação dos CSVs do projeto."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_validation import (
    DataValidationError,
    check_consistency,
    validate_attempts,
    validate_readings,
)

_READING_DTYPES = {"timestamp": "string", "attempt_id": "string", "phase": "string"}
_ATTEMPT_DTYPES = {
    "attempt_id": "string",
    "participant_id": "string",
    "session_id": "string",
    "condition": "string",
    "notes": "string",
}


def read_readings_csv(path: Path) -> pd.DataFrame:
    """Lê e valida um CSV de leituras; os erros citam o nome do arquivo."""
    df = _read_csv(path, _READING_DTYPES)
    try:
        return validate_readings(df)
    except DataValidationError as exc:
        raise DataValidationError([f"{Path(path).name}: {p}" for p in exc.problems]) from exc


def read_attempts_csv(path: Path) -> pd.DataFrame:
    """Lê e valida o CSV de tentativas."""
    df = _read_csv(path, _ATTEMPT_DTYPES)
    try:
        return validate_attempts(df)
    except DataValidationError as exc:
        raise DataValidationError([f"{Path(path).name}: {p}" for p in exc.problems]) from exc


def load_raw_data(readings_dir: Path, attempts_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Carrega e valida todas as leituras e tentativas reais.

    Os arquivos originais nunca são alterados. Cada leitura ganha a coluna
    ``source_file`` para rastrear de qual arquivo veio.

    Returns:
        ``(leituras, tentativas, avisos)``.
    """
    readings_dir = Path(readings_dir)
    files = sorted(readings_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(
            f"nenhum CSV em {readings_dir}. Coloque lá as leituras no formato de "
            "templates/readings_template.csv"
        )
    if not Path(attempts_path).exists():
        raise FileNotFoundError(
            f"{attempts_path} não existe. Cadastre as tentativas no formato de "
            "templates/attempts_template.csv"
        )

    frames: list[pd.DataFrame] = []
    problems: list[str] = []
    for file in files:
        try:
            df = read_readings_csv(file)
        except DataValidationError as exc:
            problems.extend(exc.problems)
            continue
        df["source_file"] = file.name
        frames.append(df)
    try:
        attempts = read_attempts_csv(attempts_path)
    except DataValidationError as exc:
        problems.extend(exc.problems)
    if problems:
        raise DataValidationError(problems)

    readings = pd.concat(frames, ignore_index=True)
    duplicated = readings.duplicated(subset=["attempt_id", "timestamp"], keep=False)
    if duplicated.any():
        names = ", ".join(sorted(readings.loc[duplicated, "source_file"].unique()))
        raise DataValidationError(
            [f"{int(duplicated.sum())} leituras repetidas (mesmo attempt_id e timestamp) entre: {names}"]
        )

    warnings = check_consistency(readings, attempts)
    readings = readings.sort_values(["attempt_id", "timestamp"], kind="stable").reset_index(drop=True)
    return readings, attempts, warnings


def read_dataset_csv(path: Path) -> pd.DataFrame:
    """Lê uma tabela de features gerada pelo ``prepare`` (uma linha por tentativa)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} não existe; rode 'prepare' antes")
    return pd.read_csv(path, dtype=_ATTEMPT_DTYPES | {"target": "string"})


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Grava um CSV, com timestamps em ISO 8601 quando houver a coluna."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if "timestamp" in out.columns:
        out["timestamp"] = out["timestamp"].map(lambda ts: ts.isoformat())
    out.to_csv(path, index=False)


def _read_csv(path: Path, dtypes: dict[str, str]) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"arquivo não encontrado: {path}")
    try:
        return pd.read_csv(path, dtype=dtypes)
    except pd.errors.EmptyDataError as exc:
        raise DataValidationError([f"{path.name}: arquivo vazio"]) from exc
