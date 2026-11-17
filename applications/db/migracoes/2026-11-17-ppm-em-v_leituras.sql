-- Banco criado antes de 17/11/2026: expõe o ppm em v_leituras (só para gráficos).
-- Uso: docker compose exec -T postgres psql -U mq3 -d mq3 < applications/db/migracoes/2026-11-17-ppm-em-v_leituras.sql
CREATE OR REPLACE VIEW v_leituras AS
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
