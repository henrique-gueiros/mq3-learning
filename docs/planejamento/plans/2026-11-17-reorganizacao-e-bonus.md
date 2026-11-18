# Plano — Reorganização do repositório, achados do review e bônus

Branch: `reorganiza-estrutura` (a partir da `main` em `362f8df`). **Atualizado a cada passo
concluído**: marque a etapa, anote o commit e mova o que sobrou para "Pendente". Quem pegar uma
etapa deve conseguir trabalhar só com este arquivo, o código e os READMEs.

Regras que valem para todas as etapas (detalhes em `AGENTS.md`):

- Commits em português, **sem** linha `Co-Authored-By` (regra da equipe), direto na branch; push só quando a equipe pedir.
- Teste primeiro: o teste que falha, depois o código. Rodar tudo no fim de cada etapa (comandos em "Como verificar").
- Não apagar nada que a equipe não autorizou (Grafana, `services/`, firmware).

## Contexto

O professor pede, no critério "GitHub (Organização)", esta estrutura (cada item é obrigatório):

```text
README.md      descrição, requisitos, instruções
/docs          relatório em PDF (CSBC – ABNT2)
/applications  código backend + frontend + outros
/esp32-esp8266 firmware dos módulos (FreeRTOS)
/schematics    diagramas eletrônicos (Tinkercad, Cirkit, Fritzing, Wokwi, KiCad...)
```

Dica do professor: usar o GitHub Projects para as tarefas. Datas: relatório e repositório em
**03/12/2026**, apresentação em **12/12/2026**. Bônus de até 10 pts por funcionalidades extras
(alertas por e-mail ou mensageiro, comunicação em IPv6).

## Andamento

| Etapa | Situação | Commit |
| --- | --- | --- |
| 1. Reorganizar pastas (`ml/`, `services/`, CSVs, `docs/`) | **feita** | `6b66af7` |
| 2. Corrigir os achados do review | **parcial** (4 de 7) | `66b7995` |
| 3. README no modelo do professor e `schematics/README.md` | **feita** | `db3feb8` |
| 4. Achados do review que sobraram (A, B, C) | a fazer | |
| 5. Firmware: FreeRTOS e Wi-Fi/MQTT (com o Artur) | a fazer | |
| 6. Esquemático: arquivo-fonte (com quem desenhou) | a fazer | |
| 7. Relatório CSBC em `docs/relatorio/` | a fazer (vence 03/12) | |
| 8. GitHub Projects e organização do repositório | a fazer (com o Henrique, dono do repo) | |
| 9. Unificar `services/` com `applications/` | a fazer (aprovado em 05/11 para depois da coleta) | |
| 10. Remover o Grafana (Etapa 7 do plano da tela) | a fazer; **perguntar à equipe antes** | |
| 11. Bônus: alertas (Telegram + e-mail) | a fazer | |
| 12. Bônus: IPv6 no Compose | a fazer | |
| 13. Merge na `main` e aviso à equipe | a fazer, depois das etapas 4 a 6 | |

## Feito

### Etapa 1 — reorganização (`6b66af7`)

- `ml/` → `applications/ml/`, `services/` → `applications/services/` (`git mv`, histórico preservado).
- 23 CSVs de `esp32-esp8266/` → `esp32-esp8266/leituras/`. O filtro de monitor do PlatformIO
  (`esp32-esp8266/monitor/filter_leituras.py`) grava agora em `leituras/`.
- `docs/` em subpastas: `requisitos/` (PDFs e planilha), `relatorio/` (README), `imagens/`
  (diagrama e `prints/`), `planejamento/` (era `superpowers/`) e `roadmap.md`.
- Caminhos ajustados em `applications/coleta/` (`arquivos.py`, `casos.py`, `lote.py`, `simulador.py`,
  `importador.py`, `ponte.py`), nos testes (`parents[...]`), em `applications/services/mq3mqtt/config.py`,
  no `schema.sql` (comentário) e em todos os `.md` (regex trocando `ml/` e `services/` por
  `applications/ml/` e `applications/services/`; `docs/superpowers/` por `docs/planejamento/`).
- O `.venv` do `applications/ml/` foi consertado (`sed` nos scripts de `bin/`); **quem tem um `.venv` antigo deve
  recriá-lo**: `python3 -m venv applications/ml/.venv && pip install -r applications/ml/requirements.txt -r applications/coleta/requirements.txt -r applications/api/requirements.txt -r applications/services/requirements.txt`.
- CI (`.github/workflows/ci.yml`): caminhos novos e job que também roda `applications/services`.

### Etapa 2 — achados do review corrigidos (`66b7995`)

| Achado | Correção |
| --- | --- |
| API abria uma conexão por requisição | `psycopg_pool.ConnectionPool` criado no `lifespan` (`applications/api/app.py`); `psycopg[binary,pool]` no requirements |
| `id::text = %(id)s` ignorava índices | `leituras_rodada` valida o id como UUID (404 para id inválido) e compara `= %(id)s::uuid`; teste novo `test_id_que_nao_e_uuid_da_404_em_vez_de_erro` |
| Tela de análise nunca atualizava | `refetchInterval` de 15 s em `useFiltros` e `useResumo` (`applications/frontend/src/api/consultas.ts`) |
| CI não rodava `services/` | job novo (ver etapa 1) |

### Etapa 3 — README (`db3feb8`)

README da raiz reescrito (descrição, equipe, como funciona, requisitos, como rodar, estrutura no formato
do professor, limitações). O tutorial antigo de coleta/treino/MQTT foi para `docs/guia-coleta-e-ml.md`.
`schematics/README.md` com tabela de pinos.

## Como verificar (rodar no fim de cada etapa)

```bash
# Python (de applications/), com um Postgres descartável:
docker run --rm -d --name pg-teste -e POSTGRES_PASSWORD=t -p 55432:5432 postgres:16
cd applications && PG_DSN=postgresql://postgres:t@localhost:55432/postgres ml/.venv/bin/python -m pytest -q   # esperado: 137 passed
(cd ml && ../ml/.venv/bin/python -m pytest -q)         # esperado: 37 passed
(cd services && ../ml/.venv/bin/python -m pytest -q)   # esperado: 6 passed
docker stop pg-teste
# Tela:
cd applications/frontend && npm test && npx tsc -b      # esperado: 188 passed
# Compose:
docker compose config -q && (cd applications/services && docker compose config -q)
```

## Pendente

### Etapa 4 — achados do review que sobraram

**A. Detector com referência fixa (`applications/frontend/src/aovivo/detector.ts`, linha ~159).** Na calibração,
`subiu(recentes, LIMIARES.referencia)` compara com umidade 55 %, MQ-3 900 e MQ-135 400. Carro úmido ou MQ-3
aquecendo dispara "Sopro detectado" falso e a tela fica em sopro/recuperando até 120 s.
Caminho sugerido: exigir que a subida venha *depois* de `minAmostrasBase` leituras de base (ou só usar a
referência quando a primeira leitura já estiver acima dela por mais de N segundos *e* a umidade subiu entre
leituras consecutivas); acrescentar teste em `detector.test.ts` com sessão úmida e MQ-3 quente. Os limiares
dependem de dados reais (roadmap, tarefa 3): rever junto com a análise exploratória.

**B. SQL de análise na API (`applications/api/consultas.py`).** Percentis, média relativa ao ambiente (heatmap) e
amostragem da dispersão estão como SQL na API e duplicados em `applications/grafana/montar_dashboard.py`,
contra a regra de `applications/AGENTS.md` ("a lógica de análise fica nas views"). Caminho: criar views em
`applications/db/01-schema.sql` (`v_distribuicao`, `v_heatmap`, `v_dispersao`), com migração em
`applications/db/migracoes/`; a API passa a fazer só `SELECT` com filtros; testes de views em
`applications/coleta/tests/test_banco.py`. A duplicação some quando o Grafana sair (etapa 10): então a prioridade é baixa
se a etapa 10 for aprovada.

**C. Ordem entre tópicos MQTT (`applications/frontend/src/aovivo/estado.ts`, linha ~88).** Leituras de uma rodada
nova que chegam antes da mensagem `rodada` dela são descartadas. Caminho: guardar essas leituras em `pendentes`
(como já é feito com eventos) e aplicá-las quando a `rodada` chegar ou depois de 2 s; teste em `estado.test.ts`.

### Etapa 5 — firmware (Artur mantém; `AGENTS.md` reserva o firmware a ele)

1. `esp32-esp8266/src/main.cpp` hoje é o laço do Arduino. O professor descreve "Firmware dos módulos (FreeRTOS)":
   separar em tarefas `xTaskCreate` (leitura dos sensores, gravação do CSV/LittleFS, LED e, depois, rede).
2. Wi-Fi + MQTT direto da ESP32 (biblioteca PubSubClient ou AsyncMqttClient): publicar em
   `mq3/<placa>/{rodada,leituras,eventos,status}` com os formatos de `applications/coleta/mensagens.py`; `status` com
   last will. Credenciais em arquivo não versionado (`secrets.h` no `.gitignore` de `esp32-esp8266/`).
3. Atualizar `esp32-esp8266/README.md`, `ARCHITECTURE.md` (diagrama) e `docs/imagens/diagrama-arquitetura.png`
   (a linha tracejada "futuro" vira cheia).
4. Se for feito, a ponte serial deixa de ser obrigatória; o `Dia de coleta` em `applications/README.md` muda.

### Etapa 6 — esquemático (`schematics/`)

Falta o arquivo-fonte do esquemático (Wokwi `diagram.json`, Fritzing `.fzz`, KiCad...) ou o link do projeto.
Quem desenhou acrescenta em `schematics/` e põe o link no `schematics/README.md`. Conferir se a ligação do MQ-3/MQ-135
(saída analógica de 5 V no ADC, que satura perto de 3,1 V) tem divisor de tensão e documentar o resultado.

### Etapa 7 — relatório (`docs/relatorio/`)

PDF no modelo CSBC/ABNT2, entrega 03/12. Conteúdo mínimo: introdução, arquitetura (usar `ARCHITECTURE.md` e o
diagrama), circuito (`schematics/`), coleta (casos, 12 CSVs válidos, limitações: sem participante por arquivo,
sopro contínuo), ML (decisões, validação por grupo, resultados quando houver modelo), dashboard/tela, bônus,
limitações e referências. A IA só revisa texto do relatório (regra do `AGENTS.md`); o texto é da equipe.

### Etapa 8 — organização no GitHub

- Dono do repositório (Henrique): criar o GitHub Projects (colunas A fazer / Fazendo / Feito) e abrir issues a partir
  das etapas deste plano.
- Conferir que todos os integrantes têm commits (hoje só LFPerylo, Artur-Dowsley e henrique-gueiros têm).
- Repositório público (já está). README com descrição, requisitos e instruções (feito na etapa 3).
- Atualizar o `Checkpoint Embarcados` / relatório com a nova estrutura de pastas.

### Etapa 9 — unificar `services/` e `applications/`

Aprovado em 05/11 para depois da coleta (memória do projeto). Plano: um contrato de mensagens (adotar o de
`applications/coleta/mensagens.py`), um ingestor, um Compose na raiz, trazer o servidor do modelo e o tópico
`resultado` para `applications/`, remover `applications/services/` ao final. Hoje as duas pilhas usam as mesmas
portas (1883/5432) e não sobem juntas; `applications/services/mq3mqtt/messages.py` ainda aceita só o CSV de 9
colunas. Pré-requisito: modelo treinado (`applications/ml/models/sob_efeito.joblib`, hoje inexistente).

### Etapa 10 — remover o Grafana

`applications/grafana/`, `applications/pdc/` e o serviço `grafana`/`pdc` do `docker-compose.yml`, depois de a
equipe aprovar. Detalhes na Etapa 7 de `docs/planejamento/plans/2026-11-17-frontend-react.md`. Atualizar
`ARCHITECTURE.md`, README e `applications/AGENTS.md`; apagar `applications/coleta/tests/test_dashboard.py`.

### Etapa 11 — bônus: alertas (Telegram + e-mail)

Serviço novo `applications/alertas/` no Compose, assinando o MQTT:

- **Eventos:** placa offline/online (`mq3/<placa>/status`, last will já existe); sopro detectado; resultado
  `sob_efeito` (`mq3/<placa>/resultado`, só quando houver modelo). O texto só diz "sob efeito" quando o modelo disser.
- **Canais:** Telegram (bot via BotFather, HTTP) e e-mail (SMTP; Mailpit local para a demonstração). Não usar WhatsApp.
- **Regras:** intervalo mínimo entre alertas do mesmo tipo (cooldown), sem dado pessoal na mensagem.
- **Credenciais** só no `.env` (documentar no `.env.example`, nunca versionar). A equipe cria o bot e a conta SMTP.
- **Testes:** canais falsos injetados, regras de cooldown e mapeamento evento → mensagem (TDD), sem rede.
- Documentar em `applications/README.md` e no relatório; mostrar na apresentação (celular recebendo ao vivo).

### Etapa 12 — bônus: IPv6

1. Rede do Compose com IPv6 (`networks: default: enable_ipv6: true`, sub-rede ULA `fd00:…/64`) e `ip6tables` do Docker ligado.
2. Mosquitto escutando em IPv6 (`listener 1883 ::` / `socket_domain ipv6` em `applications/mosquitto/mosquitto.conf`).
3. Ponte, ingestor e simulador conectando por endereço IPv6; tela e API acessíveis por `http://[::1]:8080`.
4. Evidências para o relatório: `curl -6`, `mosquitto_sub -h ::1 -t 'mq3/#'`, `ss -ltn | grep ::` e captura de pacotes.
5. ESP32 em IPv6 só se o firmware já publicar (etapa 5) e a rede da apresentação tiver IPv6: risco alto; extra.
6. Perguntar ao professor se IPv6 no notebook conta como "infraestrutura de comunicação em IPv6".

### Etapa 13 — merge

Quando as etapas 4 a 6 terminarem (ou a equipe decidir fechar antes): `git switch main && git merge reorganiza-estrutura`,
avisar a equipe para `git pull` e recriar o `applications/ml/.venv`; banco criado antes de 17/11 precisa das migrações de
`applications/db/migracoes/`.

## Limpeza do espaço de trabalho (não versionado)

- `Relatório progressão projeto.md` e `Copy of Checkpoint Embarcados.docx` estão soltos na raiz, sem versionar: decidir com a
  equipe (o relatório de progressão pode virar insumo de `docs/relatorio/`).
- `.claude/`, `.cursor/` e `.impeccable/` estão no `.gitignore` (configuração local de agentes).
