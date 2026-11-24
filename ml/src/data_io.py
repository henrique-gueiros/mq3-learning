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

_ATTEMPT_DTYPES = {
    "attempt_id": "string",
    "session_file": "string",
    "participant_id": "string",
    "condition": "string",
    "notes": "string",
}


def read_session_csv(path: Path) -> pd.DataFrame:
    """Lê e valida um CSV de sessão do firmware; acrescenta ``session_file``."""
    path = Path(path)
    df = _read_csv(path, {})
    try:
        df = validate_readings(df)
    except DataValidationError as exc:
        raise DataValidationError([f"{path.name}: {p}" for p in exc.problems]) from exc
    df.insert(0, "session_file", path.name)
    df["session_file"] = df["session_file"].astype("string")
    return df


def read_attempts_csv(path: Path) -> pd.DataFrame:
    """Lê e valida o CSV de tentativas."""
    df = _read_csv(path, _ATTEMPT_DTYPES)
    try:
        return validate_attempts(df)
    except DataValidationError as exc:
        raise DataValidationError([f"{Path(path).name}: {p}" for p in exc.problems]) from exc


def arquivos_de_sessao(sessions_dir: Path) -> list[Path]:
    """CSVs de sessão da pasta, em ordem. ``*.eventos.csv`` (botão da placa) não é sessão."""
    return sorted(p for p in Path(sessions_dir).glob("*.csv") if not p.name.endswith(".eventos.csv"))


def load_raw_data(sessions_dir: Path, attempts_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Carrega e valida todas as sessões e tentativas reais.

    Os arquivos originais nunca são alterados.

    Returns:
        ``(leituras de todas as sessões, tentativas, avisos)``.
    """
    sessions_dir = Path(sessions_dir)
    files = arquivos_de_sessao(sessions_dir)
    if not files:
        raise FileNotFoundError(
            f"nenhum CSV em {sessions_dir}. Copie para lá os CSVs de sessão gravados pelo firmware"
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
            frames.append(read_session_csv(file))
        except DataValidationError as exc:
            problems.extend(exc.problems)
    try:
        attempts = read_attempts_csv(attempts_path)
    except DataValidationError as exc:
        problems.extend(exc.problems)
    if problems:
        raise DataValidationError(problems)

    readings = pd.concat(frames, ignore_index=True)
    warnings = check_consistency(readings, attempts)
    return readings, attempts, warnings


def read_dataset_csv(path: Path) -> pd.DataFrame:
    """Lê uma tabela de features gerada pelo ``prepare`` (uma linha por tentativa)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} não existe; rode 'prepare' antes")
    return pd.read_csv(path, dtype=_ATTEMPT_DTYPES | {"target": "string"})


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _read_csv(path: Path, dtypes: dict[str, str]) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"arquivo não encontrado: {path}")
    try:
        return pd.read_csv(path, dtype=dtypes)
    except pd.errors.EmptyDataError as exc:
        raise DataValidationError([f"{path.name}: arquivo vazio"]) from exc
