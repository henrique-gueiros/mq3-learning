#!/bin/sh
# Cria o usuário só leitura (leitor) que a API usa para consultar o banco.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v senha="$LEITOR_PG_SENHA" <<'SQL'
CREATE ROLE leitor LOGIN PASSWORD :'senha';
GRANT USAGE ON SCHEMA public TO leitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO leitor;
SQL
