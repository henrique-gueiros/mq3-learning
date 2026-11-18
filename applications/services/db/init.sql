-- Leituras no mesmo formato do CSV do firmware, mais a placa e o nome da sessão.
-- ppm e alcool ficam guardados porque estão no CSV. O modelo não usa essas colunas.

CREATE TABLE leituras (
    id bigserial PRIMARY KEY,
    placa text NOT NULL,
    sessao text NOT NULL,
    amostra bigint NOT NULL,
    t_ms bigint NOT NULL,
    mq3_raw double precision NOT NULL,
    ppm double precision,
    mq135_raw double precision,
    mq135_mv double precision,
    temperature_c double precision,
    humidity_pct double precision,
    alcool integer,
    recebido_em timestamptz NOT NULL DEFAULT now(),
    UNIQUE (placa, sessao, amostra)
);

CREATE TABLE eventos (
    id bigserial PRIMARY KEY,
    placa text NOT NULL,
    sessao text NOT NULL,
    evento text NOT NULL,
    t_ms bigint NOT NULL,
    attempt_id text,
    recebido_em timestamptz NOT NULL DEFAULT now(),
    UNIQUE (placa, sessao, evento, t_ms)
);

CREATE TABLE status_placa (
    placa text PRIMARY KEY,
    status text NOT NULL,
    atualizado_em timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE resultados (
    id bigserial PRIMARY KEY,
    placa text NOT NULL,
    sessao text NOT NULL,
    attempt_id text,
    status text NOT NULL,
    prediction text,
    prob_sem_efeito double precision,
    prob_sob_efeito double precision,
    detalhe text,
    publicado_em timestamptz NOT NULL DEFAULT now()
);
