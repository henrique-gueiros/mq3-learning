"""Linha de comando do pipeline.

Rode de dentro da pasta ``ml/``::

    python -m src.cli validate   # confere leituras e tentativas de data/raw/
    python -m src.cli prepare    # features por sopro + separação treino/teste
    python -m src.cli train      # experimento por sensores e modelo final
    python -m src.cli predict --readings novas.csv
    python -m src.cli all        # prepare + train
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.data_io import load_raw_data, read_dataset_csv, read_readings_csv, write_csv
from src.features import SENSOR_SETS, TASKS, build_dataset, compute_features
from src.inference import predict_attempts
from src.paths import ML_ROOT, ProjectPaths
from src.splitting import GROUP_COLUMNS, apply_split, load_split, save_split, update_split
from src.train import choose_best, run_experiment, save_model, train_final_model


def run_validate(paths: ProjectPaths) -> None:
    """Valida leituras e tentativas reais e mostra um resumo."""
    readings, attempts, warnings = load_raw_data(paths.raw_readings_dir, paths.raw_attempts)
    _print_warnings(warnings)
    print(
        f"OK: {readings['source_file'].nunique()} arquivo(s) de leituras, {len(readings)} leituras, "
        f"{len(attempts)} tentativas, {attempts['participant_id'].nunique()} participantes, "
        f"{attempts['session_id'].nunique()} sessões"
    )
    print("Tentativas por condição: " + _counts(attempts["condition"]))
    print("Tentativas por classe:   " + _counts(attempts["target"]))


def run_prepare(paths: ProjectPaths, group_by: str, test_size: float, seed: int) -> None:
    """Calcula as features de cada sopro e separa treino e teste por grupo."""
    readings, attempts, warnings = load_raw_data(paths.raw_readings_dir, paths.raw_attempts)
    features, feature_warnings = compute_features(readings)
    dataset = build_dataset(features, attempts)
    if dataset.empty:
        raise ValueError("nenhuma tentativa com features válidas")
    write_csv(dataset, paths.features_all)

    split, split_warnings = update_split(dataset, load_split(paths.split_manifest), group_by, test_size, seed)
    _print_warnings(warnings + feature_warnings + split_warnings)
    save_split(split, paths.split_manifest)
    train, test = apply_split(dataset, split)
    write_csv(train, paths.train)
    write_csv(test, paths.test)

    print(f"Features: {len(dataset)} tentativas -> {_rel(paths, paths.features_all)}")
    print(f"Separação por {split.group_by} -> {_rel(paths, paths.split_manifest)}")
    for name, part, path in (("Treino", train, paths.train), ("Teste ", test, paths.test)):
        print(
            f"{name}: {part[split.group_by].nunique()} grupos, {len(part)} tentativas "
            f"({_counts(part['target'])}) -> {_rel(paths, path)}"
        )


def run_train(paths: ProjectPaths, tasks: list[str], select_by: str, seed: int) -> None:
    """Roda o experimento por conjunto de sensores e salva o melhor modelo de cada tarefa."""
    split = load_split(paths.split_manifest)
    if split is None:
        raise FileNotFoundError(f"{_rel(paths, paths.split_manifest)} não existe; rode 'prepare' antes")
    train = read_dataset_csv(paths.train)
    test = read_dataset_csv(paths.test)

    for task in tasks:
        print(f"\n== Tarefa {task}: {TASKS[task]} ==")
        results = run_experiment(train, task, group_by=split.group_by, seed=seed)
        report = paths.reports_dir / f"experiment_{task}.csv"
        write_csv(results, report)
        _print_results(results)
        print(f"Resultados da validação cruzada: {_rel(paths, report)}")

        best = choose_best(results, select_by)
        model, metadata = train_final_model(
            train, test, task, best["sensor_set"], best["model"], group_by=split.group_by, seed=seed
        )
        metadata["selected_by"] = select_by
        metadata["cv_score"] = float(best[select_by])
        model_path = paths.models_dir / f"{task}.joblib"
        save_model(model, metadata, model_path)
        final_report = paths.reports_dir / f"final_{task}.json"
        final_report.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
        )

        print(f"Escolhido por {select_by}: {best['model']} com {best['sensor_set']}")
        if "test_metrics" in metadata:
            metrics = ", ".join(f"{k}={v:.2f}" for k, v in metadata["test_metrics"].items())
            print(f"Teste ({metadata['n_test_attempts']} tentativas): {metrics}")
        else:
            print("Aviso: o teste não tem tentativas desta tarefa; nada foi avaliado.")
        print(f"Modelo: {_rel(paths, model_path)} | Relatório: {_rel(paths, final_report)}")


def run_predict(paths: ProjectPaths, readings_path: Path, model_path: Path, output: Path | None) -> None:
    """Classifica tentativas novas de um CSV de leituras."""
    readings = read_readings_csv(readings_path)
    predictions, warnings = predict_attempts(readings, model_path)
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

    sub.add_parser("validate", help="confere leituras e tentativas de data/raw/")

    prepare = sub.add_parser("prepare", help="features por sopro e separação treino/teste")
    _add_prepare_args(prepare)

    train = sub.add_parser("train", help="experimento por conjunto de sensores e modelo final")
    _add_train_args(train)

    predict = sub.add_parser("predict", help="classifica tentativas novas")
    predict.add_argument("--readings", type=Path, required=True, help="CSV de leituras no formato do template")
    predict.add_argument("--model", type=Path, help="modelo .joblib (padrão: models/3classes.joblib)")
    predict.add_argument("--output", type=Path, help="CSV para salvar as previsões (opcional)")

    run_all = sub.add_parser("all", help="prepare e train")
    _add_prepare_args(run_all)
    _add_train_args(run_all, with_seed=False)
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
            run_train(paths, _tasks(args.task), args.select_by, args.seed)
        elif args.command == "predict":
            model = args.model or paths.models_dir / "3classes.joblib"
            run_predict(paths, args.readings, model, args.output)
        elif args.command == "all":
            print("== Preparação ==")
            run_prepare(paths, args.group_by, args.test_size, args.seed)
            run_train(paths, _tasks(args.task), args.select_by, args.seed)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


def _add_prepare_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--group-by", choices=GROUP_COLUMNS, default="participant_id",
        help="separar treino/teste por participante (padrão) ou por sessão",
    )
    parser.add_argument("--test-size", type=float, default=0.25, help="fração de grupos no teste (padrão: 0.25)")
    parser.add_argument("--seed", type=int, default=42, help="semente (padrão: 42)")


def _add_train_args(parser: argparse.ArgumentParser, with_seed: bool = True) -> None:
    parser.add_argument(
        "--task", choices=[*TASKS, "todas"], default="todas", help="tarefa a treinar (padrão: todas)"
    )
    parser.add_argument(
        "--select-by", default="f1_macro",
        help="métrica da validação cruzada para escolher o modelo final (ex.: f1_macro, recall_bebida)",
    )
    if with_seed:
        parser.add_argument("--seed", type=int, default=42, help="semente (padrão: 42)")


def _tasks(task: str) -> list[str]:
    return list(TASKS) if task == "todas" else [task]


def _print_results(results: pd.DataFrame) -> None:
    columns = ["sensor_set", "model", "f1_macro", "balanced_accuracy"]
    columns += [c for c in results.columns if c.startswith("recall_")]
    table = results[columns].copy()
    table["sensor_set"] = pd.Categorical(table["sensor_set"], categories=list(SENSOR_SETS))
    with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 160):
        print(table.sort_values(["sensor_set", "model"]).to_string(index=False))


def _counts(values: pd.Series) -> str:
    return ", ".join(f"{k}: {v}" for k, v in values.value_counts().sort_index().items())


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
