# Arquitetura — Sopro Seguro

Mapa do sistema: as peças, como os dados andam entre elas, os contratos e onde cada
coisa mora. Regras de trabalho ficam no `AGENTS.md`; estado e próximos passos, em
`docs/roadmap.md`.

## Visão geral

```text
                 ┌──────────── coleta (notebook) ────────────┐
ESP32 ──USB──▶ ponte serial ──▶ CSV de sessão (ml/data/raw/sessions/)
 MQ-3 · MQ-135 · DHT11   │      └▶ linha em ml/data/raw/attempts.csv
                          │
simulador (CSV real) ─────┤ MQTT  mq3/<placa>/{rodada,leituras,eventos,status}
                          ▼
                     Mosquitto ──▶ ingestor ──▶ PostgreSQL (tabelas + views)
                    1883 · ws 9001                    │
                          │                           ▼
                          │                   API FastAPI (somente leitura, :8000)
                          ▼                           │
                   tela React (applications/frontend): ao vivo por /mqtt, análise por /api
                          aba Modelo ──POST /modelo/classificar──▶ classificador HTTP (:8010)
                                                                    lê ml/models/sob_efeito.joblib
                     Mosquitto ──sopro_fim──▶ servidor do modelo (mesmo container :8010)
                          ▲                   lê a rodada no PostgreSQL, grava em resultados
                          └──── mq3/<placa>/resultado ◀┘

ml/ (offline ou Airflow): CSVs + attempts.csv ──▶ validação ──▶ features ──▶ treino ──▶ ml/models/sob_efeito.joblib
```

O DAG `dataset_para_treino` (http://localhost:8088; registra no MLflow, http://localhost:5050) lê as
rodadas encerradas no Postgres, grava sessão e tentativas que ainda não existem em
`ml/data/raw/` e roda a mesma preparação de `python -m src.cli prepare`. O arquivo
`ml/data/processed/disponivel.json` marca o dataset como pronto para o treino. CSV de
sessão que já existe não é reescrito. Rodada com `origem = 'simulador'` fica de fora.

A ESP32 ainda não publica no MQTT: hoje a ponte serial (ou o simulador) publica no
lugar dela, com as mesmas mensagens. Quem visita o sistema usa a tela React
(http://localhost:8080). O Grafana foi removido em 24/11/2026; em 17/11 os
números da tela tinham batido com os painéis dele.

## Pastas

| Pasta | O quê | Como usar |
| --- | --- | --- |
| `esp32-esp8266/` | Firmware (PlatformIO): lê os 3 sensores ~1×/s e grava CSV por sessão. Mantido por outro integrante | `esp32-esp8266/README.md` |
| `applications/coleta/` | Ponte serial, ingestor (MQTT → Postgres), simulador, importador e lote de CSVs | `applications/README.md` |
| `applications/db/` | Esquema e views do Postgres (`01-schema.sql`), usuário só leitura, migrações | — |
| `applications/api/` | API somente leitura com os dados dos gráficos de análise | `applications/README.md`, `/api/docs` |
| `applications/frontend/` | Tela única (React): ao vivo + análise; design system Vercel/Geist | `applications/frontend/README.md` |
| `ml/` | Pipeline de ML: validação, features, separação por participante, treino, inferência | `ml/README.md` |
| `services/` | Servidor do modelo: ao vivo (MQTT + banco da coleta) e HTTP da aba Modelo | `services/README.md` |
| `docs/` | Requisitos das disciplinas, decisões de ML (PDF), roadmap, planos (`superpowers/`) | — |
| `schematics/` | Esquemático e foto da montagem | — |

## Contratos

### Sensores e CSV de sessão

ESP32 (`esp32dev`): MQ-3 no GPIO 34, MQ-135 no GPIO 35, DHT11 no GPIO 4. O ADC satura
perto de 3,1 V (leituras altas dos MQ ficam achatadas). O CSV tem 9, 11 ou 13 colunas
conforme a versão do firmware; todas as peças aceitam os três formatos.

| Coluna | Uso |
| --- | --- |
| `t_ms` | ms desde a partida da placa (obrigatório) |
| `mq3_raw`, `mq135_raw`, `humidity_pct` | Leituras usadas nas features. O DHT11 fica vazio nos primeiros segundos |
| `temperature_c` | Gravada, fora das features (não distingue hálito de ambiente) |
| `amostra`, `ppm`, `mq135_mv`, `alcool` | Calculados ou contados pelo firmware: nunca rótulo nem feature |

### `ml/data/raw/attempts.csv`

Uma linha por sopro (modelo em `ml/templates/attempts_template.csv`): `attempt_id`,
`session_file`, `participant_id`, `condition`, `blow_start_s` e, opcionais,
`blow_end_s`, `reference_mg_l`, `notes`. O rótulo vem da `condition`:

| Condição | Classe |
| --- | --- |
| `clean`, `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash` | `sem_efeito` |
| `drink` | `sob_efeito` |

Condições novas entram em `CONDITIONS` (`ml/src/data_validation.py`). Recorte de cada
sopro (`assign_phases`): 15 s antes, o sopro (5 s sem `blow_end_s`) e 30 s depois;
dois sopros da mesma sessão precisam de ~50 s de intervalo. Features em `ml/src/features.py`.

### MQTT (contrato único)

Formato em `applications/coleta/mensagens.py`; JSON, QoS 1, `null` para ausentes.

| Tópico | Quem publica | Conteúdo |
| --- | --- | --- |
| `mq3/<placa>/rodada` | ESP32, ponte, simulador | `rodada_id`, caso, participante, início, arquivo, origem; **retida** |
| `mq3/<placa>/leituras` | idem | uma leitura, com os campos do CSV e o `rodada_id` |
| `mq3/<placa>/eventos` | idem | `sopro_inicio`, `sopro_fim`, `rodada_fim` (com `t_ms`) |
| `mq3/<placa>/status` | idem | `{"estado": "online" \| "offline"}`; **retida**; `offline` é o last will |
| `mq3/<placa>/resultado` | servidor do modelo | `rodada_id`, `t_ms` do fim, `sessao`, `attempt_id`, `status`, `prediction`, `prob_sem_efeito`, `prob_sob_efeito`, `detalhe` |

O ingestor grava sem duplicar (chave rodada + amostra). O navegador assina os mesmos
tópicos por WebSocket.

O servidor do modelo (`services/mq3mqtt/ao_vivo.py`) assina `eventos`. A cada
`sopro_fim`, espera 35 s (a janela de 30 s depois do sopro usada no treino, mais
folga), lê a rodada no Postgres, recorta e classifica com o mesmo código de
`ml/src/inference.py`, grava em `resultados` e publica `resultado`. Sem
`ml/models/sob_efeito.joblib` o `status` é `sem_modelo` e a classe fica vazia.
O simulador publica `sopro_fim` 5 s depois de cada início (`--duracao`).

A aba Ao vivo assina `resultado`: o card "Modelo de ML" mostra a classe do último
sopro da rodada, as probabilidades e "Alerta de detecção." quando `sob_efeito`
(`applications/frontend/src/aovivo/componentes/ResultadoAoVivo.tsx`). O serviço
`alerta` (`services/mq3mqtt/alerta.py`) manda a mesma detecção pelo Telegram quando
`TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` estão no `.env`; sem eles, só registra no log.

A aba Modelo da tela não passa pelo banco. Ela faz `POST /modelo/classificar`
com um recorte de sopro (leituras e o instante do sopro) e recebe o mesmo corpo
do `resultado`. No Compose da raiz o serviço é o container `model` (porta 8010).
O recorte de demonstração não é gravado.

### Banco (`applications/db/01-schema.sql`)

Tabelas `rodadas`, `leituras`, `eventos`, `resultados`. Views, que concentram a lógica dos gráficos:

| View | O quê |
| --- | --- |
| `v_janelas_sopro` | cada sopro com o fim (primeiro `sopro_fim` antes do próximo, ou 5 s) |
| `v_leituras` | leituras + rodada, `tempo_s`, `em_sopro` (sopro até +30 s) e `ppm` (só para gráficos) |
| `v_sopros` | por sopro: base (mediana dos 15 s antes), pico e subida |
| `v_media_rodada` | média e pico por rodada, no arquivo e na janela de sopro |
| `v_rodadas_sem_sopro` | rodadas sem sopro marcado (fora do simulador) |

Rodadas com `origem = 'simulador'` ficam fora da análise por padrão.

## Execução

| Serviço | Porta (host) | Onde |
| --- | --- | --- |
| Mosquitto | 1883 (MQTT), 127.0.0.1:9001 (WebSocket) | `docker-compose.yml` |
| PostgreSQL | 127.0.0.1:5432 | idem |
| API | 127.0.0.1:8000 | idem |
| Tela (nginx: serve o build e encaminha `/api` e `/mqtt`) | 127.0.0.1:8080 | idem (`applications/frontend/Dockerfile`) |
| Tela (dev) | 5173 | `npm run dev` em `applications/frontend` (usa 8000 e 9001 do host) |
| Airflow | 127.0.0.1:8088 | idem; DAG `dataset_para_treino` |
| MLflow | 127.0.0.1:5050 (contêiner: 5000) | idem; SQLite e artefatos no volume `mlflow-dados` |
| Servidor do modelo | 127.0.0.1:8010 | idem (`services/Dockerfile.model`) |

Tudo sobe com `docker compose up -d --build`. A rede padrão tem IPv6 (`fd00:5050:5a::/64`); o Mosquitto escuta em IPv4 e IPv6.

Ambiente Python: um só, `ml/.venv` (criação em `ml/README.md`), com
`ml/requirements.txt`, `applications/coleta/requirements.txt` e
`applications/api/requirements.txt`. O scikit-learn é fixo em 1.6.1: o `.joblib` só
abre na versão que o gravou. Frontend: Node + npm em `applications/frontend`.
