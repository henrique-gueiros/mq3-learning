# Servidor do modelo

Um processo, no container `model` do `docker-compose.yml` da raiz, com duas portas de entrada:

- **Ao vivo** (`mq3mqtt/ao_vivo.py`): assina `mq3/+/eventos`. A cada `sopro_fim`, espera 35 s (a janela de 30 s depois do sopro usada no treino, mais folga para as últimas leituras), lê a rodada no Postgres da coleta, recorta e classifica com o mesmo código de `ml/src/inference.py`, grava em `resultados` e publica em `mq3/<placa>/resultado`.
- **Aba Modelo** (`mq3mqtt/classificar_http.py`): `POST /modelo/classificar` na porta 8010. O corpo é um recorte de sopro; a resposta é o mesmo JSON do `resultado`. Não grava no banco.

O contrato das mensagens é o da coleta (`applications/coleta/mensagens.py`), descrito em `ARCHITECTURE.md`.

Sem `ml/models/sob_efeito.joblib` a resposta é `status: sem_modelo` e a classe fica vazia. Nenhuma classe é inventada.

## Resultado

```json
{
  "rodada_id": "…", "t_ms": 45000, "sessao": "leituras_3.csv", "attempt_id": "leituras_3@40s",
  "status": "classificado", "prediction": "sob_efeito",
  "prob_sem_efeito": 0.2, "prob_sob_efeito": 0.8, "detalhe": ""
}
```

`status`: `classificado`, `sem_modelo`, `sem_inicio` (chegou `sopro_fim` sem `sopro_inicio`) ou `sem_janela` (sem leituras úteis no recorte).

## Testes

De dentro de `services/`, com o ambiente do `ml/`:

```bash
source ../ml/.venv/bin/activate
PYTHONPATH=.:../ml python -m pytest
```

Os testes de banco rodam com `PG_DSN` definido (veja `tests/conftest.py`).

Banco criado antes de 24/11/2026 precisa da migração `applications/db/migracoes/2026-11-24-resultados-e-origem-placa.sql`.
