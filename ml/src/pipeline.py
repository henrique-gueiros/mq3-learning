"""Ingestão, preparação e disponibilização do dataset de treino.

O Airflow (``ml/dags/dataset_para_treino.py``) e o comando ``python -m src.cli pipeline``
só chamam estas funções. A limpeza, as features e a separação treino/teste continuam
aqui e nos módulos que este arquivo usa.

A ingestão lê rodadas já gravadas no Postgres da coleta e materializa o que o
``prepare`` espera:

- um CSV de sessão por rodada encerrada, em ``data/raw/sessions/``;
- uma linha por sopro em ``data/raw/attempts.csv``.

Um CSV de sessão que já existe não é reescrito. Rodada de simulador fica de fora,
salvo pedido explícito. O rótulo continua sendo o ``caso`` anotado na coleta.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.data_io import load_raw_data, read_dataset_csv, write_csv
from src.data_validation import CONDITIONS, DataValidationError, validate_readings
from src.features import assign_phases, build_dataset, compute_features
from src.amostras_sem_efeito import deixar_so_duas_classes, reorganizar_amostras_sem_efeito
from src.paths import ProjectPaths
from src.sopros_bebida import reorganizar_sopros_de_bebida
from src.splitting import apply_split, load_split, save_split, update_split

_COLUNAS_FIRMWARE = [
    "amostra",
    "t_ms",
    "mq3_raw",
    "ppm",
    "mq135_raw",
    "mq135_mv",
    "temperature_c",
    "humidity_pct",
    "alcool",
]
_COLUNAS_ATTEMPTS = [
    "attempt_id",
    "session_file",
    "participant_id",
    "condition",
    "blow_start_s",
    "blow_end_s",
    "reference_mg_l",
    "notes",
]
_NOME_SESSAO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.csv$")


@dataclass(frozen=True)
class SoproColetado:
    """Um sopro marcado na coleta, em milissegundos da sessão."""

    inicio_ms: int
    fim_ms: int | None


@dataclass(frozen=True)
class RodadaColetada:
    """Uma rodada do banco, pronta para virar CSV de sessão e tentativas."""

    rodada_id: str
    caso: str | None
    participante: str | None
    arquivo_sessao: str | None
    origem: str | None
    encerrada: bool
    leituras: pd.DataFrame
    sopros: tuple[SoproColetado, ...]


@dataclass(frozen=True)
class ResultadoIngestao:
    """O que a ingestão gravou e o que deixou como estava."""

    sessoes_gravadas: tuple[str, ...]
    sessoes_preservadas: tuple[str, ...]
    tentativas_acrescentadas: tuple[str, ...]
    avisos: tuple[str, ...]

    def como_dict(self) -> dict:
        return {
            "sessoes_gravadas": list(self.sessoes_gravadas),
            "sessoes_preservadas": list(self.sessoes_preservadas),
            "tentativas_acrescentadas": list(self.tentativas_acrescentadas),
            "avisos": list(self.avisos),
        }


@dataclass(frozen=True)
class ResumoPreparacao:
    """Contagens do dataset separado em treino e teste."""

    n_features: int
    group_by: str
    n_grupos_treino: int
    n_treino: int
    treino_por_classe: dict[str, int]
    n_grupos_teste: int
    n_teste: int
    teste_por_classe: dict[str, int]
    avisos: tuple[str, ...]

    def como_dict(self) -> dict:
        return {
            "n_features": self.n_features,
            "group_by": self.group_by,
            "n_grupos_treino": self.n_grupos_treino,
            "n_treino": self.n_treino,
            "treino_por_classe": self.treino_por_classe,
            "n_grupos_teste": self.n_grupos_teste,
            "n_teste": self.n_teste,
            "teste_por_classe": self.teste_por_classe,
            "avisos": list(self.avisos),
        }


def agrupar_sopros(eventos: list[tuple[str, int]]) -> tuple[SoproColetado, ...]:
    """Casa cada ``sopro_inicio`` com o ``sopro_fim`` seguinte.

    Um fim sem início aberto é ignorado. Um início sem fim fica com ``fim_ms``
    vazio: o ``prepare`` usa a duração padrão de 5 s.
    """
    sopros: list[SoproColetado] = []
    aberto: int | None = None
    for tipo, t_ms in sorted(eventos, key=lambda evento: (evento[1], evento[0] != "sopro_inicio")):
        if tipo == "sopro_inicio":
            if aberto is not None:
                sopros.append(SoproColetado(aberto, None))
            aberto = int(t_ms)
        elif tipo == "sopro_fim" and aberto is not None and int(t_ms) > aberto:
            sopros.append(SoproColetado(aberto, int(t_ms)))
            aberto = None
    if aberto is not None:
        sopros.append(SoproColetado(aberto, None))
    return tuple(sopros)


def ingerir(
    rodadas: list[RodadaColetada],
    paths: ProjectPaths,
    incluir_simulador: bool = False,
) -> ResultadoIngestao:
    """Grava sessões novas e acrescenta tentativas, sem editar CSV de sessão existente.

    Rodada aberta não entra: o arquivo seria um recorte incompleto e, uma vez
    gravado, não poderia ser atualizado.
    """
    ids_existentes, sessoes_anotadas, colunas = _ler_attempts(paths.raw_attempts)
    gravadas: list[str] = []
    preservadas: list[str] = []
    acrescentadas: list[str] = []
    avisos: list[str] = []
    linhas_novas: list[dict[str, str]] = []

    for rodada in sorted(rodadas, key=lambda item: item.rodada_id):
        nome, motivo = _avaliar_rodada(rodada, incluir_simulador)
        if motivo:
            avisos.append(motivo)
            continue
        assert nome is not None
        destino = paths.raw_sessions_dir / nome
        if destino.exists():
            preservadas.append(nome)
            if nome in sessoes_anotadas:
                avisos.append(f"sessão já anotada, CSV preservado: {nome}")
                continue
        else:
            quadro, erro = _quadro_da_sessao(rodada.leituras)
            if erro:
                avisos.append(f"sessão inválida ({nome}): {erro}")
                continue

        novas = _linhas_de_tentativa(rodada, nome, ids_existentes)
        if not novas:
            avisos.append(f"nenhum sopro novo para {nome}")
            continue
        if not destino.exists():
            paths.raw_sessions_dir.mkdir(parents=True, exist_ok=True)
            write_csv(quadro, destino)
            gravadas.append(nome)
        for linha in novas:
            ids_existentes.add(linha["attempt_id"])
            linhas_novas.append(linha)
            acrescentadas.append(linha["attempt_id"])
        sessoes_anotadas.add(nome)

    if linhas_novas:
        _anexar_attempts(paths.raw_attempts, linhas_novas, colunas)
    return ResultadoIngestao(tuple(gravadas), tuple(preservadas), tuple(acrescentadas), tuple(avisos))


def ler_rodadas(dsn: str, incluir_simulador: bool = False) -> list[RodadaColetada]:
    """Lê rodadas, leituras e eventos no Postgres da coleta.

    Não grava nada. ``incluir_simulador`` precisa ser verdadeiro para trazer
    rodadas com ``origem = 'simulador'``.
    """
    import psycopg
    from psycopg.rows import dict_row

    consulta_rodadas = """
        SELECT id::text AS rodada_id, caso, participante, arquivo_sessao, origem,
               fim IS NOT NULL AS encerrada
        FROM rodadas
        WHERE %(incluir_simulador)s OR origem IS DISTINCT FROM 'simulador'
        ORDER BY id
    """
    consulta_leituras = """
        SELECT rodada_id::text AS rodada_id, amostra, t_ms, mq3_raw, ppm, mq135_raw,
               mq135_mv, temperature_c, humidity_pct, alcool
        FROM leituras
        WHERE rodada_id::text = ANY(%(ids)s)
        ORDER BY rodada_id, amostra
    """
    consulta_eventos = """
        SELECT rodada_id::text AS rodada_id, tipo, t_ms
        FROM eventos
        WHERE rodada_id::text = ANY(%(ids)s)
          AND tipo IN ('sopro_inicio', 'sopro_fim')
        ORDER BY rodada_id, t_ms
    """
    with psycopg.connect(dsn, row_factory=dict_row) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(consulta_rodadas, {"incluir_simulador": incluir_simulador})
            cabecalhos = list(cursor.fetchall())
            if not cabecalhos:
                return []
            ids = [linha["rodada_id"] for linha in cabecalhos]
            cursor.execute(consulta_leituras, {"ids": ids})
            leituras = list(cursor.fetchall())
            cursor.execute(consulta_eventos, {"ids": ids})
            eventos = list(cursor.fetchall())
    return _montar_rodadas(cabecalhos, leituras, eventos)


def ingerir_do_banco(
    dsn: str,
    paths: ProjectPaths,
    incluir_simulador: bool = False,
) -> ResultadoIngestao:
    """Lê o Postgres da coleta e grava só o que ainda não está em ``data/raw``."""
    return ingerir(ler_rodadas(dsn, incluir_simulador), paths, incluir_simulador=incluir_simulador)


def preparar_dataset(
    paths: ProjectPaths,
    group_by: str = "participant_id",
    test_size: float = 0.25,
    seed: int = 42,
) -> ResumoPreparacao:
    """Calcula as features de cada sopro e separa treino e teste por grupo.

    É o mesmo passo de ``python -m src.cli prepare``. Antes das features,
    reescreve os sopros dos arquivos de bebida (nome ou origem com "alcool"):
    três amostras seguidas, e o trio sai se algum PPM fica abaixo de 0,6.
    Nos outros arquivos, umidade de 60% ou mais vira sopro de três amostras;
    abaixo disso, cada amostra vira uma linha. Perfume, ar limpo e enxaguante
    entram como ``sem_efeito``. A coluna ``condition`` fica só com as duas classes.
    """
    avisos_bebida = reorganizar_sopros_de_bebida(paths)
    avisos_sem_efeito = reorganizar_amostras_sem_efeito(paths)
    avisos_classes = deixar_so_duas_classes(paths.raw_attempts)
    readings, attempts, warnings = load_raw_data(paths.raw_sessions_dir, paths.raw_attempts)
    phased, phase_warnings = assign_phases(readings, attempts)
    features, feature_warnings = compute_features(phased)
    dataset = build_dataset(features, attempts)
    if dataset.empty:
        raise ValueError("nenhuma tentativa com features válidas")
    write_csv(dataset, paths.features_all)

    split, split_warnings = update_split(dataset, load_split(paths.split_manifest), group_by, test_size, seed)
    save_split(split, paths.split_manifest)
    train, test = apply_split(dataset, split)
    write_csv(train, paths.train)
    write_csv(test, paths.test)
    return ResumoPreparacao(
        n_features=len(dataset),
        group_by=split.group_by,
        n_grupos_treino=int(train[split.group_by].nunique()) if not train.empty else 0,
        n_treino=len(train),
        treino_por_classe=_contagem(train),
        n_grupos_teste=int(test[split.group_by].nunique()) if not test.empty else 0,
        n_teste=len(test),
        teste_por_classe=_contagem(test),
        avisos=tuple(
            avisos_bebida + avisos_sem_efeito + avisos_classes + warnings + phase_warnings + feature_warnings + split_warnings
        ),
    )


def gravar_disponivel(
    paths: ProjectPaths,
    ingestao: ResultadoIngestao | dict | None = None,
    preparacao: ResumoPreparacao | dict | None = None,
) -> dict:
    """Confere os CSVs de treino e grava ``data/processed/disponivel.json``.

    O treino (hoje o comando ``train``, depois o MLflow) lê esse manifesto para
    saber que a preparação terminou.
    """
    features = read_dataset_csv(paths.features_all)
    train = read_dataset_csv(paths.train)
    test = read_dataset_csv(paths.test)
    if features.empty:
        raise ValueError("nenhuma tentativa em features_all.csv; o dataset não foi disponibilizado")

    avisos = list(_pegar(ingestao, "avisos", ())) + list(_pegar(preparacao, "avisos", ()))
    manifesto = {
        "pronto_para_treino": True,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "features": _relativo(paths, paths.features_all),
        "treino": _relativo(paths, paths.train),
        "teste": _relativo(paths, paths.test),
        "n_features": len(features),
        "n_treino": len(train),
        "n_teste": len(test),
        "sessoes_gravadas": list(_pegar(ingestao, "sessoes_gravadas", ())),
        "sessoes_preservadas": list(_pegar(ingestao, "sessoes_preservadas", ())),
        "tentativas_acrescentadas": list(_pegar(ingestao, "tentativas_acrescentadas", ())),
        "avisos": avisos,
    }
    paths.disponivel.parent.mkdir(parents=True, exist_ok=True)
    paths.disponivel.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifesto


def executar_pipeline(
    paths: ProjectPaths,
    rodadas: list[RodadaColetada] | None = None,
    group_by: str = "participant_id",
    test_size: float = 0.25,
    seed: int = 42,
    incluir_simulador: bool = False,
    dsn: str | None = None,
) -> dict:
    """Roda ingestão, preparação e disponibilização, nesta ordem.

    ``rodadas`` existe para os testes e para quem já leu o banco. Com ``dsn``,
    as rodadas do Postgres entram junto.
    """
    lote = list(rodadas or [])
    if dsn:
        lote.extend(ler_rodadas(dsn, incluir_simulador))
    ingestao = ingerir(lote, paths, incluir_simulador=incluir_simulador)
    preparacao = preparar_dataset(paths, group_by, test_size, seed)
    return gravar_disponivel(paths, ingestao, preparacao)


def treinar_modelos(
    paths: ProjectPaths,
    select_by: str = "f1_macro",
    seed: int = 42,
    n_estimators: int = 100,
) -> dict:
    """Compara os modelos no treino e devolve a escolha, sem olhar o teste.

    A validação cruzada fica em ``reports/experiment.csv``. O teste continua
    intacto para ``avaliar_teste``.
    """
    from src import figuras, rastreio
    from src.features import SENSOR_SET_EXECUCAO, feature_columns
    from src.splitting import load_split
    from src.train import fixar_producao, model_specs, modelo_de_producao, run_experiment, spec_final

    split = load_split(paths.split_manifest)
    if split is None:
        raise FileNotFoundError(f"{paths.split_manifest} não existe; rode a preparação antes")
    train = read_dataset_csv(paths.train)
    specs = model_specs(seed, n_estimators=n_estimators)
    results, folds = run_experiment(
        train,
        group_by=split.group_by,
        sensor_sets=[SENSOR_SET_EXECUCAO],
        seed=seed,
        models=specs,
        return_folds=True,
    )
    report = paths.reports_dir / "experiment.csv"
    write_csv(results, report)
    write_csv(folds, paths.reports_dir / "folds.csv")
    final = modelo_de_producao(results, select_by)
    # A curva é a floresta que será servida: os folds ainda podem ter escolhido
    # um peso, e esse peso não entra no arquivo gravado.
    curva = _com_parametros_escolhidos(
        spec_final(str(final["model"]), seed, n_estimators).pipeline, final["chosen_params"]
    )
    curva.set_params(clf__class_weight=None)

    graficos = [
        figuras.barras_por_modelo(results, paths.figuras_dir / "f1_por_modelo.png"),
        figuras.treino_vs_validacao(folds, paths.figuras_dir / "treino_vs_validacao.png"),
        figuras.curva_aprendizado(
            curva,
            train[feature_columns(str(final["sensor_set"]))],
            train["target"],
            train[split.group_by],
            paths.figuras_dir / "curva_aprendizado.png",
            titulo=(
                f"Curva de aprendizado: floresta sem peso com {final['sensor_set']}\n"
                "(profundidade e folha mais escolhidas nos folds; peso fixo em nenhum)"
            ),
        ),
    ]
    rastreio.registrar_experimento(results, folds=folds, figuras=graficos)
    comparacao = []
    for row in results.sort_values(select_by, ascending=False).to_dict(orient="records"):
        comparacao.append(
            {
                "sensor_set": row["sensor_set"],
                "model": row["model"],
                select_by: float(row[select_by]),
                "recall_sob_efeito": float(row["recall_sob_efeito"]),
            }
        )
    return fixar_producao(
        {
            "group_by": split.group_by,
            "select_by": select_by,
            "modelo": str(final["model"]),
            "sensor_set": str(final["sensor_set"]),
            "cv_score": float(final[select_by]),
            "n_treino": int(final["n_attempts"]),
            "relatorio": _relativo(paths, report),
            "comparacao": comparacao,
        }
    )


def avaliar_teste(paths: ProjectPaths, escolha: dict, seed: int = 42) -> dict:
    """Treina a floresta sem peso, com o limiar do treino, e avalia uma vez no teste.

    Grava ``models/sob_efeito.joblib`` e ``reports/final.json``. A comparação
    por F1 fica em ``experiment.csv``; o arquivo servido não segue esse F1.
    """
    from src import figuras, rastreio
    from src.features import feature_columns
    from src.splitting import load_split
    from src.train import fixar_producao, save_model, scores_sob_efeito, train_final_model

    escolha = fixar_producao(escolha)
    split = load_split(paths.split_manifest)
    if split is None:
        raise FileNotFoundError(f"{paths.split_manifest} não existe; rode a preparação antes")
    train = read_dataset_csv(paths.train)
    test = read_dataset_csv(paths.test)
    model, metadata = train_final_model(
        train,
        test,
        escolha["sensor_set"],
        escolha["modelo"],
        group_by=split.group_by,
        seed=seed,
    )
    metadata["selected_by"] = escolha["select_by"]
    metadata["criterio_final"] = escolha["criterio_final"]
    metadata["cv_score"] = float(escolha["cv_score"])
    model_path = paths.models_dir / "sob_efeito.joblib"
    save_model(model, metadata, model_path)
    final_report = paths.reports_dir / "final.json"
    final_report.parent.mkdir(parents=True, exist_ok=True)
    final_report.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    graficos = []
    if "confusion_matrix" in metadata:
        graficos.append(
            figuras.matriz_confusao(
                metadata["confusion_matrix"]["labels"],
                metadata["confusion_matrix"]["matrix"],
                paths.figuras_dir / "matriz_confusao.png",
            )
        )
        scores = scores_sob_efeito(model, test[feature_columns(escolha["sensor_set"])])
        if scores is not None:
            roc = figuras.curva_roc(test["target"], scores, paths.figuras_dir / "roc.png")
            if roc is not None:
                graficos.append(roc)
    rastreio.registrar_final(metadata, model, graficos)
    return {
        "modelo": escolha["modelo"],
        "sensor_set": escolha["sensor_set"],
        "cv_score": float(escolha["cv_score"]),
        "n_treino": int(metadata["n_train_attempts"]),
        "n_teste": int(metadata.get("n_test_attempts", 0)),
        "metricas_teste": metadata.get("test_metrics", {}),
        "matriz_confusao": metadata.get("confusion_matrix"),
        "modelo_arquivo": _relativo(paths, model_path),
        "relatorio": _relativo(paths, final_report),
    }


def _com_parametros_escolhidos(pipeline, chosen_params: str):
    """Clona o pipeline com os hiperparâmetros que mais vezes venceram nos folds externos."""
    from collections import Counter

    from sklearn.base import clone

    escolhas = [json.dumps(p, sort_keys=True) for p in json.loads(chosen_params) if p]
    modelo = clone(pipeline)
    if escolhas:
        modelo.set_params(**json.loads(Counter(escolhas).most_common(1)[0][0]))
    return modelo


def _avaliar_rodada(rodada: RodadaColetada, incluir_simulador: bool) -> tuple[str | None, str | None]:
    """Devolve ``(nome do arquivo, None)`` ou ``(None, aviso)``."""
    if rodada.origem == "simulador" and not incluir_simulador:
        return None, f"rodada de simulador ignorada: {rodada.rodada_id}"
    if not rodada.encerrada:
        return None, f"rodada aberta, ainda não exportada: {rodada.rodada_id}"
    caso = (rodada.caso or "").strip().lower()
    if caso not in CONDITIONS:
        return None, f"caso desconhecido {rodada.caso!r} na rodada {rodada.rodada_id}"
    if not (rodada.participante or "").strip():
        return None, f"participante vazio na rodada {rodada.rodada_id}"
    nome = _nome_sessao(rodada.arquivo_sessao, rodada.rodada_id)
    if nome is None:
        return None, f"nome de arquivo inválido na rodada {rodada.rodada_id}: {rodada.arquivo_sessao!r}"
    if not rodada.sopros:
        return None, f"rodada encerrada sem sopro: {rodada.rodada_id}"
    return nome, None


def _nome_sessao(bruto: str | None, rodada_id: str) -> str | None:
    texto = (bruto or "").strip()
    if not texto:
        texto = f"rodada_{rodada_id}.csv"
    if texto.lower().endswith(".csv"):
        texto = texto[:-4] + ".csv"
    else:
        texto += ".csv"
    if _NOME_SESSAO.fullmatch(texto):
        return texto
    return None


def _quadro_da_sessao(leituras: pd.DataFrame) -> tuple[pd.DataFrame | None, str | None]:
    if leituras is None or leituras.empty:
        return None, "nenhuma leitura"
    try:
        validadas = validate_readings(leituras)
    except DataValidationError as exc:
        return None, exc.problems[0]
    colunas = [coluna for coluna in _COLUNAS_FIRMWARE if coluna in validadas.columns]
    return validadas[colunas].copy(), None


def _linhas_de_tentativa(
    rodada: RodadaColetada,
    nome: str,
    ids_existentes: set[str],
) -> list[dict[str, str]]:
    linhas = []
    for indice, sopro in enumerate(sorted(rodada.sopros, key=lambda item: item.inicio_ms), start=1):
        attempt_id = f"{Path(nome).stem}_s{indice}"
        if attempt_id in ids_existentes:
            continue
        linhas.append(
            {
                "attempt_id": attempt_id,
                "session_file": nome,
                "participant_id": (rodada.participante or "").strip(),
                "condition": (rodada.caso or "").strip().lower(),
                "blow_start_s": str(sopro.inicio_ms / 1000),
                "blow_end_s": "" if sopro.fim_ms is None else str(sopro.fim_ms / 1000),
                "reference_mg_l": "",
                "notes": f"exportado da rodada {rodada.rodada_id}",
            }
        )
    return linhas


def _ler_attempts(path: Path) -> tuple[set[str], set[str], list[str]]:
    if not path.exists() or path.stat().st_size == 0:
        return set(), set(), list(_COLUNAS_ATTEMPTS)
    with path.open(encoding="utf-8", newline="") as handle:
        leitor = csv.DictReader(handle)
        colunas = list(leitor.fieldnames or _COLUNAS_ATTEMPTS)
        ids: set[str] = set()
        sessoes: set[str] = set()
        for linha in leitor:
            attempt_id = (linha.get("attempt_id") or "").strip()
            sessao = (linha.get("session_file") or "").strip()
            if attempt_id:
                ids.add(attempt_id)
            if sessao:
                if not sessao.lower().endswith(".csv"):
                    sessao += ".csv"
                sessoes.add(sessao)
    return ids, sessoes, colunas


def _anexar_attempts(path: Path, linhas: list[dict[str, str]], colunas: list[str]) -> None:
    novo = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if not novo and not path.read_bytes().endswith(b"\n"):
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n")
    with path.open("a", encoding="utf-8", newline="") as handle:
        escritor = csv.DictWriter(handle, fieldnames=colunas, lineterminator="\n", extrasaction="ignore")
        if novo:
            escritor.writeheader()
        for linha in linhas:
            escritor.writerow({coluna: linha.get(coluna, "") for coluna in colunas})


def _montar_rodadas(cabecalhos: list[dict], leituras: list[dict], eventos: list[dict]) -> list[RodadaColetada]:
    por_leitura: dict[str, list[dict]] = {}
    for linha in leituras:
        por_leitura.setdefault(linha["rodada_id"], []).append(linha)
    por_evento: dict[str, list[tuple[str, int]]] = {}
    for evento in eventos:
        por_evento.setdefault(evento["rodada_id"], []).append((evento["tipo"], int(evento["t_ms"])))
    rodadas = []
    for cabecalho in cabecalhos:
        rodada_id = cabecalho["rodada_id"]
        quadro = pd.DataFrame(por_leitura.get(rodada_id, []))
        if not quadro.empty:
            quadro = quadro.drop(columns=["rodada_id"])
        rodadas.append(
            RodadaColetada(
                rodada_id=rodada_id,
                caso=cabecalho.get("caso"),
                participante=cabecalho.get("participante"),
                arquivo_sessao=cabecalho.get("arquivo_sessao"),
                origem=cabecalho.get("origem"),
                encerrada=bool(cabecalho.get("encerrada")),
                leituras=quadro,
                sopros=agrupar_sopros(por_evento.get(rodada_id, [])),
            )
        )
    return rodadas


def _contagem(parte: pd.DataFrame) -> dict[str, int]:
    if parte.empty or "target" not in parte.columns:
        return {}
    return {str(classe): int(quantidade) for classe, quantidade in parte["target"].value_counts().sort_index().items()}


def _pegar(origem: ResultadoIngestao | ResumoPreparacao | dict | None, campo: str, vazio):
    if origem is None:
        return vazio
    if isinstance(origem, dict):
        return origem.get(campo, vazio)
    return getattr(origem, campo, vazio)


def _relativo(paths: ProjectPaths, path: Path) -> str:
    return str(path.resolve().relative_to(paths.root.resolve()))
