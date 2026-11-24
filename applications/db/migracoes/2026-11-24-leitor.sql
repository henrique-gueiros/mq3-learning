-- Banco criado antes de 24/11/2026: o usuário só leitura deixa de ser do Grafana
-- (removido) e passa a se chamar leitor. A senha continua a mesma; no .env, a
-- variável nova é LEITOR_PG_SENHA (o compose ainda aceita GRAFANA_PG_SENHA).
-- Uso: docker compose exec -T postgres psql -U mq3 -d mq3 < applications/db/migracoes/2026-11-24-leitor.sql
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_leitor')
       AND NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'leitor') THEN
        ALTER ROLE grafana_leitor RENAME TO leitor;
    END IF;
END $$;
