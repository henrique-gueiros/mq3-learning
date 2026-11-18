-- Banco criado antes de 17/11/2026: funções de análise por filtro (a API só faz SELECT nelas).
-- Uso: docker compose exec -T postgres psql -U mq3 -d mq3 < applications/db/migracoes/2026-11-17-funcoes-de-analise.sql

-- Análise por filtros. Uma view não recebe parâmetros, então os agregados que dependem dos filtros da tela
-- (casos, participantes, janela e simulador) são funções: a API só faz SELECT e esta é a única fonte da conta.
-- p_casos e p_participantes nulos significam todos; rodadas sem caso ou participante ficam de fora.
-- p_janela: 'arquivo' (tudo) ou 'sopro' (só a janela de sopro).

-- Percentis 5, 25, 50, 75 e 95 e média de cada sensor, por caso (boxplot).
CREATE OR REPLACE FUNCTION f_distribuicao(p_casos text[], p_participantes text[], p_janela text, p_simulador boolean)
RETURNS TABLE (
    caso text,
    n bigint,
    mq3_p5 double precision,
    mq3_p25 double precision,
    mq3_p50 double precision,
    mq3_p75 double precision,
    mq3_p95 double precision,
    mq3_media double precision,
    mq135_p5 double precision,
    mq135_p25 double precision,
    mq135_p50 double precision,
    mq135_p75 double precision,
    mq135_p95 double precision,
    mq135_media double precision,
    umid_p5 double precision,
    umid_p25 double precision,
    umid_p50 double precision,
    umid_p75 double precision,
    umid_p95 double precision,
    umid_media double precision
) LANGUAGE sql STABLE AS $$
    SELECT caso, count(*),
           percentile_cont(0.05) WITHIN GROUP (ORDER BY mq3_raw) AS mq3_p5,
           percentile_cont(0.25) WITHIN GROUP (ORDER BY mq3_raw) AS mq3_p25,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY mq3_raw) AS mq3_p50,
           percentile_cont(0.75) WITHIN GROUP (ORDER BY mq3_raw) AS mq3_p75,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY mq3_raw) AS mq3_p95,
           avg(mq3_raw)::double precision AS mq3_media,
           percentile_cont(0.05) WITHIN GROUP (ORDER BY mq135_raw) AS mq135_p5,
           percentile_cont(0.25) WITHIN GROUP (ORDER BY mq135_raw) AS mq135_p25,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY mq135_raw) AS mq135_p50,
           percentile_cont(0.75) WITHIN GROUP (ORDER BY mq135_raw) AS mq135_p75,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY mq135_raw) AS mq135_p95,
           avg(mq135_raw)::double precision AS mq135_media,
           percentile_cont(0.05) WITHIN GROUP (ORDER BY humidity_pct) AS umid_p5,
           percentile_cont(0.25) WITHIN GROUP (ORDER BY humidity_pct) AS umid_p25,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY humidity_pct) AS umid_p50,
           percentile_cont(0.75) WITHIN GROUP (ORDER BY humidity_pct) AS umid_p75,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY humidity_pct) AS umid_p95,
           avg(humidity_pct)::double precision AS umid_media
    FROM v_leituras
    WHERE (p_janela = 'arquivo' OR em_sopro)
      AND caso IS NOT NULL AND (p_casos IS NULL OR caso = ANY (p_casos))
      AND participante IS NOT NULL AND (p_participantes IS NULL OR participante = ANY (p_participantes))
      AND (coalesce(origem, '') <> 'simulador' OR p_simulador)
    GROUP BY caso
    ORDER BY caso
$$;

-- Diferença (%) da média de cada caso em relação à do ambiente ('clean'). O ambiente entra no cálculo
-- mesmo fora do filtro de casos: ele é a referência.
CREATE OR REPLACE FUNCTION f_heatmap(p_casos text[], p_participantes text[], p_janela text, p_simulador boolean)
RETURNS TABLE (caso text, mq3 double precision, mq135 double precision, umid double precision)
LANGUAGE sql STABLE AS $$
    WITH medias AS (
        SELECT caso, avg(mq3_raw) AS mq3, avg(mq135_raw) AS mq135, avg(humidity_pct) AS umid
        FROM v_leituras
        WHERE (p_janela = 'arquivo' OR em_sopro)
          AND caso IS NOT NULL
          AND participante IS NOT NULL AND (p_participantes IS NULL OR participante = ANY (p_participantes))
          AND (coalesce(origem, '') <> 'simulador' OR p_simulador)
        GROUP BY caso)
    SELECT m.caso,
           ((m.mq3 / nullif(b.mq3, 0) - 1) * 100)::double precision,
           ((m.mq135 / nullif(b.mq135, 0) - 1) * 100)::double precision,
           ((m.umid / nullif(b.umid, 0) - 1) * 100)::double precision
    FROM medias m
    CROSS JOIN (SELECT * FROM medias WHERE caso = 'clean') b
    WHERE m.caso <> 'clean' AND (p_casos IS NULL OR m.caso = ANY (p_casos))
    ORDER BY m.caso
$$;

-- Até p_limite leituras por caso (MQ-3 × MQ-135), sorteadas sempre do mesmo jeito.
CREATE OR REPLACE FUNCTION f_dispersao(p_casos text[], p_participantes text[], p_janela text, p_simulador boolean, p_limite integer)
RETURNS TABLE (caso text, mq3_raw integer, mq135_raw integer)
LANGUAGE sql STABLE AS $$
    SELECT t.caso, t.mq3_raw, t.mq135_raw
    FROM (
        SELECT caso, mq3_raw, mq135_raw,
               row_number() OVER (PARTITION BY caso ORDER BY md5(rodada_id::text || amostra::text)) AS n
        FROM v_leituras
        WHERE (p_janela = 'arquivo' OR em_sopro)
          AND caso IS NOT NULL AND (p_casos IS NULL OR caso = ANY (p_casos))
          AND participante IS NOT NULL AND (p_participantes IS NULL OR participante = ANY (p_participantes))
          AND (coalesce(origem, '') <> 'simulador' OR p_simulador)
          AND mq3_raw IS NOT NULL AND mq135_raw IS NOT NULL) t
    WHERE t.n <= p_limite
    ORDER BY t.caso, t.n
$$;
