-- Banco da coleta: rodadas, leituras e eventos, mais as views usadas pelo Grafana.
-- As janelas seguem applications/ml/src/features.py: 15 s antes do sopro (linha de base pela
-- mediana), o sopro (até sopro_fim ou 5 s) e 30 s depois.
-- ppm e alcool são calculados pelo firmware. O alcool fica fora de todas as views; o ppm aparece só
-- em v_leituras, para comparar casos nos gráficos, e nunca entra em médias, subidas, rótulos ou features.

CREATE TABLE rodadas (
    id             uuid PRIMARY KEY,
    placa          text NOT NULL,
    caso           text,
    participante   text,
    inicio         timestamptz,
    fim            timestamptz,
    arquivo_sessao text,
    origem         text CHECK (origem IN ('ponte', 'importador', 'simulador')),
    sha256         text UNIQUE,
    notas          text
);

CREATE TABLE leituras (
    rodada_id     uuid NOT NULL REFERENCES rodadas (id),
    amostra       integer NOT NULL,
    t_ms          bigint NOT NULL,
    mq3_raw       integer NOT NULL,
    ppm           real,
    mq135_raw     integer,
    mq135_mv      integer,
    temperature_c real,
    humidity_pct  real,
    alcool        smallint,
    recebido_em   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (rodada_id, amostra)
);

CREATE TABLE eventos (
    rodada_id uuid NOT NULL REFERENCES rodadas (id),
    tipo      text NOT NULL CHECK (tipo IN ('sopro_inicio', 'sopro_fim', 'rodada_fim')),
    t_ms      bigint NOT NULL,
    UNIQUE (rodada_id, tipo, t_ms)
);

-- Cada sopro com o seu fim: o primeiro sopro_fim antes do próximo sopro, ou 5 s.
CREATE VIEW v_janelas_sopro AS
WITH inicios AS (
    SELECT rodada_id,
           t_ms AS inicio_ms,
           row_number() OVER (PARTITION BY rodada_id ORDER BY t_ms) AS n,
           lead(t_ms) OVER (PARTITION BY rodada_id ORDER BY t_ms) AS proximo_ms
    FROM eventos
    WHERE tipo = 'sopro_inicio'
)
SELECT i.rodada_id,
       i.n,
       i.inicio_ms,
       coalesce(
           (SELECT min(f.t_ms)
            FROM eventos f
            WHERE f.rodada_id = i.rodada_id
              AND f.tipo = 'sopro_fim'
              AND f.t_ms > i.inicio_ms
              AND (i.proximo_ms IS NULL OR f.t_ms < i.proximo_ms)),
           i.inicio_ms + 5000
       ) AS fim_ms
FROM inicios i;

CREATE VIEW v_leituras AS
SELECT l.rodada_id,
       l.amostra,
       l.t_ms,
       ((l.t_ms - min(l.t_ms) OVER rodada) / 1000.0)::double precision AS tempo_s,
       r.inicio + (l.t_ms - min(l.t_ms) OVER rodada) * interval '1 millisecond' AS ts,
       l.mq3_raw,
       l.mq135_raw,
       l.temperature_c,
       l.humidity_pct,
       r.placa,
       r.caso,
       r.participante,
       r.origem,
       EXISTS (
           SELECT 1
           FROM v_janelas_sopro s
           WHERE s.rodada_id = l.rodada_id
             AND l.t_ms BETWEEN s.inicio_ms AND s.fim_ms + 30000
       ) AS em_sopro,
       l.ppm
FROM leituras l
JOIN rodadas r ON r.id = l.rodada_id
WINDOW rodada AS (PARTITION BY l.rodada_id);

-- Um ponto por sopro: linha de base (mediana dos 15 s antes), pico e subida.
CREATE VIEW v_sopros AS
SELECT s.rodada_id,
       r.caso,
       r.participante,
       r.origem,
       s.n,
       s.inicio_ms,
       s.fim_ms,
       b.base_mq3_raw,
       b.base_mq135_raw,
       b.base_humidity_pct,
       b.base_temperature_c,
       p.pico_mq3_raw,
       p.pico_mq135_raw,
       p.pico_humidity_pct,
       p.pico_temperature_c,
       p.pico_mq3_raw - b.base_mq3_raw AS subida_mq3_raw,
       p.pico_mq135_raw - b.base_mq135_raw AS subida_mq135_raw,
       p.pico_humidity_pct - b.base_humidity_pct AS subida_humidity_pct,
       p.pico_temperature_c - b.base_temperature_c AS subida_temperature_c
FROM v_janelas_sopro s
JOIN rodadas r ON r.id = s.rodada_id
LEFT JOIN LATERAL (
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY l.mq3_raw) AS base_mq3_raw,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY l.mq135_raw) AS base_mq135_raw,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY l.humidity_pct) AS base_humidity_pct,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY l.temperature_c) AS base_temperature_c
    FROM leituras l
    WHERE l.rodada_id = s.rodada_id
      AND l.t_ms >= s.inicio_ms - 15000
      AND l.t_ms < s.inicio_ms
) b ON true
LEFT JOIN LATERAL (
    SELECT max(l.mq3_raw) AS pico_mq3_raw,
           max(l.mq135_raw) AS pico_mq135_raw,
           max(l.humidity_pct) AS pico_humidity_pct,
           max(l.temperature_c) AS pico_temperature_c
    FROM leituras l
    WHERE l.rodada_id = s.rodada_id
      AND l.t_ms BETWEEN s.inicio_ms AND s.fim_ms + 30000
) p ON true;

-- Média e pico de cada rodada no arquivo inteiro e só nas janelas de sopro.
CREATE VIEW v_media_rodada AS
SELECT r.id AS rodada_id,
       r.caso,
       r.participante,
       r.origem,
       j.janela,
       count(l.amostra) AS n_leituras,
       avg(l.mq3_raw)::double precision AS media_mq3_raw,
       avg(l.mq135_raw)::double precision AS media_mq135_raw,
       avg(l.humidity_pct)::double precision AS media_humidity_pct,
       avg(l.temperature_c)::double precision AS media_temperature_c,
       max(l.mq3_raw) AS pico_mq3_raw,
       max(l.mq135_raw) AS pico_mq135_raw,
       max(l.humidity_pct) AS pico_humidity_pct,
       max(l.temperature_c) AS pico_temperature_c
FROM rodadas r
CROSS JOIN (VALUES ('arquivo'), ('sopro')) AS j (janela)
LEFT JOIN v_leituras l
       ON l.rodada_id = r.id
      AND (j.janela = 'arquivo' OR l.em_sopro)
GROUP BY r.id, r.caso, r.participante, r.origem, j.janela;

CREATE VIEW v_rodadas_sem_sopro AS
SELECT r.id AS rodada_id, r.caso, r.participante, r.arquivo_sessao, r.inicio
FROM rodadas r
WHERE r.origem IS DISTINCT FROM 'simulador'
  AND NOT EXISTS (
      SELECT 1 FROM eventos e WHERE e.rodada_id = r.id AND e.tipo = 'sopro_inicio'
  );

-- Análise por filtros. Uma view não recebe parâmetros, então os agregados que dependem dos filtros da tela
-- (casos, participantes, janela e simulador) são funções: a API só faz SELECT e esta é a única fonte da conta.
-- p_casos e p_participantes nulos significam todos; rodadas sem caso ou participante ficam de fora.
-- p_janela: 'arquivo' (tudo) ou 'sopro' (só a janela de sopro).

-- Percentis 5, 25, 50, 75 e 95 e média de cada sensor, por caso (boxplot).
CREATE FUNCTION f_distribuicao(p_casos text[], p_participantes text[], p_janela text, p_simulador boolean)
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
CREATE FUNCTION f_heatmap(p_casos text[], p_participantes text[], p_janela text, p_simulador boolean)
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
CREATE FUNCTION f_dispersao(p_casos text[], p_participantes text[], p_janela text, p_simulador boolean, p_limite integer)
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
