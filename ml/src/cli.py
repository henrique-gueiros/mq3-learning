"""Linha de comando do pipeline de dados.

Rode de dentro da pasta ``ml/``::

    python -m src.cli validate   # confere os CSVs de data/raw/
    python -m src.cli split      # separa sessões de treino e teste
    python -m src.cli estimate   # estima o gerador a partir do treino real
    python -m src.cli generate   # gera os dados sintéticos
    python -m src.cli prepare    # monta data/processed/train.csv e test.csv
    python -m src.cli all        # tudo acima, em ordem
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.data_generation import generate_synthetic, load_params, save_params
from src.data_io import load_raw_readings, read_readings_csv, write_readings_csv
from src.parameter_estimation import estimate_params
from src.paths import ML_ROOT, ProjectPaths
from src.preprocessing import build_train_test
from src.splitting import apply_split, load_split, save_split, update_split


def run_validate(paths: ProjectPaths) -> pd.DataFrame:
    """Valida os CSVs reais e mostra um resumo."""
    df = load_raw_readings(paths.raw_dir)
    print(f"OK: {df['source_file'].nunique()} arquivo(s), {len(df)} leituras, {df['session_id'].nunique()} sessões")
    _print_label_counts(df)
    return df


def run_split(paths: ProjectPaths, test_size: float, seed: int) -> None:
    """Atualiza o manifesto de sessões e grava ``real_train.csv`` e ``real_test.csv``."""
    df = load_raw_readings(paths.raw_dir)
    split, warnings = update_split(df, load_split(paths.split_manifest), test_size, seed)
    _print_warnings(warnings)
    save_split(split, paths.split_manifest)

    train, test = apply_split(df, split)
    write_readings_csv(train, paths.real_train)
    write_readings_csv(test, paths.real_test)
    print(f"Treino: {len(split.train_sessions)} sessões, {len(train)} leituras -> {_rel(paths, paths.real_train)}")
    print(f"Teste:  {len(split.test_sessions)} sessões, {len(test)} leituras -> {_rel(paths, paths.real_test)}")
    print(f"Manifesto: {_rel(paths, paths.split_manifest)}")


def run_estimate(paths: ProjectPaths, n_sessions: int | None, seed: int) -> None:
    """Estima os parâmetros do gerador usando só o treino real."""
    if not paths.real_train.exists():
        raise FileNotFoundError(f"{_rel(paths, paths.real_train)} não existe; rode 'split' antes")
    train = read_readings_csv(paths.real_train, expected_source="real")
    params, warnings = estimate_params(train, n_sessions_per_class=n_sessions, seed=seed)
    _print_warnings(warnings)
    save_params(params, paths.estimated_params)
    for label, cp in sorted(params.classes.items()):
        print(
            f"label={label}: nível {cp.level_mean:.2f} ± {cp.level_std:.2f} entre sessões, "
            f"ruído {cp.noise_std:.2f}, {cp.samples_per_session} leituras/sessão"
        )
    print(f"Parâmetros: {_rel(paths, paths.estimated_params)}")


def run_generate(
    paths: ProjectPaths, config: Path | None, seed: int | None, output: Path | None
) -> Path:
    """Gera dados sintéticos a partir de um arquivo de parâmetros."""
    if config is None:
        config = paths.estimated_params if paths.estimated_params.exists() else paths.didactic_params
    params = load_params(config)
    if params.origin == "didactic":
        print("Aviso: parâmetros didáticos (inventados), servem só para testar o código.")

    df = generate_synthetic(params, seed=seed)
    output = output or paths.synthetic_dir / f"synthetic_{params.origin}.csv"
    write_readings_csv(df, output)
    print(f"Gerado com {_rel(paths, Path(config))}: {df['session_id'].nunique()} sessões, {len(df)} leituras")
    _print_label_counts(df)
    print(f"Arquivo: {_rel(paths, output)}")
    return output


def run_prepare(paths: ProjectPaths, synthetic_path: Path | None) -> None:
    """Monta ``train.csv`` (real + sintético opcional) e ``test.csv`` (só real)."""
    for path in (paths.real_train, paths.real_test):
        if not path.exists():
            raise FileNotFoundError(f"{_rel(paths, path)} não existe; rode 'split' antes")
    real_train = read_readings_csv(paths.real_train, expected_source="real")
    real_test = read_readings_csv(paths.real_test, expected_source="real")
    synthetic = read_readings_csv(synthetic_path, expected_source="synthetic") if synthetic_path else None

    train, test, warnings = build_train_test(real_train, real_test, synthetic)
    _print_warnings(warnings)
    write_readings_csv(train, paths.train)
    write_readings_csv(test, paths.test)
    print(f"Treino: {len(train)} leituras por origem {train['source'].value_counts().to_dict()} -> {_rel(paths, paths.train)}")
    print(f"Teste:  {len(test)} leituras reais -> {_rel(paths, paths.test)}")


def run_all(paths: ProjectPaths, test_size: float, seed: int, n_sessions: int | None) -> None:
    """Executa todas as etapas em ordem, usando o gerador estimado."""
    print("== Validação ==")
    run_validate(paths)
    print("\n== Separação treino/teste ==")
    run_split(paths, test_size, seed)
    print("\n== Estimativa do gerador ==")
    run_estimate(paths, n_sessions, seed)
    print("\n== Geração sintética ==")
    synthetic_path = run_generate(paths, paths.estimated_params, None, None)
    print("\n== Conjuntos finais ==")
    run_prepare(paths, synthetic_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli", description="Pipeline de dados do detector de álcool com MQ-3."
    )
    parser.add_argument("--root", type=Path, default=ML_ROOT, help="pasta ml/ (padrão: a deste repositório)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="confere os CSVs reais de data/raw/")

    split = sub.add_parser("split", help="separa sessões reais em treino e teste")
    _add_split_args(split)

    estimate = sub.add_parser("estimate", help="estima os parâmetros do gerador a partir do treino real")
    _add_estimate_args(estimate)

    generate = sub.add_parser("generate", help="gera dados sintéticos")
    generate.add_argument("--config", type=Path, help="JSON de parâmetros (padrão: estimado, ou didático se não existir)")
    generate.add_argument("--seed", type=int, help="substitui a seed do arquivo de parâmetros")
    generate.add_argument("--output", type=Path, help="CSV de saída (padrão: data/synthetic/synthetic_<origem>.csv)")

    prepare = sub.add_parser("prepare", help="monta data/processed/train.csv e test.csv")
    prepare.add_argument("--synthetic", type=Path, help="CSV sintético para somar ao treino (opcional)")

    run_all_parser = sub.add_parser("all", help="validate, split, estimate, generate e prepare")
    _add_split_args(run_all_parser)
    _add_estimate_args(run_all_parser, with_seed=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = ProjectPaths(args.root.resolve())
    try:
        if args.command == "validate":
            run_validate(paths)
        elif args.command == "split":
            run_split(paths, args.test_size, args.seed)
        elif args.command == "estimate":
            run_estimate(paths, args.n_sessions, args.seed)
        elif args.command == "generate":
            run_generate(paths, args.config, args.seed, args.output)
        elif args.command == "prepare":
            run_prepare(paths, args.synthetic)
        elif args.command == "all":
            run_all(paths, args.test_size, args.seed, args.n_sessions)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


def _add_split_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--test-size", type=float, default=0.25, help="fração de sessões de teste (padrão: 0.25)")
    parser.add_argument("--seed", type=int, default=42, help="semente do sorteio (padrão: 42)")


def _add_estimate_args(parser: argparse.ArgumentParser, with_seed: bool = True) -> None:
    parser.add_argument(
        "--n-sessions", type=int, default=20, help="sessões sintéticas por classe (padrão: 20; 0 = igual ao real)"
    )
    if with_seed:
        parser.add_argument("--seed", type=int, default=42, help="seed gravada nos parâmetros (padrão: 42)")


def _print_label_counts(df: pd.DataFrame) -> None:
    counts = df["label"].value_counts(dropna=False)
    parts = [f"label={'vazio' if pd.isna(k) else int(k)}: {v}" for k, v in counts.sort_index().items()]
    print("Leituras por rótulo: " + ", ".join(parts))


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
