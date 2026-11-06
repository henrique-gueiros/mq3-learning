#!/bin/sh
# Cria o usuário só leitura que o Grafana Cloud usa para consultar o banco.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v senha="$GRAFANA_PG_SENHA" <<'SQL'
CREATE ROLE grafana_leitor LOGIN PASSWORD :'senha';
GRANT USAGE ON SCHEMA public TO grafana_leitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_leitor;
SQL
