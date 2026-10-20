"""Estimativa dos parâmetros do gerador a partir de leituras reais de treino.

Para cada classe, cada sessão vira um "trecho" (as leituras daquela sessão com
aquele rótulo). Em cada trecho calculamos:

- a mediana, que representa o nível da sessão;
- o desvio-padrão, que representa o ruído dentro da sessão;
- o número de leituras.

Depois resumimos os trechos: a média e o desvio-padrão dos níveis viram
``level_mean`` e ``level_std``; a mediana dos desvios vira ``noise_std``.

Use apenas sessões de treino. Estimar com sessões de teste faz o gerador
carregar informação do teste para o treino.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.data_generation import ClassParams, SyntheticParams


def estimate_params(
    train_df: pd.DataFrame,
    n_sessions_per_class: int | None = 20,
    seed: int = 42,
) -> tuple[SyntheticParams, list[str]]:
    """Estima ``SyntheticParams`` a partir das leituras reais de treino.

    Args:
        train_df: leituras reais validadas, somente das sessões de treino.
        n_sessions_per_class: quantas sessões sintéticas gerar por classe;
            ``None`` usa a mesma quantidade de sessões reais.
        seed: semente que ficará gravada nos parâmetros.

    Returns:
        ``(parâmetros, avisos)``. Os avisos apontam estimativas pouco confiáveis.
    """
    labeled = train_df.dropna(subset=["label"])
    if labeled.empty:
        raise ValueError("não há leituras rotuladas no treino para estimar os parâmetros")
    if (labeled["source"] != "real").any():
        raise ValueError("a estimativa deve usar somente leituras reais (source='real')")

    warnings: list[str] = []
    classes: dict[int, ClassParams] = {}
    sessions_per_class: dict[str, int] = {}
    for label in (0, 1):
        segment = labeled[labeled["label"] == label]
        if segment.empty:
            raise ValueError(f"não há leituras de treino com label={label}; impossível estimar essa classe")

        grouped = segment.groupby("session_id")["sensor_raw"]
        levels = grouped.median()
        noise = grouped.std(ddof=1).dropna()
        sizes = grouped.size()
        n_real = len(levels)
        sessions_per_class[str(label)] = n_real

        if n_real < 2:
            warnings.append(
                f"label={label}: só 1 sessão real; a variação entre sessões (level_std) foi fixada em 0"
            )
        if noise.empty:
            warnings.append(f"label={label}: sessões com 1 leitura só; o ruído (noise_std) foi fixado em 0")
        elif n_real < 5:
            warnings.append(f"label={label}: só {n_real} sessões reais; as estimativas são pouco confiáveis")

        classes[label] = ClassParams(
            n_sessions=n_sessions_per_class or n_real,
            samples_per_session=int(sizes.median()),
            level_mean=float(levels.mean()),
            level_std=float(levels.std(ddof=1)) if n_real >= 2 else 0.0,
            noise_std=float(noise.median()) if not noise.empty else 0.0,
        )

    intervals = (
        labeled.sort_values(["session_id", "timestamp"])
        .groupby("session_id")["timestamp"]
        .diff()
        .dt.total_seconds()
    )
    intervals = intervals[intervals > 0]
    if intervals.empty:
        warnings.append("não deu para medir o intervalo entre leituras; usando 1 segundo")
        interval = 1.0
    else:
        interval = float(intervals.median())

    params = SyntheticParams(
        classes=classes,
        sample_interval_seconds=interval,
        clip_min=float(labeled["sensor_raw"].min()),
        clip_max=float(labeled["sensor_raw"].max()),
        seed=seed,
        origin="estimated",
        notes=(
            "Parâmetros estimados das sessões reais de treino. O gerador não representa "
            "a dinâmica temporal do sensor; os valores ficam limitados à faixa observada."
        ),
        metadata={
            "estimated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "real_rows": int(len(labeled)),
            "real_sessions_per_class": sessions_per_class,
        },
    )
    return params, warnings
