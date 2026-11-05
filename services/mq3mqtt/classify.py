"""Decide o que publicar quando um sopro termina.

O cálculo da classe, quando o arquivo do modelo existe, é o mesmo de
``ml/src/inference.py``. Sem esse arquivo o serviço não inventa uma classe:
devolve ``sem_modelo`` e as leituras continuam no banco.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def attempt_id_de(sessao: str, inicio_t_ms: int, attempt_id: str | None) -> str:
    """Identificador do sopro. Usa o que veio no evento, se a placa enviou um."""
    if attempt_id:
        return attempt_id
    stem = sessao[:-4] if sessao.lower().endswith(".csv") else sessao
    return f"{stem}@{inicio_t_ms / 1000:g}s"


def montar_resultado(
    sessao: str,
    inicio: dict[str, Any] | None,
    fim_t_ms: int,
    readings: list[dict[str, Any]],
    model_path: Path,
) -> dict[str, Any]:
    """Monta o corpo de ``mq3/<placa>/resultado`` para um ``sopro_fim``.

    ``inicio`` é a linha do ``sopro_inicio`` correspondente. ``readings`` são as
    linhas já gravadas dessa sessão, com as colunas do CSV.
    """
    if inicio is None:
        return _resultado(
            sessao,
            attempt_id=None,
            status="sem_inicio",
            detalhe="chegou sopro_fim sem um sopro_inicio anterior nesta sessão",
        )

    attempt_id = attempt_id_de(sessao, int(inicio["t_ms"]), inicio.get("attempt_id"))
    if not Path(model_path).is_file():
        return _resultado(
            sessao,
            attempt_id=attempt_id,
            status="sem_modelo",
            detalhe=(
                "as leituras deste sopro ficaram no banco; "
                f"ainda não existe modelo treinado em {model_path.name}"
            ),
        )
    if not readings:
        return _resultado(
            sessao,
            attempt_id=attempt_id,
            status="sem_janela",
            detalhe="não há leituras gravadas para esta sessão",
        )

    import pandas as pd

    from src.data_validation import validate_readings
    from src.inference import predict_attempts

    frame = pd.DataFrame(readings)
    validated = validate_readings(frame)
    validated.insert(0, "session_file", sessao)
    attempt = pd.DataFrame(
        {
            "attempt_id": [attempt_id],
            "session_file": [sessao],
            "blow_start_s": [int(inicio["t_ms"]) / 1000],
            "blow_end_s": [fim_t_ms / 1000],
        }
    )
    predictions, warnings = predict_attempts(validated, attempt, model_path)
    if predictions.empty:
        return _resultado(
            sessao,
            attempt_id=attempt_id,
            status="sem_janela",
            detalhe="; ".join(warnings) or "o recorte do sopro ficou sem leituras úteis",
        )

    row = predictions.iloc[0]
    prediction = str(row["prediction"])
    return _resultado(
        sessao,
        attempt_id=attempt_id,
        status="classificado",
        prediction=prediction,
        prob_sem_efeito=_prob(row, "prob_sem_efeito"),
        prob_sob_efeito=_prob(row, "prob_sob_efeito"),
        detalhe="; ".join(warnings),
    )


def _resultado(
    sessao: str,
    attempt_id: str | None,
    status: str,
    detalhe: str,
    prediction: str | None = None,
    prob_sem_efeito: float | None = None,
    prob_sob_efeito: float | None = None,
) -> dict[str, Any]:
    return {
        "sessao": sessao,
        "attempt_id": attempt_id,
        "status": status,
        "prediction": prediction,
        "prob_sem_efeito": prob_sem_efeito,
        "prob_sob_efeito": prob_sob_efeito,
        "detalhe": detalhe,
    }


def _prob(row, column: str) -> float | None:
    if column not in row.index:
        return None
    value = row[column]
    if value is None or value != value:  # NaN
        return None
    return float(value)
