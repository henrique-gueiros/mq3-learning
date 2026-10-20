"""Montagem dos conjuntos finais de treino e teste e extração de features."""

from __future__ import annotations

import pandas as pd

FEATURE_COLUMNS = ["sensor_raw"]


def build_train_test(
    real_train: pd.DataFrame,
    real_test: pd.DataFrame,
    synthetic: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Junta o treino real com o sintético (opcional) e mantém o teste só com dados reais.

    Linhas sem rótulo são removidas dos dois conjuntos, porque não servem para
    treinar nem para avaliar. A coluna ``source`` continua indicando a origem de
    cada linha.

    Returns:
        ``(treino, teste, avisos)``.
    """
    for name, df in (("treino real", real_train), ("teste", real_test)):
        if (df["source"] != "real").any():
            raise ValueError(f"o {name} deve ter somente leituras reais")

    warnings: list[str] = []
    parts = [real_train]
    if synthetic is not None:
        if (synthetic["source"] != "synthetic").any():
            raise ValueError("o arquivo sintético contém linhas com source diferente de 'synthetic'")
        collision = set(synthetic["session_id"]) & (set(real_train["session_id"]) | set(real_test["session_id"]))
        if collision:
            raise ValueError(f"session_id sintético igual a um real: {sorted(collision)[:5]}")
        if "notes" in synthetic.columns and synthetic["notes"].str.contains("origin=didactic", na=False).any():
            warnings.append(
                "os dados sintéticos usam parâmetros didáticos (inventados); "
                "prefira os estimados das leituras reais"
            )
        if len(synthetic) > len(real_train):
            warnings.append(
                f"o treino tem mais leituras sintéticas ({len(synthetic)}) que reais ({len(real_train)}); "
                "o modelo pode aprender mais o simulador que o sensor"
            )
        parts.append(synthetic)

    train = pd.concat(parts, ignore_index=True)
    dropped_train = int(train["label"].isna().sum())
    dropped_test = int(real_test["label"].isna().sum())
    if dropped_train or dropped_test:
        warnings.append(f"removidas linhas sem rótulo: {dropped_train} do treino, {dropped_test} do teste")

    train = train.dropna(subset=["label"]).reset_index(drop=True)
    test = real_test.dropna(subset=["label"]).reset_index(drop=True)
    return train, test, warnings


def to_xy(
    df: pd.DataFrame, feature_columns: list[str] | None = None
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Separa features (``X``), rótulo (``y``) e sessão (``groups``) para o scikit-learn.

    ``groups`` serve para validação cruzada por sessão (por exemplo ``GroupKFold``).
    """
    columns = feature_columns or FEATURE_COLUMNS
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"features ausentes: {missing}")

    labeled = df.dropna(subset=["label"])
    if labeled[columns].isna().any().any():
        raise ValueError(f"há valores vazios nas features {columns}")
    return labeled[columns], labeled["label"].astype(int), labeled["session_id"]
