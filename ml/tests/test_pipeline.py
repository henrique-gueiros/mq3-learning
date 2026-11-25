"""Ingestão, preparação e disponibilização do dataset de treino.

As curvas vêm de ``conftest`` e não representam o sensor.
"""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

import pandas as pd
import pytest

from src.paths import ProjectPaths
from src.pipeline import (
    RodadaColetada,
    SoproColetado,
    agrupar_sopros,
    executar_pipeline,
    ingerir,
)
from tests.conftest import BLOW_START_S, make_dataset, make_session


def _rodada(
    *,
    condition: str = "clean",
    participante: str = "p9",
    arquivo: str = "2026-11-18_p9_clean_1.csv",
    origem: str = "ponte",
    encerrada: bool = True,
    sopros: tuple[tuple[int, int | None], ...] = ((BLOW_START_S * 1000, 25000),),
    seed: int = 1,
    rodada_id: str = "11111111-1111-1111-1111-111111111111",
    leituras: pd.DataFrame | None = None,
) -> RodadaColetada:
    return RodadaColetada(
        rodada_id=rodada_id,
        caso=condition,
        participante=participante,
        arquivo_sessao=arquivo,
        origem=origem,
        encerrada=encerrada,
        leituras=make_session(condition, seed=seed) if leituras is None else leituras,
        sopros=tuple(SoproColetado(inicio, fim) for inicio, fim in sopros),
    )


def _escrever_brutos(paths: ProjectPaths) -> None:
    readings, attempts = make_dataset(n_participants=6, repetitions=1)
    paths.raw_sessions_dir.mkdir(parents=True, exist_ok=True)
    for session_file, session in readings.groupby("session_file"):
        session.drop(columns="session_file").to_csv(paths.raw_sessions_dir / session_file, index=False)
    attempts.drop(columns="target").to_csv(paths.raw_attempts, index=False)


def test_agrupar_sopros_usa_o_fim_marcado_e_deixa_o_ultimo_aberto():
    sopros = agrupar_sopros(
        [
            ("sopro_fim", 1000),
            ("sopro_inicio", 20000),
            ("sopro_fim", 20000),
            ("sopro_fim", 25000),
            ("sopro_inicio", 80000),
        ]
    )
    assert sopros == (SoproColetado(20000, 25000), SoproColetado(80000, None))


def test_ingerir_grava_sessao_nova_e_uma_tentativa_por_sopro(tmp_path):
    paths = ProjectPaths(tmp_path)
    rodada = _rodada(sopros=((20000, 25000), (80000, None)))

    resultado = ingerir([rodada], paths)

    arquivo = paths.raw_sessions_dir / "2026-11-18_p9_clean_1.csv"
    assert resultado.sessoes_gravadas == ("2026-11-18_p9_clean_1.csv",)
    assert arquivo.exists()
    gravado = pd.read_csv(arquivo)
    assert list(gravado["t_ms"]) == list(rodada.leituras.sort_values("t_ms")["t_ms"])
    with paths.raw_attempts.open(encoding="utf-8") as handle:
        linhas = list(csv.DictReader(handle))
    assert [linha["attempt_id"] for linha in linhas] == [
        "2026-11-18_p9_clean_1_s1",
        "2026-11-18_p9_clean_1_s2",
    ]
    assert linhas[0]["condition"] == "clean"
    assert linhas[0]["participant_id"] == "p9"
    assert float(linhas[0]["blow_start_s"]) == 20
    assert float(linhas[0]["blow_end_s"]) == 25
    assert linhas[1]["blow_end_s"] == ""
    assert "11111111-1111-1111-1111-111111111111" in linhas[0]["notes"]


def test_ingerir_anota_csv_que_ja_existia_sem_reescreve_lo(tmp_path):
    paths = ProjectPaths(tmp_path)
    destino = paths.raw_sessions_dir / "2026-11-18_p9_clean_1.csv"
    destino.parent.mkdir(parents=True)
    destino.write_text("csv-da-ponte\n", encoding="utf-8")

    resultado = ingerir([_rodada()], paths)

    assert destino.read_text(encoding="utf-8") == "csv-da-ponte\n"
    assert resultado.sessoes_gravadas == ()
    assert resultado.tentativas_acrescentadas == ("2026-11-18_p9_clean_1_s1",)


def test_ingerir_nao_altera_csv_de_sessao_que_ja_existe(tmp_path):
    paths = ProjectPaths(tmp_path)
    destino = paths.raw_sessions_dir / "2026-11-18_p9_clean_1.csv"
    destino.parent.mkdir(parents=True)
    destino.write_text("conteudo-original\n", encoding="utf-8")
    attempts = paths.raw_attempts
    attempts.write_text(
        "attempt_id,session_file,participant_id,condition,blow_start_s,blow_end_s,reference_mg_l,notes\n"
        "ja-anotado,2026-11-18_p9_clean_1.csv,p9,clean,20,,,\n",
        encoding="utf-8",
    )
    antes = attempts.read_text(encoding="utf-8")

    resultado = ingerir([_rodada()], paths)

    assert destino.read_text(encoding="utf-8") == "conteudo-original\n"
    assert attempts.read_text(encoding="utf-8") == antes
    assert resultado.sessoes_gravadas == ()
    assert resultado.sessoes_preservadas == ("2026-11-18_p9_clean_1.csv",)
    assert resultado.tentativas_acrescentadas == ()


def test_ingerir_e_idempotente(tmp_path):
    paths = ProjectPaths(tmp_path)
    rodada = _rodada()

    ingerir([rodada], paths)
    csv_bytes = (paths.raw_sessions_dir / "2026-11-18_p9_clean_1.csv").read_bytes()
    attempts = paths.raw_attempts.read_text(encoding="utf-8")

    de_novo = ingerir([rodada], paths)

    assert (paths.raw_sessions_dir / "2026-11-18_p9_clean_1.csv").read_bytes() == csv_bytes
    assert paths.raw_attempts.read_text(encoding="utf-8") == attempts
    assert de_novo.tentativas_acrescentadas == ()
    assert de_novo.sessoes_preservadas == ("2026-11-18_p9_clean_1.csv",)


def test_ingerir_acrescenta_tentativa_sem_reescrever_as_que_ja_estavam(tmp_path):
    paths = ProjectPaths(tmp_path)
    paths.raw_attempts.parent.mkdir(parents=True)
    paths.raw_attempts.write_text(
        "attempt_id,session_file,participant_id,condition,blow_start_s,blow_end_s,reference_mg_l,notes\n"
        "p1-clean-0,p1_clean_0.csv,p1,clean,20,,,anotado à mão\n",
        encoding="utf-8",
    )

    ingerir([_rodada()], paths)

    texto = paths.raw_attempts.read_text(encoding="utf-8")
    assert "p1-clean-0,p1_clean_0.csv,p1,clean,20,,,anotado à mão\n" in texto
    assert "2026-11-18_p9_clean_1_s1" in texto


def test_ingerir_deixa_de_fora_simulador_caso_desconhecido_e_rodada_aberta(tmp_path):
    paths = ProjectPaths(tmp_path)
    resultado = ingerir(
        [
            _rodada(origem="simulador", arquivo="sim.csv", rodada_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            _rodada(
                condition="alcool_no_ar",
                arquivo="errado.csv",
                rodada_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                leituras=make_session("clean"),
            ),
            _rodada(encerrada=False, arquivo="aberta.csv", rodada_id="cccccccc-cccc-cccc-cccc-cccccccccccc"),
            _rodada(arquivo="../fora.csv", rodada_id="dddddddd-dddd-dddd-dddd-dddddddddddd"),
        ],
        paths,
    )

    assert resultado.sessoes_gravadas == ()
    assert not paths.raw_sessions_dir.exists() or list(paths.raw_sessions_dir.glob("*.csv")) == []
    assert not (tmp_path / "fora.csv").exists()
    assert any("simulador" in aviso for aviso in resultado.avisos)
    assert any("desconhecid" in aviso for aviso in resultado.avisos)
    assert any("aberta" in aviso for aviso in resultado.avisos)
    assert any("nome de arquivo" in aviso for aviso in resultado.avisos)


def test_ingerir_nao_grava_sessao_invalida(tmp_path):
    paths = ProjectPaths(tmp_path)
    leituras = make_session("clean")
    leituras["mq3_raw"] = None
    resultado = ingerir([_rodada(leituras=leituras)], paths)

    assert resultado.sessoes_gravadas == ()
    assert resultado.tentativas_acrescentadas == ()
    assert any("inválid" in aviso for aviso in resultado.avisos)


def test_executar_pipeline_disponibiliza_o_dataset_que_ja_esta_em_raw(tmp_path):
    paths = ProjectPaths(tmp_path)
    _escrever_brutos(paths)

    manifesto = executar_pipeline(paths)

    assert manifesto["pronto_para_treino"] is True
    assert paths.features_all.exists()
    assert paths.train.exists()
    assert paths.test.exists()
    gravado = json.loads(paths.disponivel.read_text(encoding="utf-8"))
    assert gravado["n_treino"] + gravado["n_teste"] == gravado["n_features"]
    assert gravado["n_features"] == 18
    assert Path(tmp_path, gravado["treino"]).exists()


def test_executar_pipeline_inclui_rodada_nova_do_banco(tmp_path):
    paths = ProjectPaths(tmp_path)
    _escrever_brutos(paths)

    manifesto = executar_pipeline(paths, rodadas=[_rodada()])

    features = pd.read_csv(paths.features_all)
    assert "2026-11-18_p9_clean_1_s1" in set(features["attempt_id"])
    assert manifesto["tentativas_acrescentadas"] == ["2026-11-18_p9_clean_1_s1"]


def test_executar_pipeline_falha_sem_dados(tmp_path):
    with pytest.raises(FileNotFoundError):
        executar_pipeline(ProjectPaths(tmp_path))


def test_cli_pipeline_grava_o_manifesto(tmp_path):
    from src.cli import main

    paths = ProjectPaths(tmp_path)
    _escrever_brutos(paths)

    assert main(["--root", str(tmp_path), "pipeline", "--dsn", ""]) == 0
    assert json.loads(paths.disponivel.read_text(encoding="utf-8"))["pronto_para_treino"] is True


def test_treino_escolhe_modelo_e_o_teste_mede_uma_vez(tmp_path):
    from src.data_io import write_csv
    from src.pipeline import avaliar_teste, treinar_modelos
    from src.splitting import apply_split, save_split, update_split
    from tests.conftest import make_feature_dataset

    paths = ProjectPaths(tmp_path)
    dataset = make_feature_dataset(n_participants=6, repetitions=1)
    split, _ = update_split(dataset, existing=None, group_by="participant_id", test_size=0.25, seed=42)
    save_split(split, paths.split_manifest)
    train, test = apply_split(dataset, split)
    write_csv(train, paths.train)
    write_csv(test, paths.test)

    escolha = treinar_modelos(paths, n_estimators=5)
    resultado = avaliar_teste(paths, escolha, seed=42)

    assert escolha["sensor_set"] == "mq3+mq135+dht11"
    assert escolha["n_treino"] == len(train)
    assert resultado["n_teste"] == len(test)
    assert "recall_sob_efeito" in resultado["metricas_teste"]
    assert (paths.models_dir / "sob_efeito.joblib").exists()
    assert (paths.reports_dir / "experiment.csv").exists()


def test_dag_declara_treino_e_teste():
    fonte = Path(__file__).resolve().parents[1] / "dags" / "dataset_para_treino.py"
    arvore = ast.parse(fonte.read_text(encoding="utf-8"))

    class _Visitante(ast.NodeVisitor):
        def __init__(self) -> None:
            self.tarefas: list[str] = []

        def visit_keyword(self, no: ast.keyword) -> None:
            if no.arg == "task_id" and isinstance(no.value, ast.Constant):
                self.tarefas.append(no.value.value)
            self.generic_visit(no)

    visitante = _Visitante()
    visitante.visit(arvore)
    assert visitante.tarefas == ["ingerir", "preparar", "disponibilizar", "treinar", "testar"]
    texto = fonte.read_text(encoding="utf-8")
    assert "tarefa_ingerir >> tarefa_preparar >> tarefa_disponibilizar >> tarefa_treinar >> tarefa_testar" in texto


def _preparar_treino_e_teste(paths: ProjectPaths) -> None:
    from src.data_io import write_csv
    from src.splitting import apply_split, save_split, update_split
    from tests.conftest import make_feature_dataset

    dataset = make_feature_dataset(n_participants=8, repetitions=1)
    split, _ = update_split(dataset, existing=None, group_by="participant_id", test_size=0.25, seed=42)
    save_split(split, paths.split_manifest)
    train, test = apply_split(dataset, split)
    write_csv(train, paths.train)
    write_csv(test, paths.test)


def test_treino_e_teste_gravam_figuras_e_desvios(tmp_path, monkeypatch):
    from src.pipeline import avaliar_teste, treinar_modelos

    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    paths = ProjectPaths(tmp_path)
    _preparar_treino_e_teste(paths)

    escolha = treinar_modelos(paths, n_estimators=5)
    avaliar_teste(paths, escolha, seed=42)

    experimento = pd.read_csv(paths.reports_dir / "experiment.csv")
    assert {"f1_macro_std", "f1_macro_treino", "roc_auc"} <= set(experimento.columns)
    assert (paths.reports_dir / "folds.csv").exists()
    for nome in ("f1_por_modelo", "treino_vs_validacao", "curva_aprendizado", "matriz_confusao", "roc"):
        assert (paths.figuras_dir / f"{nome}.png").exists(), nome


def test_treino_e_teste_vao_para_o_mlflow_quando_ha_uri(tmp_path, monkeypatch):
    import mlflow

    from src.pipeline import avaliar_teste, treinar_modelos

    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file:{tmp_path / 'mlruns'}")
    paths = ProjectPaths(tmp_path)
    _preparar_treino_e_teste(paths)

    escolha = treinar_modelos(paths, n_estimators=5)
    avaliar_teste(paths, escolha, seed=42)

    runs = mlflow.search_runs(search_all_experiments=True)
    nomes = set(runs["tags.mlflow.runName"])
    assert {"comparacao_de_modelos", "modelo_final"} <= nomes
    assert len(runs) > 2


def test_dag_repassa_a_uri_do_mlflow():
    fonte = Path(__file__).resolve().parents[1] / "dags" / "dataset_para_treino.py"
    assert "MLFLOW_TRACKING_URI" in fonte.read_text(encoding="utf-8")


def test_curva_de_aprendizado_usa_os_hiperparametros_mais_escolhidos():
    from src.pipeline import _com_parametros_escolhidos
    from src.train import model_specs

    pipeline = model_specs()["logistic_regression"].pipeline
    escolhidos = json.dumps([{"clf__C": 10.0}, {"clf__C": 0.1}, {"clf__C": 10.0}])

    assert _com_parametros_escolhidos(pipeline, escolhidos).get_params()["clf__C"] == 10.0
    assert _com_parametros_escolhidos(pipeline, "[{}, {}]").get_params()["clf__C"] == pipeline.get_params()["clf__C"]
