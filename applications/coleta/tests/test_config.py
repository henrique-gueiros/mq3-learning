from coleta.config import Config


def test_dsn_vem_do_env_do_repositorio(tmp_path, monkeypatch):
    monkeypatch.delenv("PG_DSN", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comentário\nPOSTGRES_DB=mq3\nPOSTGRES_USER=mq3\nPOSTGRES_PASSWORD=segredo\n")
    assert Config.do_ambiente(env).pg_dsn == "postgresql://mq3:segredo@localhost:5432/mq3"


def test_pg_dsn_do_ambiente_tem_prioridade(tmp_path, monkeypatch):
    monkeypatch.setenv("PG_DSN", "postgresql://x:y@h:1/z")
    (tmp_path / ".env").write_text("POSTGRES_PASSWORD=segredo\n")
    assert Config.do_ambiente(tmp_path / ".env").pg_dsn == "postgresql://x:y@h:1/z"


def test_sem_env(tmp_path, monkeypatch):
    monkeypatch.delenv("PG_DSN", raising=False)
    assert Config.do_ambiente(tmp_path / "nao_existe").pg_dsn == Config().pg_dsn
