"""Linha de comando do pipeline.

Rode de dentro da pasta ``ml/``::

    python -m src.cli validate   # confere sessões e tentativas de data/raw/
    python -m src.cli prepare    # features por sopro + separação treino/teste
    python -m src.cli train      # experimento por sensores e modelo final
    python -m src.cli predict --session leituras_7.csv --blow-start-s 60
    python -m src.cli all        # prepare + train
    python -m src.cli pipeline   # ingestão (se PG_DSN), preparação e disponibilização
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

from src.data_io import load_raw_data, read_dataset_csv, read_session_csv, write_csv
from src.features import SENSOR_SETS
from src.inference import predict_attempts
from src.paths import ML_ROOT, ProjectPaths
from src import rastreio
from src.pipeline import avaliar_teste, executar_pipeline, preparar_dataset, treinar_modelos
from src.splitting import GROUP_COLUMNS


def run_validate(paths: ProjectPaths) -> None:
    """Valida sessões e tentativas reais e mostra um resumo."""
    readings, attempts, warnings = load_raw_data(paths.raw_sessions_dir, paths.raw_attempts)
    _print_warnings(warnings)
    print(
        f"OK: {readings['session_file'].nunique()} sessão(ões), {len(readings)} leituras, "
        f"{len(attempts)} tentativas, {attempts['participant_id'].nunique()} participantes"
    )
    print("Tentativas por condição: " + _counts(attempts["condition"]))
    print("Tentativas por classe:   " + _counts(attempts["target"]))


def run_prepare(paths: ProjectPaths, group_by: str, test_size: float, seed: int) -> None:
    """Calcula as features de cada sopro e separa treino e teste por grupo."""
    resumo = preparar_dataset(paths, group_by, test_size, seed)
    _print_warnings(list(resumo.avisos))
    print(f"Features: {resumo.n_features} tentativas -> {_rel(paths, paths.features_all)}")
    print(f"Separação por {resumo.group_by} -> {_rel(paths, paths.split_manifest)}")
    for name, n_grupos, n_tentativas, contagem, path in (
        ("Treino", resumo.n_grupos_treino, resumo.n_treino, resumo.treino_por_classe, paths.train),
        ("Teste ", resumo.n_grupos_teste, resumo.n_teste, resumo.teste_por_classe, paths.test),
    ):
        print(
            f"{name}: {n_grupos} grupos, {n_tentativas} tentativas "
            f"({_fmt_contagem(contagem)}) -> {_rel(paths, path)}"
        )


def run_pipeline(
    paths: ProjectPaths,
    group_by: str,
    test_size: float,
    seed: int,
    dsn: str | None,
    incluir_simulador: bool,
) -> None:
    """Ingere rodadas do banco (se houver DSN), prepara e grava o manifesto."""
    print("== Ingestão, preparação e disponibilização ==")
    manifesto = executar_pipeline(
        paths,
        group_by=group_by,
        test_size=test_size,
        seed=seed,
        incluir_simulador=incluir_simulador,
        dsn=dsn,
    )
    _print_warnings(manifesto["avisos"])
    print(
        f"Sessões novas: {len(manifesto['sessoes_gravadas'])}; "
        f"preservadas: {len(manifesto['sessoes_preservadas'])}; "
        f"tentativas novas: {len(manifesto['tentativas_acrescentadas'])}"
    )
    print(
        f"Dataset: {manifesto['n_features']} tentativas "
        f"(treino {manifesto['n_treino']}, teste {manifesto['n_teste']}) "
        f"-> {_rel(paths, paths.disponivel)}"
    )


def run_train(paths: ProjectPaths, select_by: str, seed: int) -> None:
    """Compara os modelos e salva o melhor (mesmo fluxo do Airflow: ``pipeline``)."""
    print("\n== Comparação: sob_efeito ou sem_efeito ==")
    escolha = treinar_modelos(paths, select_by=select_by, seed=seed)
    resultados = read_dataset_csv(paths.reports_dir / "experiment.csv")
    _print_results(resultados)
    print(f"Resultados da validação cruzada: {escolha['relatorio']}")

    resultado = avaliar_teste(paths, escolha, seed=seed)
    print(f"Escolhido por {select_by}: {resultado['modelo']} com {resultado['sensor_set']}")
    if resultado["metricas_teste"]:
        metricas = ", ".join(f"{k}={_fmt_metrica(v)}" for k, v in resultado["metricas_teste"].items())
        print(f"Teste ({resultado['n_teste']} tentativas): {metricas}")
    else:
        print("Aviso: o teste não tem tentativas; nada foi avaliado.")
    print(f"Modelo: {resultado['modelo_arquivo']} | Relatório: {resultado['relatorio']}")
    print(f"Figuras: {_rel(paths, paths.figuras_dir)}")
    if rastreio.ativo():
        print(f"Experimento registrado no MLflow ({os.environ['MLFLOW_TRACKING_URI']})")


def run_predict(
    paths: ProjectPaths,
    session_path: Path,
    blow_start_s: float,
    blow_end_s: float | None,
    model_path: Path,
    output: Path | None,
) -> None:
    """Classifica um sopro de um CSV de sessão do firmware."""
    readings = read_session_csv(session_path)
    attempt = pd.DataFrame(
        {
            "attempt_id": [f"{Path(session_path).stem}@{blow_start_s:g}s"],
            "session_file": [Path(session_path).name],
            "blow_start_s": [blow_start_s],
            "blow_end_s": [blow_end_s],
        }
    )
    predictions, warnings = predict_attempts(readings, attempt, model_path)
    _print_warnings(warnings)
    with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 120):
        print(predictions.to_string(index=False))
    if output:
        write_csv(predictions, output)
        print(f"Previsões: {_rel(paths, output)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli", description="Pipeline de ML do detector de álcool com MQ-3, MQ-135 e DHT11."
    )
    parser.add_argument("--root", type=Path, default=ML_ROOT, help="pasta ml/ (padrão: a deste repositório)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="confere sessões e tentativas de data/raw/")

    prepare = sub.add_parser("prepare", help="features por sopro e separação treino/teste")
    _add_prepare_args(prepare)

    train = sub.add_parser("train", help="experimento por conjunto de sensores e modelo final")
    _add_train_args(train)

    predict = sub.add_parser("predict", help="classifica um sopro de uma sessão nova")
    predict.add_argument("--session", type=Path, required=True, help="CSV de sessão gravado pelo firmware")
    predict.add_argument("--blow-start-s", type=float, required=True, help="segundo da sessão em que o sopro começou")
    predict.add_argument("--blow-end-s", type=float, help="segundo em que o sopro terminou (opcional)")
    predict.add_argument("--model", type=Path, help="modelo .joblib (padrão: models/sob_efeito.joblib)")
    predict.add_argument("--output", type=Path, help="CSV para salvar as previsões (opcional)")

    run_all = sub.add_parser("all", help="prepare e train")
    _add_prepare_args(run_all)
    _add_train_args(run_all, with_seed=False)

    pipeline = sub.add_parser(
        "pipeline",
        help="ingestão (Postgres, se --dsn), preparação e disponibilização do dataset",
    )
    _add_prepare_args(pipeline)
    pipeline.add_argument(
        "--dsn",
        default=os.environ.get("PG_DSN") or None,
        help="Postgres da coleta (padrão: a variável PG_DSN). Vazio usa só os CSVs já em data/raw",
    )
    pipeline.add_argument(
        "--incluir-simulador",
        action="store_true",
        help="também exporta rodadas com origem simulador (fora do treino por padrão)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = ProjectPaths(args.root.resolve())
    try:
        if args.command == "validate":
            run_validate(paths)
        elif args.command == "prepare":
            run_prepare(paths, args.group_by, args.test_size, args.seed)
        elif args.command == "train":
            run_train(paths, args.select_by, args.seed)
        elif args.command == "predict":
            model = args.model or paths.models_dir / "sob_efeito.joblib"
            run_predict(paths, args.session, args.blow_start_s, args.blow_end_s, model, args.output)
        elif args.command == "all":
            print("== Preparação ==")
            run_prepare(paths, args.group_by, args.test_size, args.seed)
            run_train(paths, args.select_by, args.seed)
        elif args.command == "pipeline":
            run_pipeline(
                paths, args.group_by, args.test_size, args.seed, args.dsn or None, args.incluir_simulador
            )
    except (ValueError, FileNotFoundError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


def _add_prepare_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--group-by", choices=GROUP_COLUMNS, default="participant_id",
        help="separar treino/teste por participante (padrão) ou por arquivo de sessão",
    )
    parser.add_argument("--test-size", type=float, default=0.25, help="fração de grupos no teste (padrão: 0.25)")
    parser.add_argument("--seed", type=int, default=42, help="semente (padrão: 42)")


def _add_train_args(parser: argparse.ArgumentParser, with_seed: bool = True) -> None:
    parser.add_argument(
        "--select-by", default="f1_macro",
        help="métrica da validação cruzada para escolher o modelo final (ex.: f1_macro, recall_sob_efeito)",
    )
    if with_seed:
        parser.add_argument("--seed", type=int, default=42, help="semente (padrão: 42)")


def _print_results(results: pd.DataFrame) -> None:
    columns = ["sensor_set", "model", "f1_macro", "balanced_accuracy"]
    columns += [c for c in results.columns if c.startswith("recall_")]
    table = results[columns].copy()
    table["sensor_set"] = pd.Categorical(table["sensor_set"], categories=list(SENSOR_SETS))
    with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 160):
        print(table.sort_values(["sensor_set", "model"]).to_string(index=False))


def _counts(values: pd.Series) -> str:
    return ", ".join(f"{k}: {v}" for k, v in values.value_counts().sort_index().items())


def _fmt_metrica(valor: float | None) -> str:
    """Duas casas decimais; ``—`` quando a métrica não pôde ser calculada (ex.: AUC sem as duas classes)."""
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:.2f}"


def _fmt_contagem(contagem: dict[str, int]) -> str:
    return ", ".join(f"{classe}: {quantidade}" for classe, quantidade in sorted(contagem.items()))


def _print_warnings(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"Aviso: {warning}")


def _rel(paths: ProjectPaths, path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(paths.root))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())
