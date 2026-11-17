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

ml/ (offline): CSVs + attempts.csv ──▶ validação ──▶ features ──▶ treino ──▶ ml/models/sob_efeito.joblib
services/ (fluxo paralelo): worker + servidor do modelo ──▶ mq3/<placa>/resultado
```

A ESP32 ainda não publica no MQTT: hoje a ponte serial (ou o simulador) publica no
lugar dela, com as mesmas mensagens. O dashboard antigo do Grafana
(`applications/grafana/`) está sendo substituído pela tela React.

## Pastas

| Pasta | O quê | Como usar |
| --- | --- | --- |
| `esp32-esp8266/` | Firmware (PlatformIO): lê os 3 sensores ~1×/s e grava CSV por sessão. Mantido por outro integrante | `esp32-esp8266/README.md` |
| `applications/coleta/` | Ponte serial, ingestor (MQTT → Postgres), simulador, importador e lote de CSVs | `applications/README.md` |
| `applications/db/` | Esquema e views do Postgres (`01-schema.sql`), usuário só leitura, migrações | — |
| `applications/api/` | API somente leitura com os dados dos gráficos de análise | `applications/README.md`, `/api/docs` |
| `applications/frontend/` | Tela única (React): ao vivo + análise; design system Vercel/Geist | `applications/frontend/README.md` |
| `applications/grafana/`, `pdc/` | Dashboard antigo e túnel do Grafana Cloud (saem na Etapa 7 do plano da tela) | `applications/grafana/README.md` |
| `ml/` | Pipeline de ML: validação, features, separação por participante, treino, inferência | `ml/README.md` |
| `services/` | Fluxo paralelo: broker, banco, worker e servidor do modelo | `services/README.md` |
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

### MQTT — coleta (`applications/`)

Formato em `applications/coleta/mensagens.py`; JSON, QoS 1, `null` para ausentes.

| Tópico | Quem publica | Conteúdo |
| --- | --- | --- |
| `mq3/<placa>/rodada` | ponte, simulador (depois a ESP32) | `rodada_id`, caso, participante, início, arquivo, origem; **retida** |
| `mq3/<placa>/leituras` | idem | uma leitura, com os campos do CSV e o `rodada_id` |
| `mq3/<placa>/eventos` | idem | `sopro_inicio`, `sopro_fim`, `rodada_fim` (com `t_ms`) |
| `mq3/<placa>/status` | idem | `{"estado": "online" \| "offline"}`; **retida**; `offline` é o last will |

O ingestor grava sem duplicar (chave rodada + amostra). O navegador assina os mesmos
tópicos por WebSocket.

### MQTT — servidor do modelo (`services/`)

Formato em `services/mq3mqtt/messages.py`. Mesmos `leituras`/`eventos`/`status`, mais
`mq3/<placa>/sopro_pronto` (worker → servidor do modelo) e `mq3/<placa>/resultado`
(`sem_modelo` até existir `ml/models/sob_efeito.joblib`; depois classe e
probabilidades). Unificar os dois contratos é decisão da equipe.

### Banco (`applications/db/01-schema.sql`)

Tabelas `rodadas`, `leituras`, `eventos`. Views, que concentram a lógica dos gráficos:

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
| Grafana local (perfil `local`) | 127.0.0.1:3000 | idem |

O Compose de `services/` usa as mesmas portas: as duas stacks não sobem juntas.

Ambiente Python: um só, `ml/.venv` (criação em `ml/README.md`), com
`ml/requirements.txt`, `applications/coleta/requirements.txt` e
`applications/api/requirements.txt`. O scikit-learn é fixo em 1.6.1: o `.joblib` só
abre na versão que o gravou. Frontend: Node + npm em `applications/frontend`.
