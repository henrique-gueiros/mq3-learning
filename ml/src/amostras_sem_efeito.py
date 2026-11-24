"""Amostras dos arquivos que não são de bebida.

Nesta coleta o perfume no ar, o álcool na mão e a limpeza das mãos não são um
sopro só: são muitas leituras. A umidade só decide o recorte, dentro de um
arquivo que já não é de álcool.

Hipótese desta coleta, revista na análise exploratória: o ar limpo e o
perfume medidos ficam abaixo de 60%, e os trechos que parecem sopro (como nas
rodadas de bebida) ficam em 60% ou mais. A partir de 60%, três amostras
seguidas são um sopro. Abaixo disso, ou com a umidade vazia, cada amostra é
uma linha. A classe continua a do arquivo (ar limpo, perfume, enxaguante),
sempre ``sem_efeito``. A umidade não diz se a pessoa bebeu.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from src.paths import ProjectPaths
from src.data_io import arquivos_de_sessao
from src.sopros_bebida import arquivos_bebida

UMIDADE_MINIMA_SOPRO = 60.0
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
_NOTA_SOPRO = "3 amostras seguidas com umidade >= 60%; hipotese para marcar sopro em arquivo sem alcool"
_NOTA_AMOSTRA = "uma amostra; umidade abaixo de 60% ou vazia; arquivo sem alcool"


def tentativas_sem_efeito(
    amostras: pd.DataFrame,
    session_file: str,
    participant_id: str,
    condition: str,
    umidade_minima: float = UMIDADE_MINIMA_SOPRO,
) -> pd.DataFrame:
    """Recorta um arquivo sem álcool em sopros de 3 amostras e amostras avulsas.

    Um trecho contíguo com umidade igual ou acima do limiar é sopro: entra de
    três em três. O que sobra desse trecho, e tudo que está abaixo do limiar,
    vira uma linha por amostra. Nenhuma leitura com ``t_ms`` válido é deixada
    de fora.
    """
    linhas = _linhas(amostras, session_file, participant_id, condition, umidade_minima)
    if not linhas:
        return pd.DataFrame(columns=_COLUNAS)
    return pd.DataFrame(linhas, columns=_COLUNAS)


def reorganizar_amostras_sem_efeito(paths: ProjectPaths, lote: Path | None = None) -> list[str]:
    """Reescreve as tentativas dos arquivos que não são de bebida.

    Sem arquivo de álcool na pasta, não mexe em ``attempts.csv``. Assim os
    testes com sessão sintética continuam com o sopro que eles cadastraram.
    """
    if lote is None:
        lote = _lote_padrao(paths)
    bebidas = arquivos_bebida(paths.raw_sessions_dir, lote)
    if not bebidas:
        return []

    nomes_bebida = {path.name for path in bebidas}
    casos = _casos_do_lote(lote)
    sessoes = [path for path in arquivos_de_sessao(paths.raw_sessions_dir) if path.name not in nomes_bebida]
    participantes = _participantes(paths.raw_attempts)
    novas: list[dict] = []
    avisos: list[str] = []
    reescritas: set[str] = set()

    for path in sessoes:
        if "instavel" in path.name.lower():
            avisos.append(f"{path.name}: sensor instável no nome do arquivo; ficou de fora")
            reescritas.add(path.name)
            continue
        condicao = _condicao(path.name, casos.get(path.name))
        if condicao is None:
            avisos.append(f"{path.name}: sem caso anotado; ficou de fora")
            continue
        try:
            amostras = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            avisos.append(f"{path.name}: CSV vazio; ficou de fora")
            reescritas.add(path.name)
            continue
        if "t_ms" not in amostras.columns or "humidity_pct" not in amostras.columns:
            avisos.append(f"{path.name}: sem t_ms ou umidade; ficou de fora")
            continue
        linhas = _linhas(
            amostras,
            path.name,
            participantes.get(path.name, "equipe"),
            "sem_efeito",
            UMIDADE_MINIMA_SOPRO,
        )
        if "bebida" in path.name.lower():
            for linha in linhas:
                linha["notes"] += (
                    "; o nome do arquivo diz bebida, mas ele nao esta entre os de alcool, "
                    "entao a classe e sem_efeito"
                )
        novas.extend(linhas)
        reescritas.add(path.name)
        sopros = sum(1 for linha in linhas if "3 amostras" in linha["notes"])
        avisos.append(
            f"{path.name}: {sopros} sopros de 3 amostras com umidade >= {UMIDADE_MINIMA_SOPRO}; "
            f"{len(linhas) - sopros} amostras avulsas; classe sem_efeito"
        )

    mantidas = _manter(paths.raw_attempts, reescritas)
    _gravar(paths.raw_attempts, mantidas + novas)
    return avisos


def _linhas(
    amostras: pd.DataFrame,
    session_file: str,
    participant_id: str,
    condition: str,
    umidade_minima: float,
) -> list[dict]:
    if amostras.empty or "t_ms" not in amostras.columns or "humidity_pct" not in amostras.columns:
        return []
    quadro = amostras.sort_values("t_ms", kind="stable").reset_index(drop=True)
    t_ms = pd.to_numeric(quadro["t_ms"], errors="coerce")
    umidade = pd.to_numeric(
        quadro["humidity_pct"].astype("string").str.replace(",", ".", regex=False),
        errors="coerce",
    )
    stem = Path(session_file).stem
    pessoa = participant_id.strip() or "equipe"
    condition = "sem_efeito"
    linhas: list[dict] = []
    indice = 0
    n = len(quadro)
    while indice < n:
        if pd.isna(t_ms.iloc[indice]):
            indice += 1
            continue
        sopro = _e_sopro(umidade.iloc[indice], umidade_minima)
        fim = indice + 1
        while fim < n and pd.notna(t_ms.iloc[fim]) and _e_sopro(umidade.iloc[fim], umidade_minima) == sopro:
            fim += 1
        tempos = [float(t_ms.iloc[k]) for k in range(indice, fim)]
        if sopro:
            cursor = 0
            while cursor + AMOSTRAS_POR_SOPRO <= len(tempos):
                fatia = tempos[cursor : cursor + AMOSTRAS_POR_SOPRO]
                if fatia[-1] > fatia[0]:
                    linhas.append(_linha(stem, len(linhas) + 1, session_file, pessoa, condition, fatia[0], fatia[-1], _NOTA_SOPRO))
                else:
                    for instante in fatia:
                        linhas.append(_amostra(stem, len(linhas) + 1, session_file, pessoa, condition, instante))
                cursor += AMOSTRAS_POR_SOPRO
            for instante in tempos[cursor:]:
                linhas.append(_amostra(stem, len(linhas) + 1, session_file, pessoa, condition, instante))
        else:
            for instante in tempos:
                linhas.append(_amostra(stem, len(linhas) + 1, session_file, pessoa, condition, instante))
        indice = fim
    return linhas


def _e_sopro(umidade: float, minima: float) -> bool:
    return pd.notna(umidade) and float(umidade) >= minima


def _amostra(stem: str, numero: int, session_file: str, pessoa: str, condition: str, t_ms: float) -> dict:
    return _linha(stem, numero, session_file, pessoa, condition, t_ms, t_ms + 1, _NOTA_AMOSTRA)


def _linha(
    stem: str,
    numero: int,
    session_file: str,
    pessoa: str,
    condition: str,
    inicio_ms: float,
    fim_ms: float,
    nota: str,
) -> dict:
    return {
        "attempt_id": f"{stem}_s{numero}",
        "session_file": session_file,
        "participant_id": pessoa,
        "condition": condition,
        "blow_start_s": round(inicio_ms / 1000, 3),
        "blow_end_s": round(fim_ms / 1000, 3),
        "reference_mg_l": "",
        "notes": nota,
    }


def _condicao(nome: str, caso_lote: str | None) -> str | None:
    if caso_lote in {"clean", "perfume", "alcohol70_spray", "alcohol70_hands", "mouthwash"}:
        return caso_lote
    texto = nome.lower()
    if "perfume" in texto:
        return "perfume"
    if "listerine" in texto or "enxagu" in texto or "mouthwash" in texto:
        return "mouthwash"
    if "spray" in texto or "borrif" in texto:
        return "alcohol70_spray"
    if "maos" in texto or "mãos" in texto or "hands" in texto:
        return "alcohol70_hands"
    if "clean" in texto or "ambiente" in texto or "conversa" in texto:
        return "clean"
    if "bebida" in texto:
        return "clean"
    return None


def _casos_do_lote(lote: Path | None) -> dict[str, str]:
    casos: dict[str, str] = {}
    if lote is None or not lote.exists():
        return casos
    arquivos = sorted(lote.glob("lote-*.csv")) if lote.is_dir() else [lote]
    for path in arquivos:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for linha in csv.DictReader(handle):
                sessao = (linha.get("sessao") or "").strip()
                caso = (linha.get("caso") or "").strip().lower()
                if not sessao or not caso:
                    continue
                if not sessao.lower().endswith(".csv"):
                    sessao += ".csv"
                casos[sessao] = caso
    return casos


def _lote_padrao(paths: ProjectPaths) -> Path | None:
    dados = paths.root.parent / "applications" / "dados"
    if dados.is_dir():
        return dados
    return None


def deixar_so_duas_classes(path: Path) -> list[str]:
    """Deixa em ``attempts.csv`` só ``sem_efeito`` e ``sob_efeito``.

    Perfume, ar limpo, álcool na mão, enxaguante e ``drink`` viram a classe
    correspondente. Linha com caso desconhecido sai do arquivo.
    """
    from src.data_validation import CONDITIONS

    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        leitor = csv.DictReader(handle)
        campos = list(leitor.fieldnames or [])
        origem = list(leitor)
    if "condition" not in campos:
        return []
    mantidas = []
    removidas = 0
    for linha in origem:
        caso = (linha.get("condition") or "").strip().lower()
        classe = CONDITIONS.get(caso)
        if classe is None:
            removidas += 1
            continue
        linha["condition"] = classe
        mantidas.append(linha)
    with path.open("w", encoding="utf-8", newline="") as handle:
        escritor = csv.DictWriter(handle, fieldnames=campos, lineterminator="\n", extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(mantidas)
    if not removidas:
        return []
    return [f"{removidas} tentativas com caso desconhecido foram removidas; ficam só sem_efeito e sob_efeito"]


def _participantes(path: Path) -> dict[str, str]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    pessoas: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for linha in csv.DictReader(handle):
            sessao = (linha.get("session_file") or "").strip()
            if sessao and not sessao.lower().endswith(".csv"):
                sessao += ".csv"
            if sessao and sessao not in pessoas:
                pessoas[sessao] = (linha.get("participant_id") or "").strip() or "equipe"
    return pessoas


def _manter(path: Path, reescritas: set[str]) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    mantidas: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for linha in csv.DictReader(handle):
            sessao = (linha.get("session_file") or "").strip()
            if sessao and not sessao.lower().endswith(".csv"):
                sessao += ".csv"
            if sessao in reescritas:
                continue
            mantidas.append({coluna: linha.get(coluna, "") or "" for coluna in _COLUNAS})
    return mantidas


def _gravar(path: Path, linhas: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        escritor = csv.DictWriter(handle, fieldnames=_COLUNAS, lineterminator="\n")
        escritor.writeheader()
        for linha in linhas:
            texto = {coluna: "" if linha.get(coluna) is None else str(linha.get(coluna, "")) for coluna in _COLUNAS}
            for campo in ("blow_start_s", "blow_end_s"):
                valor = linha.get(campo)
                if isinstance(valor, float):
                    texto[campo] = f"{valor:.3f}".rstrip("0").rstrip(".")
            escritor.writerow(texto)
