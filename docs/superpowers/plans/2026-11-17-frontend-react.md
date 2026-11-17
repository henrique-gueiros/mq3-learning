# Plano — Frontend React como tela única do MQ-3

Branch: `frontend-react`. Uma etapa por vez; cada uma termina com testes verdes e commit.

## Andamento

| Etapa | Situação | Commit |
| --- | --- | --- |
| 0. Ferramentas de design (skills + `DESIGN.md`) | feita | — (skills globais em `~/.claude/skills`) |
| 1. API somente leitura + WebSocket no Mosquitto | feita | `30f628e` |
| 2. Esqueleto do frontend e design system | feita | `fbb53ed` |
| 3. Seção "Ao vivo" e detector ambiente × sopro | a fazer | |
| 4. Seções de análise | a fazer | |
| 5. Animações e acabamento | a fazer | |
| 6. Compose e documentação | a fazer | |
| 7. Remoção do Grafana | a fazer | |

### Mudança depois da aprovação (17/11): calibração do detector

As 12 rodadas no banco não têm sopro marcado (vieram sem `attempts.csv`), então
`v_sopros` está vazio e não serve para os limiares iniciais. Além disso, a equipe
informou que nas sessões de bebida a pessoa soprou sem parar.

**Nova fonte dos limiares:** comparar as rodadas de ambiente (sem sopro) com as de
bebida inteiras (sopro contínuo). Medido em 17/11, primeiros 20 s × depois de 60 s:

| Caso | Umidade (%) | MQ-135 | PPM |
| --- | --- | --- | --- |
| ambiente (7) | 35–55, estável | 180–530 | ~0,4 |
| bebida (4) | 49–76 → 71–92 | 326–640 → 519–1063 | 0,40 → 0,87 numa delas |
| perfume (1) | 57 → 54 | ~1140 o tempo todo | 0,31 → 0,47 |

Isso apoia a regra do detector: umidade **e** gás sobem juntos no sopro, e o perfume
sobe o gás sem subir a umidade.

Duas rodadas de bebida já começam com umidade alta, então o detector precisa de uma
base de referência do ambiente quando a sessão começa no meio de um sopro.

A equipe ainda vai limpar os CSVs de bebida e perfume. Recomendação: marcar o trecho
válido (`blow_start_s`/`blow_end_s` no `attempts.csv`) em vez de editar o bruto. Um
CSV editado tem outro SHA-256 e duplicaria a rodada no banco.

## Contexto

Hoje a visualização da coleta é o dashboard do Grafana (`applications/grafana/`). Os gráficos e as variáveis dele estão bons, mas o visual está feio, e ele depende do PDC e do Grafana Cloud. A equipe quer uma **tela única** em React, dentro de `applications/`, para quem visita o projeto (checkpoint, Mostra TechDesign). Essa tela mostra:

1. a coleta **ao vivo**, com as leituras chegando da placa (hoje, da ponte serial ou do simulador) por MQTT;
2. os **gráficos de análise de todas as coletas**, os mesmos tipos e variáveis do Grafana, com um design novo e animado.

ML fica de fora por enquanto: nada de `resultado` nem de veredito na tela.

Decisões tomadas com o usuário:

- React, dentro de `applications/`.
- Design system **Vercel / Geist**, do awesome-design-md.
- Tema escuro por padrão, com troca para o claro.
- O Grafana fica até o React cobrir todos os painéis e sai na última etapa.

## Arquitetura

```
ESP32 / ponte / simulador ──MQTT──▶ Mosquitto ──▶ ingestor ──▶ PostgreSQL (views)
                                       │ ws:9001                        │
                                       ▼                                ▼
                         navegador (mqtt.js)  ◀── nginx ──▶  API FastAPI (somente leitura)
                                  └──────── frontend React (mesma origem) ────────┘
```

- **Ao vivo:** o navegador assina o Mosquitto por WebSocket. O nginx do frontend faz proxy de `/mqtt` → `mosquitto:9001` e de `/api` → `api:8000`. Tudo sai de uma porta só, sem CORS.
- **Análise:** uma API FastAPI fina roda as mesmas consultas do Grafana, com parâmetros e sem concatenar texto, usando um papel só de leitura.

## Como implementar: TDD

O TDD é recomendado aqui. Cada etapa segue vermelho → verde → refatorar: o teste é escrito primeiro, falha pelo motivo certo, e só então vem o código mínimo para passar. Um commit por ciclo concluído. A disciplina vale onde o comportamento é verificável:

| Camada | Teste primeiro com | Exemplos de casos escritos antes do código |
| --- | --- | --- |
| API (`applications/api`) | pytest + banco temporário (`integracao`) | filtro por caso; simulador excluído por padrão; janela `sopro` só pega `em_sopro`; heatmap sem `clean` devolve vazio; parâmetro inválido → 422 |
| Domínio do front (`src/dominio`, `src/graficos`, `src/aovivo`) | Vitest | detector (ambiente estável, deriva lenta, só gás, umidade+gás, volta à base); faixas de sopro; percentis → boxplot; ordem e cor dos casos; escala do heatmap; parser das mensagens MQTT; buffer circular |
| Componentes | Vitest + Testing Library | Stat mostra a variação em relação à base; card de estado troca de texto; estados de carregando, vazio e erro; filtros vão para a URL |
| Ponta a ponta | Playwright | com o simulador rodando, o gráfico ao vivo recebe pontos e o estado muda para "sopro detectado" |

O visual (cores, espaçamento, animação) não se testa por TDD. Ele é revisado com screenshots e com as skills de design na Etapa 5. Os gráficos ECharts são testados pelas funções que montam as `options`, não pelo canvas.

## Etapa 0 — Ferramentas de design (antes do código)

Feita: todas foram instaladas com `npx skills add <repo> -g -a claude-code -s <skill>` (globais, em `~/.claude/skills`). Referência das fontes:

| Skill | Comando |
| --- | --- |
| frontend-design | já instalada |
| vercel-react-best-practices + web-design-guidelines | `npx skills add vercel-labs/agent-skills` (escolher só essas duas) |
| Emil Kowalski (animações) | `npx skills@latest add emilkowalski/skills` |
| impeccable | `/plugin marketplace add pbakaus/impeccable` → `/plugin` → instalar; depois `/impeccable init` |
| ui-ux-pro-max | `/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill` e `/plugin install ui-ux-pro-max@ui-ux-pro-max-skill` |
| awesome-design-md | não é skill: copiar o `DESIGN.md` da Vercel (getdesign.md/vercel.com/design-md ou a pasta `design-md/vercel` do repo VoltAgent/awesome-design-md) para `applications/frontend/DESIGN.md` |

Depois de instalar, reiniciar a sessão para as skills carregarem.

## Etapa 1 — Infra: WebSocket no Mosquitto e API de leitura

- `applications/mosquitto/mosquitto.conf`: adicionar `listener 9001` + `protocol websockets`.
  - O modelo é `services/mosquitto/mosquitto.conf`, que já tem esse listener.
  - Continua anônimo; a limitação já está registrada no comentário.
- Nova pasta `applications/api/` (FastAPI + psycopg, imagem própria como o ingestor).
  - Conecta com o papel somente leitura criado por `applications/db/02-leitor.sh` (`grafana_leitor`; renomear para `leitor` na Etapa 7).
  - Os filtros comuns são query params validados: `caso[]`, `participante[]`, `janela=arquivo|sopro`, `simulador=bool`. Eles substituem os fragmentos `SIMULADOR`, `SO_RODADAS_ESCOLHIDAS` e `LEITURAS_ESCOLHIDAS` de `applications/grafana/montar_dashboard.py`, que é a fonte da verdade do SQL a portar.
  - Endpoints (um por painel do Grafana):
    - `GET /api/filtros`: casos, participantes e rodadas (id + rótulo "caso · participante · DD/MM HH:MI").
    - `GET /api/resumo`: situação da placa (recebendo/parada pelo `max(recebido_em)`), total de rodadas e total de leituras.
    - `GET /api/distribuicao`: p5/p25/p50/p75/p95/média por caso de MQ-3, MQ-135 e umidade (boxplot).
    - `GET /api/heatmap`: % de diferença da média de cada caso em relação ao `clean`.
    - `GET /api/dispersao`: amostra fixa de até 400 pontos por caso (MQ-3 × MQ-135), com `md5` para ser repetível.
    - `GET /api/sobrepostas`: `rodada, caso, tempo_s, humidity_pct, mq135_raw, ppm`.
    - `GET /api/rodadas/{id}/leituras`: `tempo_s, mq3_raw, mq135_raw, humidity_pct, em_sopro, caso`.
    - `GET /api/sopros`: subidas de MQ-3 e MQ-135 por sopro (`v_sopros`).
    - `GET /api/rodadas-sem-sopro`: tabela a partir de `v_rodadas_sem_sopro`.
  - Testes em pytest com o marcador `integracao`, reaproveitando o fixture de banco temporário de `applications/coleta/tests/conftest.py`. Cobrem os filtros, a exclusão do simulador e o heatmap sem `clean` (resposta vazia, sem erro).

## Etapa 2 — Esqueleto do frontend e design system

`applications/frontend/` com Vite + React + TypeScript:

| Peça | Escolha |
| --- | --- |
| Gráficos | ECharts via `echarts-for-react`, o mesmo motor do Business Charts; boxplot e heatmap são nativos e a lógica de `paineis/*.js` se porta quase direto |
| Ao vivo | `mqtt` (mqtt.js) sobre WebSocket |
| Dados da API | TanStack Query (cache, refetch e estados de carregando/erro) |
| Animações | Motion (`motion/react`) |
| Fonte | Geist Sans e Geist Mono (pacote `geist`) |

**Tokens** em `src/styles/tokens.css`:
- Gerados a partir do `DESIGN.md` da Vercel: cores neutras, raios, espaçamentos, sombras e escala tipográfica.
- Em `:root`, escuro por padrão e claro com `[data-theme="light"]`.
- Os números usam Geist Mono com `tabular-nums`.

**Paleta dos casos:**
- Mantém as cores e os rótulos de `paineis/comum.js` (clean→"ambiente", drink→"bebida" etc.) e a ordem fixa dos casos, centralizadas em `src/dominio/casos.ts`.
- Validar o contraste no claro e no escuro com a skill `dataviz`.

**Tema:**
- Um único `src/graficos/temaEcharts.ts` lê os tokens, então os gráficos acompanham a troca de tema.
- A troca usa View Transitions quando o navegador suporta.
- A preferência fica em `localStorage`.

**Página de referência visual:**
- Rota `/design-system` mostra os tokens, os tipos, as cores dos casos e os componentes base (Card, Stat, Chip, Segmented, Toggle, Badge de status).
- É o "design system em HTML" vivo da equipe.

## Etapa 3 — Seção "Ao vivo" (topo da tela)

Atributos mostrados ao vivo: **PPM, MQ-135 e umidade**. O PPM entra só para visualização. Ele é calculado pelo firmware a partir do MQ-3, então continua fora de rótulos e de features do ML.

### Recomendação de gráfico: 3 linhas empilhadas com o mesmo eixo de tempo

- **Linha** é o gráfico certo para série temporal contínua. Como as escalas são muito diferentes (PPM, ADC bruto, %), cada atributo ganha a **sua grade**, empilhada e alinhada no tempo. Não usar um gráfico com dois eixos Y, que engana na leitura.
- Janela deslizante dos **últimos 3 min**, com a linha nova entrando pela direita.
- Em cada grade:
  - uma **linha tracejada da linha de base do ambiente**, a mediana móvel das leituras classificadas como ambiente;
  - uma faixa clara de ±tolerância em volta dela.

  Assim quem olha vê na hora quando o sinal sai do normal do carro.
- **Faixa de estado** no topo do gráfico, do tipo timeline: `ambiente` (neutro), `sopro detectado` (acento), `recuperando` (meio-tom). Os trechos marcados à mão (`sopro_inicio`/`sopro_fim`) aparecem como contorno, para comparar o detector com a marcação.
- Ponteiro do mouse compartilhado entre as 3 grades.

### Detecção ambiente × sopro (heurística, não é ML)

Fica em `src/aovivo/detectorSopro.ts`, uma função pura testada com Vitest.

- **Linha de base:** mediana dos últimos 60 s em estado `ambiente`. Ela não é atualizada durante o sopro nem na recuperação, para o carro poder "derivar" devagar sem disparar o detector.
- **Sopro detectado:** a umidade sobe pelo menos `Δumid` acima da base **e** (PPM **ou** MQ-135) sobe pelo menos `Δgás`, dentro de uma janela de ~5 s. A umidade é o sinal do sopro (ar expirado); o gás é o sinal de álcool ou vapor. A regra exige os dois porque perfume e álcool no ambiente sobem o gás sem subir a umidade.
- **Estados:** `ambiente` → `sopro detectado` → `recuperando` (até voltar a ±tolerância da base) → `ambiente`. Uma histerese evita que o estado pisque.
- **Limiares:** ficam num arquivo de configuração (`src/aovivo/limiares.ts`) e são tratados como **hipótese**. O valor inicial vem da comparação ambiente × bebida descrita em "Mudança depois da aprovação". Quando houver sopros marcados, `v_sopros` passa a ser a fonte, e a calibração é revista depois da análise exploratória.
- **Na tela, o estado aparece como "estimado".** Não é a classificação `sob_efeito`/`sem_efeito`; ela entra quando houver modelo.

### Dados ao vivo

`src/aovivo/useMqtt.ts`:
- Assina `mq3/+/rodada` (retida), `leituras`, `eventos` e `status` (retida).
- Guarda as leituras num buffer circular de cerca de 5 min.
- Monta as janelas marcadas à mão a partir de `sopro_inicio`/`sopro_fim`; sem `sopro_fim`, usa início + 5 s, a mesma regra de `v_janelas_sopro`.
- Passa as leituras pelo detector.
- Os tipos de mensagem espelham `applications/coleta/mensagens.py`.

### Componentes

- **Card de estado grande:** "Ambiente" / "Sopro detectado" / "Recuperando", com transição animada entre os estados e o tempo no estado atual. É o destaque da tela para a demonstração.
- **Três Stats** (PPM, MQ-135, umidade): valor atual com tween e a **variação em relação à base** (ex.: `+12,4 %`), colorida quando passa do limiar.
- **Faixa da rodada:** caso (com a cor do caso), participante, placa e tempo decorrido.
- **Badge da placa:** online, offline ou sem dados há mais de 10 s, com pulso quando está recebendo.
- **O gráfico de 3 linhas descrito acima.**
- **Aviso animado** em `sopro_inicio` marcado, em sopro detectado e em `rodada_fim`.
- **Estado vazio:** "Aguardando a placa…", com instrução para rodar o simulador.

## Etapa 4 — Seções de análise (os painéis do Grafana redesenhados)

**Barra de filtros fixa**, no estado da URL para poder compartilhar o link:
- casos em chips multiseleção com a cor de cada caso;
- janela "arquivo / sopro" em controle segmentado;
- interruptor "incluir simulador" (desligado por padrão);
- participante escondido, como no Grafana.

**Topo:** cards de resumo (rodadas, leituras), com contagem animada.

Seções, na ordem do Grafana:

1. **Comparação entre os casos**
   - Boxplot com 3 grades (p5–p95, p25–p75, mediana e losango da média).
   - Heatmap divergente com a cor do `clean`, um neutro e a cor do `drink`, escala ±max(10, |máx|).
   - Dispersão MQ-3 × MQ-135.
2. **Todas as rodadas juntas**
   - Linhas sobrepostas (umidade, MQ-135, PPM).
   - Amostragem LTTB, eixo compartilhado e zoom inicial de 0–300 s.
3. **Rodada selecionada**
   - Seletor de rodada.
   - 3 grades com as faixas de sopro (`markArea` calculado das sequências de `em_sopro`).
4. **Sopros marcados**
   - Dispersão das subidas.
   - Tabela "rodadas sem sopro marcado".

As transformações de dados viram funções puras em `src/graficos/*.ts`: percentis → séries do boxplot, sequências de `em_sopro` → faixas, ordenação e cor dos casos, escala do heatmap. Elas são portadas de `applications/grafana/paineis/*.js`.

Cada gráfico tem estados de carregando (skeleton), vazio (mensagem, como `semDados`) e erro.

## Etapa 5 — Animações e acabamento

Seguir as skills do Emil Kowalski, impeccable e web-design-guidelines:
- Entrada escalonada das seções ao rolar.
- Transição entre o skeleton e o gráfico.
- Interações curtas (150–250 ms, easing ease-out).
- Números com tween.
- Pulso de status.
- Animação dos gráficos ao trocar de filtro, sem refazer tudo.
- `prefers-reduced-motion` desliga tudo isso.

Layout e acessibilidade:
- Navegação por âncoras entre as seções.
- Responsivo até a largura de celular.
- Foco visível, contraste AA e textos em português.

Rodar `/impeccable critique` e `audit` e o web-design-guidelines sobre o resultado e corrigir.

## Etapa 6 — Compose e documentação

**`docker-compose.yml`:**
- Novos serviços `api` e `frontend`. O `frontend` é um build multi-stage: o Node gera o build e um nginx serve os arquivos e faz o proxy de `/api` e `/mqtt`, na porta `127.0.0.1:8080`.
- Expor 9001 do Mosquitto só para a rede interna; o navegador entra pelo nginx.
- O que for preciso entra no `.env.example`.

**Para desenvolver:** o proxy do `vite.config.ts` aponta `/api` e `/mqtt` para a stack local.

**Documentação:**
- `applications/frontend/README.md` (como rodar, arquitetura, como adicionar um gráfico).
- Atualizar `applications/README.md`.
- Atualizar `AGENTS.md` nas seções 4, 6, 7.1, 7.3 e 8.

## Etapa 7 — Remoção do Grafana (só quando o React cobrir tudo)

1. Conferir, painel a painel, que o React mostra tudo o que o Grafana mostra.
2. Apagar:
   - `applications/grafana/` e `applications/pdc/`;
   - os serviços `pdc` e `grafana` do compose;
   - as variáveis `GCLOUD_*`, `GRAFANA_*` do `.env.example`;
   - `coleta/tests/test_dashboard.py`.
3. Renomear o papel `grafana_leitor` para `leitor` em `02-leitor.sh`, com uma migração em `applications/db/migracoes/`.
4. Atualizar o `AGENTS.md`: a seção 7.3 passa a descrever o frontend.

O que **não** muda: `services/`, que é o outro fluxo e uma decisão da equipe, e o firmware.

## Arquivos principais

- Novos: `applications/api/`, `applications/frontend/` (`src/aovivo`, `src/graficos`, `src/dominio`, `src/styles`, `DESIGN.md`, `Dockerfile`, `nginx.conf`).
- Alterados: `applications/mosquitto/mosquitto.conf`, `docker-compose.yml`, `.env.example`, `applications/README.md`, `AGENTS.md`.
- Referência para portar: `applications/grafana/montar_dashboard.py` (SQL), `applications/grafana/paineis/*.js` (gráficos e cores), `applications/db/01-schema.sql` (views), `applications/coleta/mensagens.py` (payloads).

## Verificação

1. `cd applications && python -m pytest`: a suíte atual continua verde, e os testes da API passam com `PG_DSN`.
2. `cd applications/frontend && npm test`: Vitest das funções puras e do parser das mensagens MQTT. As funções puras são as faixas de sopro, percentis → boxplot, cor e ordem dos casos, "ambiente" e a escala do heatmap. O **detector** é testado com sequências montadas à mão:
   - ambiente estável não dispara;
   - deriva lenta não dispara;
   - subida só de gás (perfume) não dispara;
   - umidade + gás dispara;
   - a volta à base retorna a `ambiente`.

   Depois, conferir o detector contra os sopros marcados das sessões reais: quantos sopros marcados ele achou e quantos falsos disparos fez em trechos de ambiente. Esses números são da heurística, não do modelo.
3. Ponta a ponta:
   - `docker compose up -d --build`;
   - importar CSVs reais (importador ou lote de `applications/`);
   - rodar `python -m coleta.simulador ../esp32-esp8266/leituras.csv --caso clean --participante p00 --sopros 20`;
   - abrir `http://localhost:8080` e ver os pontos chegando, o badge "recebendo", a faixa do sopro e os gráficos de análise preenchidos.
4. Playwright (Chromium): abrir a página com a stack de pé e o simulador rodando, conferir que o gráfico ao vivo recebe pontos e que as seções renderizam. Tirar screenshots no tema escuro e no claro, no desktop e no celular, para revisão visual.
5. Comparar lado a lado com o Grafana local (`docker compose --profile local up -d`): mesmos números no boxplot, heatmap e contagens com os mesmos filtros. Só depois disso fazer a Etapa 7.
