"""Sopros de bebida a partir dos CSVs cujo nome (ou a origem no lote) tem "alcool".

Nesta coleta várias pessoas revezaram o sopro no mesmo arquivo. Cada três
amostras seguidas, na ordem de ``t_ms``, são um sopro. O trio fica de fora
quando algum PPM está vazio ou abaixo de 0,6.

O PPM só descarta o trio. A classe continua vindo do arquivo, que já é de
bebida: ``ppm`` não entra em feature, rótulo nem decisão. O CSV da sessão
não é reescrito; o resultado vai para ``attempts.csv``.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from src.data_io import arquivos_de_sessao
from src.paths import ProjectPaths

PPM_MINIMO = 0.6
AMOSTRAS_POR_SOPRO = 3
_COLUNAS = [
    "attempt_id",
    "session_file",
    "participant_id",
    "condition",
    "blow_start_s",
    "blow_end_s",
    "reference_mg_l",
    "notes",
]
_NOTA = "3 amostras seguidas; trio de fora se algum ppm < 0,6; pessoas revezando"


def e_arquivo_bebida(nome: str) -> bool:
    """Verdadeiro quando o nome do CSV traz "alcool", sem distinguir maiúsculas."""
    return "alcool" in Path(nome).name.lower()


def sopros_de_bebida(amostras: pd.DataFrame, session_file: str, participant_id: str) -> pd.DataFrame:
    """Monta uma linha de tentativa por trio de amostras com PPM em 0,6 ou mais.

    Amostras que não fecham um trio ficam de fora. ``blow_start_s`` é o
    ``t_ms`` da primeira amostra do trio, em segundos; ``blow_end_s`` é o da
    terceira.
    """
    linhas, _ = _linhas_de_sopro(amostras, session_file, participant_id)
    if not linhas:
        return pd.DataFrame(columns=_COLUNAS)
    return pd.DataFrame(linhas, columns=_COLUNAS)


def arquivos_bebida(sessions_dir: Path, lote: Path | None = None) -> list[Path]:
    """CSVs de bebida: o nome tem "alcool", ou o lote aponta uma origem com "alcool"."""
    sessions_dir = Path(sessions_dir)
    por_nome = {path.name: path for path in arquivos_de_sessao(sessions_dir)}
    escolhidos = {nome: path for nome, path in por_nome.items() if e_arquivo_bebida(nome)}
    for origem, sessao in _pares_de_lote(lote):
        if e_arquivo_bebida(origem) and sessao in por_nome:
            escolhidos[sessao] = por_nome[sessao]
    return [escolhidos[nome] for nome in sorted(escolhidos)]


def reorganizar_sopros_de_bebida(paths: ProjectPaths, lote: Path | None = None) -> list[str]:
    """Reescreve as tentativas de bebida em ``attempts.csv``.

    Sem arquivo de álcool, o CSV de tentativas não é aberto para escrita.
    Com arquivo de álcool, as tentativas ``drink`` de outros arquivos saem:
    nesta coleta, bebida é o arquivo com "alcool" no nome ou na origem do lote.
    Perfume, ar limpo e enxaguante permanecem.
    """
    if lote is None:
        lote = _lote_padrao(paths)
    arquivos = arquivos_bebida(paths.raw_sessions_dir, lote)
    if not arquivos:
        return []

    nomes = {path.name for path in arquivos}
    mantidas, participantes = _ler_tentativas(paths.raw_attempts, nomes)
    novas: list[dict[str, str]] = []
    avisos: list[str] = []
    for path in arquivos:
        participante = participantes.get(path.name, "equipe")
        try:
            amostras = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            avisos.append(f"{path.name}: CSV vazio, nenhum sopro de bebida")
            continue
        if "ppm" not in amostras.columns or "t_ms" not in amostras.columns:
            avisos.append(f"{path.name}: sem coluna ppm ou t_ms, nenhum sopro de bebida")
            continue
        linhas, descartados = _linhas_de_sopro(amostras, path.name, participante)
        novas.extend(linhas)
        avisos.append(
            f"{path.name}: {len(linhas)} sopros de 3 amostras; "
            f"{descartados} trios de fora (ppm abaixo de {PPM_MINIMO}, ppm vazio ou sem duração)"
        )

    removidas = sorted(participantes.keys() - nomes)
    for nome in removidas:
        avisos.append(
            f"{nome}: tentativa drink removida; bebida nesta coleta é o arquivo com alcool no nome"
        )

    _gravar_tentativas(paths.raw_attempts, mantidas + novas)
    return avisos


def _linhas_de_sopro(
    amostras: pd.DataFrame,
    session_file: str,
    participant_id: str,
) -> tuple[list[dict[str, str]], int]:
    if amostras.empty or "t_ms" not in amostras.columns or "ppm" not in amostras.columns:
        return [], 0
    quadro = amostras.sort_values("t_ms", kind="stable").reset_index(drop=True)
    ppm = pd.to_numeric(
        quadro["ppm"].astype("string").str.replace(",", ".", regex=False),
        errors="coerce",
    )
    t_ms = pd.to_numeric(quadro["t_ms"], errors="coerce")
    n_completo = (len(quadro) // AMOSTRAS_POR_SOPRO) * AMOSTRAS_POR_SOPRO
    linhas: list[dict[str, str]] = []
    descartados = 0
    stem = Path(session_file).stem
    for inicio in range(0, n_completo, AMOSTRAS_POR_SOPRO):
        fatia_ppm = ppm.iloc[inicio : inicio + AMOSTRAS_POR_SOPRO]
        fatia_t = t_ms.iloc[inicio : inicio + AMOSTRAS_POR_SOPRO]
        if not bool(fatia_ppm.notna().all() and (fatia_ppm >= PPM_MINIMO).all() and fatia_t.notna().all()):
            descartados += 1
            continue
        comeco = float(fatia_t.iloc[0]) / 1000
        fim = float(fatia_t.iloc[-1]) / 1000
        if fim <= comeco:
            descartados += 1
            continue
        linhas.append(
            {
                "attempt_id": f"{stem}_s{len(linhas) + 1}",
                "session_file": session_file,
                "participant_id": participant_id.strip() or "equipe",
                "condition": "sob_efeito",
                "blow_start_s": comeco,
                "blow_end_s": fim,
                "reference_mg_l": "",
                "notes": _NOTA,
            }
        )
    return linhas, descartados


def _segundos(valor: float) -> str:
    return f"{valor:.3f}".rstrip("0").rstrip(".")


def _como_texto(linha: dict[str, str]) -> dict[str, str]:
    texto = {coluna: "" if linha.get(coluna) is None else str(linha.get(coluna, "")) for coluna in _COLUNAS}
    for campo in ("blow_start_s", "blow_end_s"):
        valor = linha.get(campo)
        if isinstance(valor, float):
            texto[campo] = _segundos(valor)
    return texto


def _pares_de_lote(lote: Path | None) -> list[tuple[str, str]]:
    pares: list[tuple[str, str]] = []
    for path in _arquivos_de_lote(lote):
        with path.open(encoding="utf-8", newline="") as handle:
            for linha in csv.DictReader(handle):
                origem = (linha.get("origem") or "").strip()
                sessao = (linha.get("sessao") or "").strip()
                if not origem or not sessao:
                    continue
                if not sessao.lower().endswith(".csv"):
                    sessao += ".csv"
                pares.append((origem, sessao))
    return pares


def _arquivos_de_lote(lote: Path | None) -> list[Path]:
    if lote is None or not lote.exists():
        return []
    if lote.is_dir():
        return sorted(path for path in lote.glob("lote-*.csv") if path.is_file())
    return [lote]


def _lote_padrao(paths: ProjectPaths) -> Path | None:
    dados = paths.root.parent / "applications" / "dados"
    if dados.is_dir():
        return dados
    return None


def _ler_tentativas(path: Path, sessoes_bebida: set[str]) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Devolve as linhas que ficam e o participante de cada drink que sai."""
    if not path.exists() or path.stat().st_size == 0:
        return [], {}
    mantidas: list[dict[str, str]] = []
    participantes: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        leitor = csv.DictReader(handle)
        for linha in leitor:
            sessao = (linha.get("session_file") or "").strip()
            if sessao and not sessao.lower().endswith(".csv"):
                sessao += ".csv"
                linha["session_file"] = sessao
            condicao = (linha.get("condition") or "").strip().lower()
            if sessao in sessoes_bebida or condicao in {"drink", "sob_efeito"}:
                if sessao and sessao not in participantes:
                    participantes[sessao] = (linha.get("participant_id") or "").strip() or "equipe"
                continue
            mantidas.append({coluna: linha.get(coluna, "") or "" for coluna in _COLUNAS})
    return mantidas, participantes


def _gravar_tentativas(path: Path, linhas: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        escritor = csv.DictWriter(handle, fieldnames=_COLUNAS, lineterminator="\n")
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow(_como_texto(linha))
