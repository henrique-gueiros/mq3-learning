"""Leitura e gravação de CSVs de leituras."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_validation import DataValidationError, validate_readings

_TEXT_DTYPES = {"timestamp": "string", "session_id": "string", "source": "string", "notes": "string"}


def read_readings_csv(path: Path, expected_source: str | None = None) -> pd.DataFrame:
    """Lê e valida um CSV de leituras; os erros citam o nome do arquivo."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"arquivo não encontrado: {path}")
    try:
        df = pd.read_csv(path, dtype=_TEXT_DTYPES)
    except pd.errors.EmptyDataError as exc:
        raise DataValidationError([f"{path.name}: arquivo vazio"]) from exc
    try:
        return validate_readings(df, expected_source=expected_source)
    except DataValidationError as exc:
        raise DataValidationError([f"{path.name}: {p}" for p in exc.problems]) from exc


def load_raw_readings(raw_dir: Path) -> pd.DataFrame:
    """Carrega todos os CSVs de ``raw_dir`` como leituras reais.

    Os arquivos originais nunca são alterados. Cada linha ganha a coluna
    ``source_file`` para rastrear de qual arquivo veio.
    """
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(
            f"nenhum CSV em {raw_dir}. Coloque lá as leituras reais "
            "no formato de templates/leituras_template.csv"
        )

    frames: list[pd.DataFrame] = []
    problems: list[str] = []
    for file in files:
        try:
            df = read_readings_csv(file, expected_source="real")
        except DataValidationError as exc:
            problems.extend(exc.problems)
            continue
        df["source_file"] = file.name
        frames.append(df)
    if problems:
        raise DataValidationError(problems)

    combined = pd.concat(frames, ignore_index=True)
    duplicated = combined.duplicated(subset=["session_id", "timestamp"], keep=False)
    if duplicated.any():
        names = ", ".join(sorted(combined.loc[duplicated, "source_file"].unique()))
        raise DataValidationError(
            [f"{int(duplicated.sum())} leituras repetidas (mesma session_id e timestamp) entre: {names}"]
        )
    return combined.sort_values(["session_id", "timestamp"], kind="stable").reset_index(drop=True)


def write_readings_csv(df: pd.DataFrame, path: Path) -> None:
    """Grava leituras em CSV com timestamps ISO 8601 (UTC)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out["timestamp"] = out["timestamp"].map(lambda ts: ts.isoformat())
    out.to_csv(path, index=False)
