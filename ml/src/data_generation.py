"""Gerador de leituras sintéticas.

Modelo do gerador (propositalmente simples):

    leitura = nível_da_sessão + ruído

- ``nível_da_sessão`` é sorteado uma vez por sessão, de uma normal com
  ``level_mean`` e ``level_std`` da classe. Isso imita a diferença de base
  entre uma sessão e outra.
- ``ruído`` é sorteado a cada leitura, de uma normal com média 0 e ``noise_std``.

O modelo não representa a dinâmica temporal do sensor (aquecimento, subida e
descida da resposta ao álcool). Ele deve ser revisto depois da análise
exploratória das leituras reais.

Os rótulos vêm do próprio cenário simulado: um modelo treinado só com esses
dados aprende a regra do simulador, não a resposta física do MQ-3.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class ClassParams:
    """Parâmetros de geração de uma classe (``label`` 0 ou 1)."""

    n_sessions: int
    samples_per_session: int
    level_mean: float
    level_std: float
    noise_std: float


@dataclass
class SyntheticParams:
    """Configuração completa do gerador, salva em JSON em ``config/``."""

    classes: dict[int, ClassParams]
    sample_interval_seconds: float = 1.0
    start_time: str = "2026-01-01T00:00:00+00:00"
    clip_min: float | None = None
    clip_max: float | None = None
    seed: int = 42
    origin: str = "didactic"
    notes: str = ""
    metadata: dict = field(default_factory=dict)

    def check(self) -> None:
        """Verifica se os parâmetros fazem sentido; levanta ``ValueError`` se não."""
        problems: list[str] = []
        if set(self.classes) != {0, 1}:
            problems.append(f"classes devem ser 0 e 1, encontrado {sorted(self.classes)}")
        for label, cp in self.classes.items():
            if cp.n_sessions < 1 or cp.samples_per_session < 1:
                problems.append(f"classe {label}: n_sessions e samples_per_session devem ser >= 1")
            if cp.level_std < 0 or cp.noise_std < 0:
                problems.append(f"classe {label}: level_std e noise_std não podem ser negativos")
        if self.sample_interval_seconds <= 0:
            problems.append("sample_interval_seconds deve ser > 0")
        if self.clip_min is not None and self.clip_max is not None and self.clip_min >= self.clip_max:
            problems.append("clip_min deve ser menor que clip_max")
        if pd.Timestamp(self.start_time).tzinfo is None:
            problems.append("start_time precisa de fuso horário (ex.: 2026-01-01T00:00:00+00:00)")
        if problems:
            raise ValueError("parâmetros sintéticos inválidos: " + "; ".join(problems))

    def to_dict(self) -> dict:
        data = asdict(self)
        data["classes"] = {str(label): asdict(cp) for label, cp in sorted(self.classes.items())}
        return data

    @classmethod
    def from_dict(cls, data: dict) -> SyntheticParams:
        try:
            classes = {int(label): ClassParams(**values) for label, values in data["classes"].items()}
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"parâmetros sintéticos inválidos: {exc}") from exc
        optional = {
            key: data[key]
            for key in (
                "sample_interval_seconds",
                "start_time",
                "clip_min",
                "clip_max",
                "seed",
                "origin",
                "notes",
                "metadata",
            )
            if key in data
        }
        params = cls(classes=classes, **optional)
        params.check()
        return params


def load_params(path: Path) -> SyntheticParams:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"arquivo de parâmetros não encontrado: {path}")
    return SyntheticParams.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_params(params: SyntheticParams, path: Path) -> None:
    params.check()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(params.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_synthetic(params: SyntheticParams, seed: int | None = None) -> pd.DataFrame:
    """Gera leituras sintéticas no mesmo esquema das reais.

    Args:
        params: configuração do gerador.
        seed: substitui ``params.seed``; a mesma seed sempre gera os mesmos dados.

    Returns:
        Tabela com ``timestamp``, ``session_id`` (``syn-0001``, ...), ``sensor_raw``,
        ``label``, ``source="synthetic"`` e ``notes`` indicando a origem dos parâmetros.
    """
    params.check()
    rng = np.random.default_rng(params.seed if seed is None else seed)
    interval = pd.Timedelta(seconds=params.sample_interval_seconds)

    session_labels = [label for label, cp in sorted(params.classes.items()) for _ in range(cp.n_sessions)]
    session_labels = [int(label) for label in rng.permutation(session_labels)]

    frames: list[pd.DataFrame] = []
    start = pd.Timestamp(params.start_time).tz_convert("UTC")
    for index, label in enumerate(session_labels, start=1):
        cp = params.classes[label]
        level = rng.normal(cp.level_mean, cp.level_std)
        values = level + rng.normal(0.0, cp.noise_std, size=cp.samples_per_session)
        if params.clip_min is not None or params.clip_max is not None:
            values = np.clip(values, params.clip_min, params.clip_max)
        timestamps = pd.date_range(start=start, periods=cp.samples_per_session, freq=interval)
        frames.append(
            pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "session_id": f"syn-{index:04d}",
                    "sensor_raw": values,
                    "label": label,
                }
            )
        )
        start = timestamps[-1] + pd.Timedelta(hours=1)

    df = pd.concat(frames, ignore_index=True)
    df["session_id"] = df["session_id"].astype("string")
    df["label"] = df["label"].astype("Int64")
    df["source"] = pd.Series("synthetic", index=df.index, dtype="string")
    df["notes"] = pd.Series(f"synthetic origin={params.origin}", index=df.index, dtype="string")
    return df
