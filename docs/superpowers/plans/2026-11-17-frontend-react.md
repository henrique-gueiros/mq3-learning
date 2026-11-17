# Plano — Tela única em React (substitui o Grafana)

Branch: `frontend-react`. Atualizado a cada etapa concluída. Quem pegar a próxima
etapa deve conseguir trabalhar só com este arquivo, o código e os READMEs.

## Andamento

| Etapa | Situação | Commit |
| --- | --- | --- |
| 0. Ferramentas de design (skills + `DESIGN.md`) | feita | — (skills globais em `~/.claude/skills`) |
| 1. API somente leitura + WebSocket no Mosquitto | feita | `30f628e` |
| 2. Esqueleto do frontend e design system | feita | `fbb53ed` |
| 3. Seção "Ao vivo" e detector ambiente × sopro | feita | ver `git log` (commit desta etapa) |
| 4. Seções de análise (painéis do Grafana redesenhados) | **próxima** | |
| 5. Animações, acabamento e revisão de design | a fazer | |
| 6. Compose (nginx) e documentação | a fazer | |
| 7. Remoção do Grafana | a fazer | |

## Regras de trabalho (valem para todas as etapas)

1. **Uma etapa por vez**, na ordem da tabela. Uma etapa só termina com testes verdes.
2. **TDD:** escreva o teste, veja falhar pelo motivo certo, escreva o mínimo para
   passar, refatore. Visual (cor, espaço, animação) não é TDD: confira por screenshot.
3. **Antes de todo commit:** rodar a revisão de código (skill `code-review` no Claude
   Code) sobre o diff e corrigir o que ela achar de válido.
4. **Ao terminar uma etapa:** atualizar este plano (tabela "Andamento", o que foi
   feito, e o detalhe da próxima etapa) no mesmo commit.
5. Textos da tela e do código em português. Código simples, com tipos e docstring
   nas funções públicas (AGENTS.md, seção 8).
6. `ppm` e `alcool` do firmware **não decidem nada** (AGENTS.md, seção 5.1). O PPM
   pode ser **mostrado**, nunca usado como regra, rótulo ou feature.

## Como rodar tudo (pré-requisitos de qualquer etapa)

```bash
# raiz do repositório
cp .env.example .env                 # se ainda não existir; troque as senhas
docker compose up -d --build         # Mosquitto (1883 e ws 9001), Postgres, ingestor, API (8000)
python -m coleta.lote                # de applications/, com o ml/.venv ativo: importa os CSVs reais

# tela
cd applications/frontend
npm install
npm run dev                          # http://localhost:5173  (/api e /mqtt vão para o Compose)
npm test                             # Vitest
npm run e2e                          # Playwright (broker simulado; não precisa do Compose)

# API
cd applications
python -m pytest                     # testes de banco precisam de PG_DSN (ver applications/README.md)

# leituras ao vivo sem a placa (de applications/, com o ml/.venv ativo)
python -m coleta.simulador ../ml/data/raw/sessions/2026-11-12_equipe_drink_4.csv \
  --caso drink --participante p00 --intervalo 0.25 --sopros 20
```

O simulador grava no banco como `origem = 'simulador'`. A análise deixa essas rodadas
de fora por padrão (interruptor "incluir simulador").

## Contexto e decisões

O dashboard do Grafana (`applications/grafana/`) tem bons gráficos e variáveis, mas o
visual é fraco e depende do PDC/Grafana Cloud. A equipe quer **uma tela só**, em React,
para todo visitante (checkpoint, Mostra TechDesign), com:

1. a coleta **ao vivo** (leituras chegando por MQTT);
2. os **gráficos de análise de todas as coletas**, os mesmos tipos e variáveis do
   Grafana, com design novo.

Decisões: React em `applications/frontend`; design system **Vercel/Geist**
(`applications/frontend/DESIGN.md`); **escuro por padrão** com troca para o claro;
ML fora por enquanto; o Grafana só sai na Etapa 7.

```
ESP32 / ponte / simulador ──MQTT──▶ Mosquitto ──▶ ingestor ──▶ PostgreSQL (views)
                                       │ ws:9001                        │
                                       ▼                                ▼
                         navegador (mqtt.js)              API FastAPI (somente leitura, :8000)
                                  └──── tela React: /mqtt e /api na mesma origem ────┘
```

Em desenvolvimento o Vite faz o proxy de `/mqtt` e `/api`; na Etapa 6 um nginx faz o mesmo.

## O que já existe (Etapas 0–3)

### API — `applications/api/`

- `consultas.py`: uma função por gráfico. Os filtros (`Filtros`: casos,
  participantes, janela `arquivo|sopro`, simulador) viram parâmetros do psycopg.
  O SQL de origem é o de `applications/grafana/montar_dashboard.py`.
- `app.py`: rotas FastAPI. Documentação em http://localhost:8000/api/docs.

| Rota | Devolve | Painel do Grafana |
| --- | --- | --- |
| `GET /api/filtros` | casos, participantes, rodadas (`id`, `caso`, `rotulo`) | variáveis |
| `GET /api/resumo` | `placa` (recebendo/parada), `rodadas`, `leituras` | 3 indicadores do topo |
| `GET /api/distribuicao` | por caso: `n` e `{p5,p25,p50,p75,p95,media}` de `mq3`, `mq135`, `umid` | boxplot |
| `GET /api/heatmap` | por caso (sem `clean`): % de `mq3`, `mq135`, `umid` em relação ao `clean` | heatmap |
| `GET /api/dispersao` | até 400 pontos por caso: `caso, mq3_raw, mq135_raw` | MQ-3 × MQ-135 |
| `GET /api/sobrepostas` | por rodada: `pontos` = `[tempo_s, umidade, mq135, ppm]` | rodadas sobrepostas |
| `GET /api/rodadas/{id}/leituras` | `caso` e pontos `tempo_s, t_ms, mq3_raw, mq135_raw, humidity_pct, ppm, em_sopro` | rodada selecionada |
| `GET /api/sopros` | `caso, subida_mq3, subida_mq135` | subida por sopro |
| `GET /api/rodadas-sem-sopro` | `rodada_id, caso, participante, arquivo, inicio` | tabela |

Filtros na query string: `?caso=drink&caso=perfume&participante=p01&janela=sopro&simulador=true`.

### Tela — `applications/frontend/`

| Pasta | O quê |
| --- | --- |
| `src/styles/tokens.css` | tokens do DESIGN.md (cores, sombras, raios, espaços), escuro padrão e `[data-theme='claro']` |
| `src/dominio` | `casos.ts` (nome, cor por tema, ordem), `formato.ts` (números pt-BR), `variacao.ts` |
| `src/tema` | `TemaProvider` + `BotaoTema` (guarda em localStorage, View Transitions) |
| `src/componentes` | `Cartao`, `Stat`, `SeloPlaca`, `Segmentado`, `Chip`, `Interruptor` |
| `src/layout` | `Cabecalho` (âncoras + selo + tema), `Secao` (título com ponto final + descrição) |
| `src/paginas/DesignSystem.tsx` | `/design-system`: referência viva dos tokens e componentes |
| `src/aovivo` | MQTT, estado, detector e componentes da seção "Ao vivo" (abaixo) |
| `src/graficos` | `aoVivo.ts` (opções do ECharts, testadas), `temaEcharts.ts` (lê os tokens) |
| `e2e/` | Playwright com broker MQTT falso (`brokerFalso.ts`) |

### Seção "Ao vivo" (Etapa 3)

- `aovivo/mensagens.ts`: tipos e `parsearMensagem` (formato de `applications/coleta/mensagens.py`; descarta `alcool` e `mq135_mv`).
- `aovivo/estado.ts`: `reduzir(estado, mensagem, agora)`, puro. Segue **uma placa**
  (a primeira com leituras; outra assume após 10 s de silêncio), guarda rodada e status
  retidos por placa, eventos pendentes por rodada, 5 min de leituras, trechos de
  estado do detector e o aviso atual. Ignora leituras repetidas e atrasadas.
- `aovivo/detector.ts`: heurística ambiente × sopro (não é ML), estados
  `calibrando → ambiente → sopro → recuperando`.
  - Base: mediana dos últimos 60 s de ambiente (não aprende o sopro).
  - Sopro: umidade **e** (MQ-135 **ou** MQ-3 cru) acima da base nos últimos 5 s, por 2 leituras seguidas.
  - Limiares (`LIMIARES`, **hipótese**): subida umid 8 pts, MQ-135 120, MQ-3 300; tolerância de volta 3 / 60 / 150; referência provisória umid 55, MQ-135 400, MQ-3 900 (só na 1ª calibração, para sessão que já começa num sopro); recuperação máx. 120 s; sopro máx. 5 min.
- `aovivo/useAoVivo.ts`: conecta `ws(s)://<host>/mqtt` com mqtt.js e assina `mq3/+/{rodada,leituras,eventos,status}`.
- Componentes: `CartaoEstado` (estado em letra grande; o gradiente da marca "respira" no sopro — único elemento decorativo da tela), `PainelAoVivo` (3 números com variação sobre a base, dados da rodada, gráfico, legenda), `GraficoAoVivo` (PPM, MQ-135 e umidade empilhados, 3 min, base tracejada, faixas de sopro/recuperação, sopros marcados em contorno), `Aviso` (toast), `SeloAoVivo` (relógio próprio de 1 s).

**Avaliação do detector nas sessões reais (17/11, rodadas fora do simulador):**

| Caso | Sessões | Resultado |
| --- | --- | --- |
| ambiente | 7 | 0 disparos em 6; 1 disparo em `6f3dbd6d` aos 942 s (umidade 50→67%, MQ-135 466→1004): parece sopro real dentro da sessão |
| bebida | 4 | sopro detectado em todas (42–66% do tempo em "sopro") |
| perfume | 1 | 0 disparos (gás alto sem umidade) |

**Limitações conhecidas:**
- Os limiares vêm de 12 sessões sem sopro marcado. Revisar na análise exploratória e quando houver `attempts.csv` com sopros marcados (aí `v_sopros` passa a ser a fonte).
- Carro já úmido (> ~63%) com gás alto no início da sessão pode mostrar "sopro" por até 120 s, até recalibrar.
- Sessão de bebida que começa no meio do sopro (base provisória) recalibra após 120 s e passa a tratar aquele ar como ambiente (`32d83bac`: 53% em sopro).

**Dados (17/11):** primeiros 20 s × depois de 60 s.

| Caso | Umidade (%) | MQ-135 | MQ-3 cru | PPM (só exibido) |
| --- | --- | --- | --- | --- |
| ambiente (7) | 35–55, estável | 180–530 | 520–1240 | ~0,4 |
| bebida (4) | 49–76 → 71–92 | 326–640 → 519–1063 | 1100–3000 | 0,40 → 0,87 numa delas |
| perfume (1) | 57 → 54 | ~1140 | ~2000–2800 | 0,31 → 0,47 |

A equipe ainda vai limpar os CSVs de bebida e perfume. Recomendação: **marcar** o
trecho válido (`blow_start_s`/`blow_end_s` no `attempts.csv`) em vez de editar o
bruto; um CSV editado tem outro SHA-256 e duplicaria a rodada no banco.

---

## Etapa 4 — Seções de análise (PRÓXIMA)

**Objetivo:** as quatro seções abaixo do "Ao vivo" mostram os mesmos gráficos do
Grafana, com os mesmos filtros, lendo a API. Ao final, dá para comparar com o
Grafana local e ver os mesmos números.

**Referências para portar** (lógica e textos de cada gráfico):
`applications/grafana/paineis/{distribuicao,variacao,separacao,sobreposicao,rodada,subida}.js`
e as descrições dos painéis em `applications/grafana/montar_dashboard.py`.

### 4.1 Acesso à API e filtros

Arquivos novos:
- `src/api/cliente.ts`: `buscar<T>(rota, filtros)` monta a query string (`caso` repetido, `participante`, `janela`, `simulador`) e faz `fetch('/api/...')`; lança erro com a mensagem da API se `!ok`.
- `src/api/consultas.ts`: um hook TanStack Query por rota (`useFiltros`, `useResumo`, `useDistribuicao`, `useHeatmap`, `useDispersao`, `useSobrepostas`, `useLeiturasRodada(id)`, `useSopros`, `useRodadasSemSopro`), com tipos espelhando a tabela da API acima. A chave da query inclui os filtros.
- `src/analise/filtros.ts`: estado dos filtros **na URL** (`?caso=..&janela=..&simulador=1&rodada=..`): `lerFiltros(search)`, `escreverFiltros(filtros)` e o hook `useFiltrosDaUrl()` (usa `history.replaceState`).
- `src/analise/BarraFiltros.tsx`: fixa abaixo do cabeçalho (`position: sticky; top: 64px`) quando a seção de análise está na tela. Chips de caso (cor do caso, `ordenarCasos`), `Segmentado` "Arquivo inteiro / Só o sopro", `Interruptor` "Incluir simulador". Participante não aparece (como no Grafana).

Testes primeiro:
- [ ] `filtros.test.ts`: ida e volta URL ↔ filtros; nenhum caso marcado = todos; janela inválida na URL vira `arquivo`.
- [ ] `cliente.test.ts` (com `fetch` falso): query string com `caso` repetido; erro da API vira exceção com a mensagem.
- [ ] `BarraFiltros.test.tsx`: clicar num chip muda a URL; o segmentado troca a janela.

### 4.2 Resumo (topo da análise)

- [ ] `src/analise/Resumo.tsx`: `Stat`s de rodadas e leituras (`/api/resumo`) com os filtros. Teste: mostra os números formatados (`11.941`).

### 4.3 "Comparação entre os casos"

Funções puras em `src/graficos/` (testar as `options`, não o canvas), uma por gráfico:

- [ ] `distribuicao.ts` → **boxplot** em 3 grades lado a lado (MQ-3, MQ-135, Umidade %).
  - Caixa p25–p75 com mediana, bigodes p5–p95 (`type: 'boxplot'`, dados `[p5,p25,p50,p75,p95]`), losango da média (`scatter`, `symbol: 'diamond'`) com o valor ao lado.
  - Preenchimento com a cor do caso a 22% e borda na cor cheia.
  - Tooltip com n, mediana, quartis, percentis e média.
  - Testes: ordem dos casos; `[p5..p95]` no lugar certo; cor por caso; nome "ambiente" para `clean`.
- [ ] `heatmap.ts` → **heatmap divergente** casos × sensores, célula = % arredondado.
  - Escala simétrica ±max(10, |máx|); polos = cor do `clean` (negativo) e do `drink` (positivo), **meio neutro cinza** (regra da skill `dataviz`).
  - Vazio sem `clean`: mensagem "Precisa de rodadas de ambiente".
  - Testes: escala mínima 10; valor arredondado; sem dados → vazio.
- [ ] `dispersao.ts` → **dispersão** MQ-3 (x) × MQ-135 (y), uma série por caso, alfa 0,6, legenda.

Componente `src/analise/SecaoComparacao.tsx`: grade com o boxplot em largura total; heatmap (≈40%) e dispersão (≈60%) lado a lado; cada gráfico num `Cartao` com título e uma linha de explicação (texto das descrições do Grafana).

### 4.4 "Todas as rodadas juntas"

- [ ] `sobrepostas.ts` → linhas sobrepostas em 3 grades empilhadas (Umidade %, MQ-135, PPM), uma linha por rodada na cor do caso, `sampling: 'lttb'`, `dataZoom` (inside + slider) começando em 0–300 s, ponteiro ligado entre as grades, legenda por caso (não por rodada).
  - Testes: uma série por rodada × grade; cor pela rodada/caso; zoom inicial 0–300.

### 4.5 "Rodada selecionada"

- [ ] Seletor de rodada (`<select>` estilizado ou lista) com os rótulos de `/api/filtros`, guardado na URL (`rodada=`). Padrão: a mais recente.
- [ ] `rodada.ts` → 3 grades empilhadas (MQ-3, MQ-135, Umidade) na cor do caso, com faixas cinza onde `em_sopro` (sequências contíguas viram `markArea`).
  - Teste da função `faixasDeSopro(pontos)`: sequências contíguas → `[início, fim]`; sem sopro → `[]`.

### 4.6 "Sopros marcados"

- [ ] `subida.ts` → dispersão subida MQ-3 (x) × subida MQ-135 (y), um ponto por sopro, cor do caso. Vazio: "Nenhum sopro marcado. Marque com Enter na ponte ou em attempts.csv."
- [ ] Tabela "Rodadas sem sopro marcado" (`/api/rodadas-sem-sopro`): caso (com bolinha da cor), participante, arquivo, início (data pt-BR). Cabeçalho em `caption-mono`, linhas com hairline (DESIGN.md, `ex-data-table-cell`).

### 4.7 Estados de cada gráfico

- [ ] Componente `src/analise/CartaoGrafico.tsx`: título, descrição e o conteúdo; mostra **skeleton** carregando, **mensagem** vazia e **erro** com o texto da API e um botão "Tentar de novo" (`refetch`). Teste dos três estados.
- [ ] Um componente `GraficoECharts` genérico (o mesmo padrão de `GraficoAoVivo`: registra só os módulos usados e lê as cores com `coresDoTema` num `useEffect`).

### Critérios de aceite da Etapa 4

- `npm test` e `npm run e2e` verdes; novo e2e: com a rota `/api/*` falsa (`page.route`), as 4 seções renderizam e trocar um chip muda a URL e refaz as consultas.
- Com o Compose e os CSVs importados, os números do boxplot, heatmap e resumo batem com o Grafana local (`docker compose --profile local up -d`, http://localhost:3000) com os mesmos filtros.
- Screenshots (escuro e claro, 1280 px e 390 px) sem sobreposição de rótulos.
- Plano atualizado e revisão de código antes do commit.

---

## Etapa 5 — Animações, acabamento e revisão de design

Skills: `emil-design-eng`, `animate`, `review-animations`, `impeccable`, `web-design-guidelines`, `vercel-react-best-practices`.

- [ ] Uma única entrada orquestrada na carga da página (cabeçalho → estado ao vivo → números), nada de fade em cada seção.
- [ ] Números do ao vivo com tween curto (≤ 200 ms) ao mudar; contagens do resumo idem.
- [ ] Transição skeleton → gráfico (opacidade), e animação do ECharts ao trocar filtro (`notMerge: false`).
- [ ] Interações 150–250 ms com `--sair`; `prefers-reduced-motion` desliga tudo (já há a regra global em `index.css`).
- [ ] Menu das seções no celular (hoje os atalhos somem abaixo de 760 px).
- [ ] O build avisa bundle > 500 kB (ECharts + mqtt.js): separar com `import()` dinâmico os gráficos de análise e a página `/design-system` (skill `vercel-react-best-practices`, regras de bundle).
- [ ] Rodar `/impeccable critique` e `/impeccable audit`, `review-animations` e `web-design-guidelines` sobre a tela; corrigir.
- [ ] Contraste AA de todo texto nos dois temas; foco visível em todos os controles; navegação por teclado.
- Aceite: screenshots antes/depois anexados ao PR; Lighthouse de acessibilidade ≥ 95.

## Etapa 6 — Compose (nginx) e documentação

- [ ] `applications/frontend/Dockerfile` multi-stage: `node:22` faz `npm ci && npm run build`; `nginx:1.27-alpine` serve `dist/`.
- [ ] `applications/frontend/nginx.conf`: `try_files $uri /index.html` (rota `/design-system`), `location /api/ → http://api:8000`, `location /mqtt → http://mosquitto:9001` com `Upgrade`/`Connection` para WebSocket.
- [ ] `docker-compose.yml`: serviço `frontend` em `127.0.0.1:8080`, `depends_on: api, mosquitto`. Tirar a porta 9001 do host (só o nginx fala com ela) e deixar a 8000 só se ainda for útil para desenvolver.
- [ ] Teste: `docker compose up -d --build` e o e2e apontado para `http://localhost:8080` (`PLAYWRIGHT_BASE_URL`), com o simulador rodando.
- [ ] Docs: `applications/frontend/README.md` (como adicionar um gráfico: função pura + teste + componente), `applications/README.md` (a tela substitui o dashboard), `AGENTS.md` seções 4, 6, 7.1, 7.3 e 8.

## Etapa 7 — Remoção do Grafana (só depois da Etapa 4 conferida)

- [ ] Conferir painel a painel que a tela mostra tudo o que o Grafana mostra.
- [ ] Apagar `applications/grafana/`, `applications/pdc/`, os serviços `pdc` e `grafana` do compose, as variáveis `GCLOUD_*` e `GRAFANA_*` do `.env.example` e `coleta/tests/test_dashboard.py`.
- [ ] Renomear o papel `grafana_leitor` para `leitor` em `applications/db/02-leitor.sh` + migração em `applications/db/migracoes/`; atualizar `API_PG_DSN` no compose.
- [ ] `AGENTS.md` seção 7.3 passa a descrever a tela.
- Não mexer em `services/` (outro fluxo; decisão da equipe) nem no firmware.
