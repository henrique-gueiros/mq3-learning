"""Figuras da avaliação, gravadas em ``reports/figuras/`` (e no MLflow, se ativo).

- ``matriz_confusao``: acertos e erros no teste;
- ``curva_roc``: taxa de verdadeiros x falsos positivos de ``sob_efeito``;
- ``barras_por_modelo``: F1 macro da validação cruzada por modelo e conjunto de
  sensores, com o desvio entre folds como barra de erro (estabilidade);
- ``treino_vs_validacao``: F1 no treino de cada fold contra o F1 na validação
  (treino bem acima da validação sugere overfitting; os dois baixos, underfitting);
- ``curva_aprendizado``: F1 de treino e validação conforme o treino cresce.

Cada função devolve o caminho do PNG gravado. As figuras descrevem os dados
que receberam; com os dados de teste automatizado elas não são desempenho real.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.metrics import roc_auc_score, roc_curve  # noqa: E402
from sklearn.model_selection import GroupKFold, learning_curve  # noqa: E402

POSITIVO = "sob_efeito"


def matriz_confusao(labels: list[str], matrix: list[list[int]], destino: Path, titulo: str = "Matriz de confusão (teste)") -> Path:
    """Desenha a matriz de confusão com a contagem em cada célula."""
    valores = np.asarray(matrix)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    imagem = ax.imshow(valores, cmap="Blues")
    fig.colorbar(imagem, ax=ax)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Previsto")
    ax.set_ylabel("Real")
    ax.set_title(titulo)
    limite = valores.max() / 2 if valores.size else 0
    for i in range(valores.shape[0]):
        for j in range(valores.shape[1]):
            cor = "white" if valores[i, j] > limite else "black"
            ax.text(j, i, str(valores[i, j]), ha="center", va="center", color=cor)
    return _salvar(fig, destino)


def curva_roc(y_true: pd.Series, scores, destino: Path, titulo: str = "Curva ROC (teste)") -> Path | None:
    """Curva ROC com ``sob_efeito`` como positivo; ``None`` se faltar uma das classes."""
    y = (pd.Series(y_true).astype(str) == POSITIVO).to_numpy()
    scores = np.asarray(scores, dtype=float)
    if len(np.unique(y)) < 2:
        return None
    fpr, tpr, _ = roc_curve(y, scores)
    auc = roc_auc_score(y, scores)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.plot(fpr, tpr, label=f"modelo (AUC = {auc:.2f})")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="acaso")
    ax.set_xlabel("Falsos positivos (sem_efeito marcado como sob_efeito)")
    ax.set_ylabel("Verdadeiros positivos (recall sob_efeito)")
    ax.set_title(titulo)
    ax.legend(loc="lower right")
    return _salvar(fig, destino)


def barras_por_modelo(resultados: pd.DataFrame, destino: Path, metrica: str = "f1_macro") -> Path:
    """Barras da métrica por modelo e conjunto de sensores, com o desvio entre folds."""
    media = resultados.pivot(index="model", columns="sensor_set", values=metrica)
    desvio_col = f"{metrica}_std"
    desvio = (
        resultados.pivot(index="model", columns="sensor_set", values=desvio_col)
        if desvio_col in resultados.columns
        else None
    )
    fig, ax = plt.subplots(figsize=(8, 4.5))
    media.plot.bar(ax=ax, yerr=desvio, capsize=3, rot=0)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel(f"{metrica} (validação cruzada)")
    ax.set_xlabel("Modelo")
    ax.set_title(f"{metrica} por modelo e conjunto de sensores (barra = desvio entre folds)")
    ax.legend(title="Sensores", fontsize=8)
    return _salvar(fig, destino)


def treino_vs_validacao(folds: pd.DataFrame, destino: Path) -> Path:
    """F1 macro no treino e na validação de cada fold, por modelo e conjunto de sensores."""
    resumo = (
        folds.groupby(["sensor_set", "model"])[["f1_macro_treino", "f1_macro"]]
        .agg(["mean", "std"])
        .reset_index()
    )
    rotulos = [f"{m}\n{s}" for s, m in zip(resumo["sensor_set"], resumo["model"])]
    x = np.arange(len(resumo))
    fig, ax = plt.subplots(figsize=(max(8, len(resumo) * 0.6), 4.5))
    largura = 0.4
    ax.bar(x - largura / 2, resumo[("f1_macro_treino", "mean")], largura, yerr=resumo[("f1_macro_treino", "std")], capsize=2, label="treino do fold")
    ax.bar(x + largura / 2, resumo[("f1_macro", "mean")], largura, yerr=resumo[("f1_macro", "std")], capsize=2, label="validação do fold")
    ax.set_xticks(x, rotulos, fontsize=7, rotation=90)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("F1 macro")
    ax.set_title("Treino x validação por fold externo (diferença grande = overfitting)")
    ax.legend()
    return _salvar(fig, destino)


def curva_aprendizado(
    estimador,
    X: pd.DataFrame,
    y: pd.Series,
    grupos: pd.Series,
    destino: Path,
    n_splits: int = 5,
    titulo: str = "Curva de aprendizado",
) -> Path:
    """F1 macro de treino e validação (por grupo) para frações crescentes do treino.

    Fold em que a fração sorteada não tem as duas classes vira NaN e fica fora da média.
    """
    n_splits = min(n_splits, pd.Series(grupos).nunique())
    tamanhos, treino, validacao = learning_curve(
        clone(estimador),
        X,
        pd.Series(y).astype(str),
        groups=pd.Series(grupos).astype(str),
        cv=GroupKFold(n_splits=n_splits),
        train_sizes=np.linspace(0.2, 1.0, 5),
        scoring="f1_macro",
        error_score=np.nan,
    )
    fig, ax = plt.subplots(figsize=(6, 4))
    for nome, valores in (("treino", treino), ("validação", validacao)):
        media = np.nanmean(valores, axis=1)
        desvio = np.nanstd(valores, axis=1)
        ax.plot(tamanhos, media, marker="o", label=nome)
        ax.fill_between(tamanhos, media - desvio, media + desvio, alpha=0.2)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Tentativas no treino")
    ax.set_ylabel("F1 macro")
    ax.set_title(titulo)
    ax.legend()
    return _salvar(fig, destino)


def _salvar(fig, destino: Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(destino, dpi=120)
    plt.close(fig)
    return destino
