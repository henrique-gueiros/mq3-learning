# AGENTS.md — applications/

Coleta (`coleta/`), banco (`db/`), API (`api/`) e a tela (`frontend/`, com regras
próprias). Uso em `applications/README.md`. Vale junto com o `AGENTS.md` da raiz.

- Toda escrita no banco é idempotente: repetir uma mensagem MQTT não duplica (chave rodada + amostra; eventos únicos).
- A lógica de análise fica nas **views e funções** (`v_*`, `f_*`) de `db/01-schema.sql`; as funções existem para os agregados que dependem dos filtros da tela. API e gráficos só fazem `SELECT`. Mudança de view ou função em banco já criado vai também como migração em `db/migracoes/`.
- A API é só leitura e recebe filtros como parâmetros do psycopg, nunca texto colado no SQL.
- O formato das mensagens MQTT é o de `coleta/mensagens.py`; mudar o formato exige mudar ponte, simulador, ingestor e `frontend/src/aovivo/mensagens.ts` juntos.
- Simulador e testes gravam rodadas com `origem = 'simulador'`, que a análise exclui por padrão.
- O Mosquitto aceita conexões sem senha: só na rede local da coleta.
- Testes: `python -m pytest` (de `applications/`). Os de banco precisam de um Postgres descartável:
  `docker run --rm -d --name pg-teste -e POSTGRES_PASSWORD=t -p 55432:5432 postgres:16` e
  `PG_DSN=postgresql://postgres:t@localhost:55432/postgres python -m pytest`.
- O dashboard do Grafana (`grafana/`) sai na Etapa 7 do plano da tela; até lá, `dashboards/coleta.json` é gerado por `grafana/montar_dashboard.py`, nunca editado à mão.
