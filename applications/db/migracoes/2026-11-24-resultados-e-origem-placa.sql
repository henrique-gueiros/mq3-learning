-- Banco criado antes de 24/11/2026: aceita rodadas publicadas pela própria placa
-- e cria a tabela de resultados do servidor do modelo ao vivo.
-- Uso: docker compose exec -T postgres psql -U mq3 -d mq3 < applications/db/migracoes/2026-11-24-resultados-e-origem-placa.sql
BEGIN;

ALTER TABLE rodadas DROP CONSTRAINT IF EXISTS rodadas_origem_check;
ALTER TABLE rodadas ADD CONSTRAINT rodadas_origem_check
    CHECK (origem IN ('ponte', 'importador', 'simulador', 'placa'));

CREATE TABLE IF NOT EXISTS resultados (
    rodada_id       uuid NOT NULL REFERENCES rodadas (id),
    t_ms            bigint NOT NULL,
    attempt_id      text,
    status          text NOT NULL,
    prediction      text CHECK (prediction IN ('sob_efeito', 'sem_efeito')),
    prob_sem_efeito real,
    prob_sob_efeito real,
    detalhe         text,
    criado_em       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (rodada_id, t_ms)
);

-- Usuário só leitura da API (02-leitor.sh só dá SELECT nas tabelas que já existiam).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_leitor') THEN
        GRANT SELECT ON resultados TO grafana_leitor;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'leitor') THEN
        GRANT SELECT ON resultados TO leitor;
    END IF;
END $$;

COMMIT;
