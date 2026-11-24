"""Orquestra ingestão, preparação e disponibilização do dataset de treino.

A lógica mora em ``ml/src/pipeline.py``. Este DAG só define a ordem e lê o
Postgres da coleta pela variável ``PG_DSN``. Disparo manual na interface do
Airflow (http://localhost:8088).

O treino e o teste registram o experimento no MLflow quando a variável
``MLFLOW_TRACKING_URI`` está definida no ambiente do Airflow (no docker-compose,
``http://mlflow:5000``). Sem ela nada é registrado.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_ML_ROOT = Path(__file__).resolve().parents[1]
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

from airflow import DAG
from airflow.operators.python import PythonOperator


def _caminhos():
    from src.paths import ProjectPaths

    return ProjectPaths(Path(os.environ.get("ML_ROOT", str(_ML_ROOT))))


def _rastreio_mlflow() -> None:
    """Avisa no log se o MLflow está ativo; ``src.rastreio`` lê a variável sozinho."""
    uri = os.environ.get("MLFLOW_TRACKING_URI", "")
    if uri:
        print(f"MLflow ativo: {uri}")
    else:
        print("MLFLOW_TRACKING_URI vazio: experimento não será registrado no MLflow")


def _incluir_simulador() -> bool:
    return os.environ.get("MQ3_INCLUIR_SIMULADOR") == "1"


def ingerir() -> dict:
    """Copia rodadas encerradas do Postgres para ``data/raw``, sem reescrever CSV."""
    from src.pipeline import ingerir_do_banco

    dsn = os.environ.get("PG_DSN")
    if not dsn:
        raise RuntimeError("PG_DSN não está definido; o Airflow precisa do Postgres da coleta")
    return ingerir_do_banco(dsn, _caminhos(), incluir_simulador=_incluir_simulador()).como_dict()


def preparar(**context) -> dict:
    """Calcula features e separa treino/teste com o mesmo código do ``prepare``.

    O disparo pode trazer ``{"group_by": "session_file"}``. Sem isso, vale
    ``MQ3_GROUP_BY`` e, por último, a separação por participante.
    """
    from src.pipeline import preparar_dataset

    conf = {}
    dag_run = context.get("dag_run")
    if dag_run is not None and dag_run.conf:
        conf = dag_run.conf
    grupo = conf.get("group_by") or os.environ.get("MQ3_GROUP_BY", "participant_id")
    teste = float(conf.get("test_size") or os.environ.get("MQ3_TEST_SIZE", "0.25"))
    semente = int(conf.get("seed") or os.environ.get("MQ3_SEED", "42"))
    return preparar_dataset(_caminhos(), grupo, teste, semente).como_dict()


def disponibilizar(**context) -> dict:
    """Grava ``data/processed/disponivel.json`` para o treino saber que pode ler."""
    from src.pipeline import gravar_disponivel

    ti = context["ti"]
    return gravar_disponivel(
        _caminhos(),
        ingestao=ti.xcom_pull(task_ids="ingerir"),
        preparacao=ti.xcom_pull(task_ids="preparar"),
    )


def treinar(**context) -> dict:
    """Compara os modelos só com o treino. O resultado fica na XCom e em experiment.csv."""
    from src.pipeline import treinar_modelos

    _rastreio_mlflow()
    conf = {}
    dag_run = context.get("dag_run")
    if dag_run is not None and dag_run.conf:
        conf = dag_run.conf
    select_by = conf.get("select_by") or os.environ.get("MQ3_SELECT_BY", "f1_macro")
    seed = int(conf.get("seed") or os.environ.get("MQ3_SEED", "42"))
    return treinar_modelos(_caminhos(), select_by=select_by, seed=seed)


def testar(**context) -> dict:
    """Avalia uma vez no teste o modelo escolhido pelo treino. As métricas ficam na XCom."""
    from src.pipeline import avaliar_teste

    _rastreio_mlflow()
    escolha = context["ti"].xcom_pull(task_ids="treinar")
    seed = int((escolha or {}).get("seed") or os.environ.get("MQ3_SEED", "42"))
    conf = {}
    dag_run = context.get("dag_run")
    if dag_run is not None and dag_run.conf:
        conf = dag_run.conf
    seed = int(conf.get("seed") or seed)
    return avaliar_teste(_caminhos(), escolha, seed=seed)


with DAG(
    dag_id="dataset_para_treino",
    description="Ingere, prepara, treina no treino e avalia uma vez no teste.",
    start_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["ml"],
) as dag:
    tarefa_ingerir = PythonOperator(task_id="ingerir", python_callable=ingerir)
    tarefa_preparar = PythonOperator(task_id="preparar", python_callable=preparar)
    tarefa_disponibilizar = PythonOperator(task_id="disponibilizar", python_callable=disponibilizar)
    tarefa_treinar = PythonOperator(task_id="treinar", python_callable=treinar)
    tarefa_testar = PythonOperator(task_id="testar", python_callable=testar)
    tarefa_ingerir >> tarefa_preparar >> tarefa_disponibilizar >> tarefa_treinar >> tarefa_testar
