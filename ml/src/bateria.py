"""Bateria de treino e teste com as duas classes na mesma quantidade.

Cada lado fica com a mesma quantidade de ``sob_efeito`` e de ``sem_efeito``.
Sem cota (``n_por_classe`` vazio), essa quantidade é o que o lado tem da classe
menor: entram todas as tentativas dela e o mesmo número da outra, espalhado
entre os arquivos. Com cota, os dois lados somam esse número e a fração
``test_size`` vai para o teste.

Uma tentativa é uma linha do dataset (o que o modelo vê), já sem janela
sobreposta. O arquivo de sessão fica inteiro de um lado só. A semente torna o
sorteio repetível. Com ``config/split.json``, os grupos antigos continuam no
mesmo lado.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.splitting import GROUP_COLUMNS, GroupSplit

CLASSES = ("sem_efeito", "sob_efeito")

# CSVs do firmware que não entram: sensor com defeito, ou sessão que não é sopro.
ARQUIVOS_EXCLUIDOS = frozenset(
    {
        "leituras_bebida1.csv",
        "leituras_bebida2.csv",
        "leituras_bebida3.csv",
        "leituras_20_sensor_Instavel.csv",
        "leituras_novos_acima_08.csv",
        "leituras_conversa1.csv",
        # Extrato curto gravado no lote; o sopro de álcool é o CSV completo.
        "2026-11-12_equipe_drink_1.csv",
        "2026-11-12_equipe_drink_2.csv",
        "2026-11-12_equipe_drink_3.csv",
        "2026-11-12_equipe_drink_4.csv",
    }
)

# Cópia renomeada na importação. Se o CSV do firmware também estiver na pasta, fica ele.
MESMA_GRAVACAO = {
    "2026-11-14_equipe_clean_1.csv": "leituras_1_ambiente.csv",
    "2026-11-14_equipe_clean_2.csv": "leituras_2_ambiente.csv",
    "2026-11-14_equipe_clean_3.csv": "leituras_3_ambiente.csv",
    "2026-11-14_equipe_clean_4.csv": "leituras_4_ambiente.csv",
    "2026-11-14_equipe_clean_5.csv": "leituras_28_ambiente.csv",
    "2026-11-12_equipe_clean_6.csv": "leituras_7_ambiente.csv",
    "2026-11-12_equipe_clean_7.csv": "leituras_9_ambiente.csv",
    "2026-11-12_equipe_perfume_1.csv": "leituras_25_perfume.csv",
}


def nome_arquivo(valor: str) -> str:
    """Nome do CSV, com sufixo, sem pasta."""
    nome = str(valor).strip().replace("\\", "/")
    base = Path(nome).name
    if base and not base.lower().endswith(".csv"):
        base += ".csv"
    return base


def arquivo_fica_de_fora(nome: str) -> bool:
    """Verdadeiro para sensor ruim, sessão fora da coleta e extrato curto de bebida."""
    base = nome_arquivo(nome)
    if base in ARQUIVOS_EXCLUIDOS:
        return True
    return "instavel" in base.lower()


def tirar_arquivos_fora(dataset: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Tira sessões excluídas e a cópia renomeada quando o original está junto.

    Returns:
        ``(tabela, avisos)``. Sem coluna ``session_file``, a tabela volta igual.
    """
    if dataset.empty or "session_file" not in dataset.columns:
        return dataset.reset_index(drop=True), []
    nomes = dataset["session_file"].map(nome_arquivo)
    presentes = set(nomes)
    fora = {nome for nome in presentes if arquivo_fica_de_fora(nome)}
    copias = {
        alias
        for alias, canonico in MESMA_GRAVACAO.items()
        if alias in presentes and nome_arquivo(canonico) in presentes
    }
    retirar = fora | copias
    if not retirar:
        return dataset.reset_index(drop=True), []
    avisos = []
    if fora:
        avisos.append("ficaram de fora da bateria: " + ", ".join(sorted(fora)))
    if copias:
        avisos.append(
            "cópia renomeada ficou de fora porque o CSV do firmware está na pasta: "
            + ", ".join(sorted(copias))
        )
    return dataset.loc[~nomes.isin(retirar)].reset_index(drop=True), avisos


def montar_bateria(
    dataset: pd.DataFrame,
    existing: GroupSplit | None,
    group_by: str = "participant_id",
    test_size: float = 0.25,
    seed: int = 42,
    n_por_classe: int | None = None,
) -> tuple[GroupSplit, pd.DataFrame, pd.DataFrame, list[str]]:
    """Monta treino e teste com as duas classes na mesma quantidade em cada lado.

    Sem ``n_por_classe``, cada lado usa o mínimo que as duas classes têm ali.
    Com ``n_por_classe``, a fração ``test_size`` vai para o teste e o resto
    para o treino. Um grupo (arquivo, ou participante quando há mais de um)
    não aparece nos dois lados.

    Returns:
        ``(separação, treino, teste, avisos)``.

    Raises:
        ValueError: a cota não cabe sem partir um grupo, ou um lado fica sem classe.
    """
    if group_by not in GROUP_COLUMNS:
        raise ValueError(f"group_by deve ser um de {list(GROUP_COLUMNS)}")
    quadro, avisos = tirar_arquivos_fora(dataset)
    if quadro.empty or "target" not in quadro.columns:
        raise ValueError("não dá para montar a bateria: nenhuma tentativa depois do descarte")

    if existing is not None:
        if (existing.group_by, existing.test_size, existing.seed) != (group_by, test_size, seed):
            avisos.append(
                f"usando group_by={existing.group_by}, test_size={existing.test_size} e "
                f"seed={existing.seed} do manifesto existente (apague config/split.json para refazer)"
            )
        group_by = existing.group_by
        test_size = existing.test_size
        seed = existing.seed
        if (
            n_por_classe is not None
            and existing.n_por_classe is not None
            and existing.n_por_classe != n_por_classe
        ):
            avisos.append(
                f"usando n_por_classe={existing.n_por_classe} do manifesto existente "
                "(apague config/split.json para refazer)"
            )
            n_por_classe = existing.n_por_classe
        elif n_por_classe is None and existing.n_por_classe is not None:
            avisos.append(
                "a cota fixa do manifesto saiu; cada lado usa as tentativas que cabem, "
                "com as duas classes na mesma quantidade"
            )
    elif group_by == "participant_id" and quadro["participant_id"].astype(str).nunique() < 2:
        avisos.append("um só participant_id; a bateria separa por arquivo de sessão")
        group_by = "session_file"

    if n_por_classe is None:
        if not 0 < test_size < 1:
            raise ValueError("test_size deve estar entre 0 e 1")
        n_treino = n_teste = None
    else:
        n_treino, n_teste = _cotas(n_por_classe, test_size)
        alvo = quadro["target"].astype(str)
        for classe in CLASSES:
            tenho = int((alvo == classe).sum())
            if tenho < n_por_classe:
                raise ValueError(
                    f"não dá para montar a bateria de {n_por_classe} tentativas por classe: "
                    f"{classe} só tem {tenho}"
                )

    grupos = _contagens(quadro, group_by)
    train_groups = list(existing.train_groups) if existing is not None else []
    test_groups = list(existing.test_groups) if existing is not None else []
    train_groups = [nome for nome in train_groups if not arquivo_fica_de_fora(nome)]
    test_groups = [nome for nome in test_groups if not arquivo_fica_de_fora(nome)]
    known = set(train_groups) | set(test_groups)
    novos = {nome: contagem for nome, contagem in grupos.items() if nome not in known}
    if n_por_classe is None:
        minimo_teste, minimo_treino = _minimos(grupos, test_groups, train_groups, 1, 1)
    else:
        minimo_teste, minimo_treino = _minimos(grupos, test_groups, train_groups, n_teste, n_treino)

    if novos and _falta(minimo_teste, minimo_treino):
        try:
            novo_teste, novo_treino = _repartir(
                novos, minimo_teste, minimo_treino, np.random.default_rng(seed), test_size
            )
        except ValueError as exc:
            if n_por_classe is None:
                raise ValueError(
                    "não dá para separar os arquivos com as duas classes nos dois lados "
                    f"sem partir um {group_by}: {exc}"
                ) from exc
            raise ValueError(
                f"não dá para montar a bateria de {n_por_classe} tentativas por classe "
                f"sem partir um {group_by} (treino {n_treino}, teste {n_teste} de cada): {exc}"
            ) from exc
        test_groups.extend(novo_teste)
        train_groups.extend(novo_treino)
    elif novos:
        train_groups.extend(sorted(novos))
        if len(novos) == 1:
            avisos.append(f"só 1 {group_by} novo ({next(iter(sorted(novos)))}); ele foi para o treino")
    elif _falta(minimo_teste, minimo_treino):
        if n_por_classe is None:
            raise ValueError(
                "não dá para equilibrar os dois lados com os grupos já gravados "
                "em config/split.json: um lado ficou sem uma das classes"
            )
        raise ValueError(
            f"não dá para montar a bateria de {n_por_classe} tentativas por classe "
            f"com os grupos já gravados em config/split.json "
            f"(treino {n_treino}, teste {n_teste} de cada)"
        )

    overlap = set(train_groups) & set(test_groups)
    if overlap:
        raise ValueError(f"grupos em treino e teste ao mesmo tempo: {sorted(overlap)}")

    rng_linhas = np.random.default_rng(seed)
    treino = _amostra_lado(quadro, group_by, train_groups, n_treino, rng_linhas)
    teste = _amostra_lado(quadro, group_by, test_groups, n_teste, rng_linhas)
    split = GroupSplit(
        group_by=group_by,
        train_groups=train_groups,
        test_groups=test_groups,
        test_size=test_size,
        seed=seed,
        n_por_classe=n_por_classe,
    )
    return split, treino, teste, avisos


def _cotas(n_por_classe: int, test_size: float) -> tuple[int, int]:
    if n_por_classe < 2:
        raise ValueError("n_por_classe tem de ser pelo menos 2")
    if not 0 < test_size < 1:
        raise ValueError("test_size deve estar entre 0 e 1")
    n_teste = int(round(n_por_classe * test_size))
    n_teste = min(max(1, n_teste), n_por_classe - 1)
    return n_por_classe - n_teste, n_teste


def _contagens(quadro: pd.DataFrame, coluna: str) -> dict[str, dict[str, int]]:
    grupos: dict[str, dict[str, int]] = {}
    for (grupo, classe), quantidade in quadro.groupby([coluna, "target"], sort=False).size().items():
        grupos.setdefault(str(grupo), {})[str(classe)] = int(quantidade)
    return grupos


def _minimos(
    grupos: dict[str, dict[str, int]],
    test_groups: list[str],
    train_groups: list[str],
    n_teste: int,
    n_treino: int,
) -> tuple[dict[str, int], dict[str, int]]:
    minimo_teste = {}
    minimo_treino = {}
    for classe in CLASSES:
        ja_teste = sum(grupos.get(nome, {}).get(classe, 0) for nome in test_groups)
        ja_treino = sum(grupos.get(nome, {}).get(classe, 0) for nome in train_groups)
        minimo_teste[classe] = max(0, n_teste - ja_teste)
        minimo_treino[classe] = max(0, n_treino - ja_treino)
    return minimo_teste, minimo_treino


def _falta(minimo_teste: dict[str, int], minimo_treino: dict[str, int]) -> bool:
    return any(minimo_teste[classe] > 0 or minimo_treino[classe] > 0 for classe in CLASSES)


def _repartir(
    grupos: dict[str, dict[str, int]],
    minimo_teste: dict[str, int],
    minimo_treino: dict[str, int],
    rng: np.random.Generator,
    fracao: float,
) -> tuple[list[str], list[str]]:
    """Escolhe o lado de cada grupo sem partir o grupo.

    Entre as divisões que enchem a cota, fica a que melhor reparte as duas
    classes entre os lados. Empate usa a semente. ``fracao`` é a parte da
    massa que se quer no teste.
    """
    nomes = sorted(grupos)
    n = len(nomes)
    if n > 20:
        raise ValueError(f"{n} grupos novos passam de 20; apague config/split.json e reduza a coleta")
    desejado = fracao
    candidatos = []
    for mask in range(1 << n):
        teste: list[str] = []
        treino: list[str] = []
        soma = {lado: {classe: 0 for classe in CLASSES} for lado in ("teste", "treino")}
        for indice, nome in enumerate(nomes):
            lado = "teste" if mask & (1 << indice) else "treino"
            (teste if lado == "teste" else treino).append(nome)
            for classe in CLASSES:
                soma[lado][classe] += grupos[nome].get(classe, 0)
        if not teste and any(minimo_teste[classe] > 0 for classe in CLASSES):
            continue
        if not treino and any(minimo_treino[classe] > 0 for classe in CLASSES):
            continue
        if any(soma["teste"][classe] < minimo_teste[classe] for classe in CLASSES):
            continue
        if any(soma["treino"][classe] < minimo_treino[classe] for classe in CLASSES):
            continue
        massa_teste = sum(soma["teste"].values())
        massa = massa_teste + sum(soma["treino"].values())
        frac = massa_teste / massa if massa else 0.0
        chave = (
            min(_arquivos_da_classe(teste, grupos), _arquivos_da_classe(treino, grupos)),
            min(len(teste), len(treino)),
            -round(abs(frac - desejado), 6),
        )
        candidatos.append((chave, teste, treino))
    if not candidatos:
        raise ValueError("nenhuma divisão de grupos enche a cota dos dois lados")
    melhor = max(item[0] for item in candidatos)
    finalistas = [item for item in candidatos if item[0] == melhor]
    escolhido = finalistas[int(rng.integers(len(finalistas)))]
    return list(escolhido[1]), list(escolhido[2])


def _arquivos_da_classe(nomes: list[str], grupos: dict[str, dict[str, int]]) -> int:
    """O menor número de grupos que uma classe tem nesse lado."""
    return min(
        sum(1 for nome in nomes if grupos[nome].get(classe, 0) > 0)
        for classe in CLASSES
    )


def _amostra_lado(
    quadro: pd.DataFrame,
    group_by: str,
    grupos: list[str],
    n: int | None,
    rng: np.random.Generator,
) -> pd.DataFrame:
    lado = quadro[quadro[group_by].astype(str).isin(grupos)]
    if n is None:
        contagens = []
        for classe in CLASSES:
            tenho = int((lado["target"].astype(str) == classe).sum())
            if tenho < 1:
                raise ValueError(
                    f"não dá para equilibrar o lado: {classe} não tem tentativa "
                    f"nos arquivos {sorted(grupos)[:8]}"
                )
            contagens.append(tenho)
        n = min(contagens)
    pedacos = []
    for classe in CLASSES:
        bloco = lado[lado["target"].astype(str) == classe]
        if len(bloco) < n:
            raise ValueError(
                f"não dá para montar a bateria: o lado ficou com {len(bloco)} tentativas "
                f"de {classe} e a cota é {n}"
            )
        pedacos.append(_sortear_espalhado(bloco, n, rng))
    saida = pd.concat(pedacos, ignore_index=True)
    return saida.sort_values("attempt_id", kind="mergesort").reset_index(drop=True)


def _sortear_espalhado(bloco: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Tira ``n`` linhas repartindo a cota entre os arquivos, o mais parelho possível."""
    bloco = bloco.sort_values("attempt_id", kind="mergesort").reset_index(drop=True)
    arquivos = sorted(bloco["session_file"].map(nome_arquivo).unique())
    ordem = [arquivos[int(i)] for i in rng.permutation(len(arquivos))]
    partes = {nome: bloco[bloco["session_file"].map(nome_arquivo) == nome] for nome in arquivos}
    capacidade = {nome: len(partes[nome]) for nome in arquivos}
    cota = {nome: 0 for nome in arquivos}
    falta = n
    ativos = [nome for nome in ordem if capacidade[nome] > 0]
    while falta > 0 and ativos:
        base = falta // len(ativos)
        resto = falta % len(ativos)
        progresso = 0
        if base == 0:
            for nome in ativos:
                if resto == 0:
                    break
                cota[nome] += 1
                falta -= 1
                resto -= 1
                progresso += 1
        else:
            for indice, nome in enumerate(ativos):
                quero = base + (1 if indice < resto else 0)
                pego = min(quero, capacidade[nome] - cota[nome])
                cota[nome] += pego
                falta -= pego
                progresso += pego
        if progresso == 0:
            break
        ativos = [nome for nome in ativos if capacidade[nome] > cota[nome]]
    if falta > 0:
        raise ValueError(f"não deu para espalhar {n} tentativas entre os arquivos do lado")
    escolhidos = []
    for nome in arquivos:
        k = cota[nome]
        if k <= 0:
            continue
        pedaco = partes[nome]
        if k == len(pedaco):
            escolhidos.append(pedaco)
            continue
        posicoes = np.sort(rng.choice(len(pedaco), size=k, replace=False))
        escolhidos.append(pedaco.iloc[posicoes])
    return pd.concat(escolhidos, ignore_index=True)
