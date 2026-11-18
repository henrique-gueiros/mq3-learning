# Plano — Tela do Sopro Seguro em React (substitui o Grafana)

Branch: `frontend-react`. Atualizado a cada etapa concluída. Quem pegar a próxima
etapa deve conseguir trabalhar só com este arquivo, o código e os READMEs.

## Andamento

| Etapa | Situação | Commit |
| --- | --- | --- |
| 0. Ferramentas de design (skills + `DESIGN.md`) | feita | — (skills globais em `~/.claude/skills`) |
| 1. API somente leitura + WebSocket no Mosquitto | feita | `30f628e` |
| 2. Esqueleto do frontend e design system | feita | `fbb53ed` |
| 3. Seção "Ao vivo" e detector ambiente × sopro | feita | ver `git log` (commit desta etapa) |
| — Nome "Sopro Seguro", ARCHITECTURE.md, roadmap e AGENTS.md por área | feita | ver `git log` |
| 4. Seções de análise — Onda 1 (1A: base da análise) | feita | `b77f983`, merge `8958d3d`; ajustes `4fd9fd7`, `6e055fe` |
| 5a. Menu das seções no celular (1C) | feita | `7baafd2`, merge `2a5ebe4` |
| 6a. Tela no Compose com nginx (1B) | feita | `668722b`, merge `bd8d05f`; ajuste `98da720` |
| 4. Seções de análise — Onda 2 (2A–2D) | feita (ver "Onda 2 — feita") | ver `git log` (commit da Onda 2) |
| 4. e2e da análise (parte da 3B) | feito (`e2e/analise.spec.ts`) | mesmo commit |
| 4. Conferência dos números com o Grafana (resto da 3B) | feita: tudo igual (ver "3B — conferência com o Grafana") | ver `git log` |
| 5b. Animações, acabamento e revisão de design (3A) — parte 1 | feita (ver "3A — acabamento: parte 1 feita") | ver `git log` |
| 5b. Animações, acabamento e revisão de design (3A) — parte 2 | feita, com a revisão das skills e Lighthouse 100 (ver "3A — revisão das skills") | ver `git log` |
| 6b. Documentação (3C) | feita neste ciclo (READMEs, ARCHITECTURE, roadmap) | ver `git log` |
| 7. Remoção do Grafana | a fazer; **perguntar à equipe antes** (apaga pastas e serviços) | |

**Estado do ambiente (17/11, 22h):** Compose da raiz de pé, com `api` e `frontend` (8080)
reconstruídos com a Onda 2 e o zoom das rodadas; o Grafana local (perfil `local`) na 3000;
stack `services/` parada
(usa as mesmas portas). Postgres descartável dos testes da API: contêiner `pg-teste` na 55432.

## Regras de trabalho (valem para todas as etapas)

1. **Uma frente por pessoa ou agente**, seguindo as ondas de "Trabalho em paralelo". Uma frente só termina com testes verdes.
2. **TDD:** escreva o teste, veja falhar pelo motivo certo, escreva o mínimo para
   passar, refatore. Visual (cor, espaço, animação) não é TDD: confira por screenshot.
3. **Antes de todo commit:** rodar a revisão de código (skill `code-review` no Claude
   Code) sobre o diff e corrigir o que ela achar de válido.
4. **Ao terminar uma etapa:** atualizar este plano (tabela "Andamento", o que foi
   feito, e o detalhe da próxima etapa). Com frentes em paralelo, quem atualiza é só
   quem integra, no merge; a frente descreve o que fez na mensagem do commit.
5. Textos da tela e do código em português. Código simples, com tipos e docstring
   nas funções públicas.
6. `ppm` e `alcool` do firmware **não decidem nada** (AGENTS.md, "Regras invioláveis").
   O PPM pode ser **mostrado**, nunca usado como regra, rótulo ou feature.
7. Regras da pasta da tela: `applications/frontend/AGENTS.md`.

## Trabalho em paralelo (worktrees)

As etapas restantes não precisam ser todas em fila. O que trava o paralelismo são
arquivos compartilhados (`App.tsx`, `package.json`, `docker-compose.yml`, este plano).
A divisão abaixo dá a cada frente arquivos **só dela**; a base da Onda 1 cria os
pontos de encaixe para as outras não se tocarem.

```text
Onda 1 (já)        1A base da análise ─────┐        1B nginx + Compose (6a)        1C menu do celular (5a)
                                           ▼
Onda 2 (após 1A)   2A comparação   2B rodadas juntas   2C rodada selecionada   2D sopros
                                           │
Onda 3 (após 2)    3A acabamento e revisão de design (5b)   3B e2e da análise + conferência com o Grafana   3C docs (6b)
                                           │
Onda 4 (após 3B)   4A remoção do Grafana (7)
```

| Frente | Etapa | Depende de | Arquivos que só ela toca |
| --- | --- | --- | --- |
| **1A base da análise** | 4.1, 4.2, 4.7 | — | `src/api/*`, `src/analise/{filtros,BarraFiltros,Resumo,CartaoGrafico}*`, `src/graficos/GraficoECharts.tsx`, **e** os 4 componentes de seção vazios + a ligação deles no `App.tsx` |
| **1B nginx + Compose** | 6 (parte 6a) | — | `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `.env.example`, `playwright.config.ts` (`PLAYWRIGHT_BASE_URL`) |
| **1C menu do celular** | 5 (parte 5a) | — | `src/layout/Cabecalho.tsx`, `src/layout/layout.css` |
| **2A comparação** | 4.3 | 1A | `src/graficos/{distribuicao,heatmap,dispersao}*`, `src/analise/SecaoComparacao*` |
| **2B rodadas juntas** | 4.4 | 1A | `src/graficos/sobrepostas*`, `src/analise/SecaoRodadas*` |
| **2C rodada selecionada** | 4.5 | 1A | `src/graficos/rodada*`, `src/analise/SecaoRodada*` |
| **2D sopros** | 4.6 | 1A | `src/graficos/subida*`, `src/analise/SecaoSopros*` |
| **3A acabamento** | 5 (parte 5b) | 2A–2D, 1C | toca a tela toda: **uma frente só**, sem paralelo |
| **3B e2e + conferência** | aceite da 4 | 2A–2D | `e2e/analise.spec.ts` |
| **3C docs** | 6 (parte 6b) | 1B, 2A–2D | `applications/README.md`, `frontend/README.md`, `ARCHITECTURE.md`, `docs/roadmap.md` |
| **4A remoção do Grafana** | 7 | 3B | `applications/grafana/`, `pdc/`, compose, `.env.example`, `db/02-leitor.sh` |

Para a Onda 2 não esbarrar:
- A **1A** registra no `GraficoECharts` todos os módulos do ECharts que a Onda 2 vai usar
  (`BoxplotChart`, `HeatmapChart`, `ScatterChart`, `LineChart`, `VisualMapComponent`,
  `DataZoomComponent`, `LegendComponent`, `MarkAreaComponent`, `TooltipComponent`,
  `GridComponent`, `TitleComponent`) e instala o que faltar no `package.json`.
- A **1A** deixa no `App.tsx` as quatro seções ligadas a componentes vazios
  (`SecaoComparacao`, `SecaoRodadas`, `SecaoRodada`, `SecaoSopros`), cada um num arquivo.
  Cada frente da Onda 2 só preenche o seu.
- Só quem integra (a pessoa ou o agente orquestrador) mexe neste plano e no CSS global.

**Como abrir uma frente** (pessoa ou agente):

```bash
git switch frontend-react && git pull
git worktree add ../sopro-<frente> -b frente-<frente>   # ex.: ../sopro-2a-comparacao, branch frente-2a-comparacao
cd ../sopro-<frente>/applications/frontend && npm install
npm run dev -- --port 517X   # uma porta por worktree (5174, 5175…)
```

Ao terminar: testes verdes, `code-review`, um commit, e merge em `frontend-react`
na ordem das ondas (dentro de uma onda, qualquer ordem). Depois:
`git worktree remove ../sopro-<frente>`.

Com agentes do Claude Code: um agente por frente com isolamento em worktree, cada um
recebendo a linha da tabela, a seção da etapa correspondente e as regras acima; o
orquestrador revisa, faz o merge e atualiza o plano. A Onda 1 roda com 3 agentes ao
mesmo tempo; a Onda 2, com 4.

## Como rodar tudo (pré-requisitos de qualquer etapa)

```bash
# raiz do repositório
cp .env.example .env                 # se ainda não existir; troque as senhas
docker compose up -d --build         # Mosquitto (1883; ws 9001 só no localhost), Postgres, ingestor, API (8000), tela (8080)
python -m coleta.lote                # de applications/, com o ml/.venv ativo: importa os CSVs reais

# tela
cd applications/frontend
npm install
npm run dev                          # http://localhost:5173  (/api e /mqtt vão para o Compose)
npm test                             # Vitest
npm run e2e                          # Playwright (broker simulado; não precisa do Compose)
PLAYWRIGHT_BASE_URL=http://localhost:8080 npm run e2e   # o mesmo e2e contra a tela do Compose

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

Em desenvolvimento o Vite faz o proxy de `/mqtt` (para `127.0.0.1:9001`) e `/api` (para
`127.0.0.1:8000`); no Compose, o nginx do serviço `frontend` (http://localhost:8080) faz o
mesmo pela rede interna. Por isso a 9001 continua publicada, só em `127.0.0.1`.

## O que já existe (Etapas 0–3)

### API — `applications/api/`

- `consultas.py`: uma função por gráfico. Os filtros (`Filtros`: casos,
  participantes, janela `arquivo|sopro`, simulador) viram parâmetros do psycopg.
  O SQL de origem é o de `applications/grafana/montar_dashboard.py`.
- `app.py`: rotas FastAPI. Documentação em http://localhost:8000/api/docs.

| Rota | Devolve | Painel do Grafana |
| --- | --- | --- |
| `GET /api/filtros` | casos, participantes, rodadas (`id`, `caso`, `participante`, `origem`, `inicio` em UTC; a tela monta o rótulo no fuso do navegador) | variáveis |
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

## Onda 1 — feita (17/11): o que existe e o que ficou para depois

- **1A, base da análise.** `src/api/cliente.ts` (`buscar`, `montarQuery`), `src/api/consultas.ts`
  (hooks e tipos de todas as rotas), `src/analise/filtros.ts` (`Filtros`, `lerFiltros`,
  `escreverFiltros`, `useFiltrosDaUrl`), `BarraFiltros`, `Resumo` (mostra o erro da API),
  `CartaoGrafico`, `tipos.ts` (`PropsSecao`), `src/graficos/GraficoECharts.tsx` e as quatro
  cascas `Secao*.tsx` ligadas no `App.tsx` dentro de `<div className="analise">`.
- **1B, nginx.** `frontend/Dockerfile` (Node 22 → nginx 1.27), `frontend/nginx.conf` (fallback
  para `index.html`, `/api/` → `api:8000`, `/mqtt` → `mosquitto:9001` com Upgrade), serviço
  `frontend` em `127.0.0.1:8080`, que espera a API saudável (healthcheck em `/api/saude`).
  `PLAYWRIGHT_BASE_URL` faz o e2e usar uma tela já no ar.
- **1C, menu do celular.** `src/layout/MenuSecoes.tsx` + `secoes.ts` (lista única de links).
  Abre abaixo de 760 px; fecha ao escolher, com Esc (foco volta ao botão), ao tocar fora,
  ao sair o foco e ao alargar a tela; prende o Tab.
- **Revisão (integração):** o padding de `.recipiente` zerava o espaço vertical da barra de
  filtros e do resumo; a 390 px a barra quebrava em 3 linhas (112 px fixos) e cobria os
  títulos ao navegar por âncora. Corrigido: barra em uma linha que rola para o lado no
  celular e `scroll-margin-top` nas seções da análise.

Achados que ficaram para depois:

| Achado | Quem cuida |
| --- | --- |
| ~~`GraficoECharts` usa `notMerge`: trocar filtro redesenha sem animar~~: feito na 3A, parte 1 | — |
| ~~`BarraFiltros` some em silêncio se `/api/filtros` falhar~~: feito na 3A, parte 1 ("Casos indisponíveis." + "Tentar de novo") | — |
| Desmarcar o último chip volta a "todos" (como no Grafana); conferir se é o que a equipe quer | 3A |
| A 390 px a barra de filtros rola para o lado sem pista visual de que há mais (o segmentado fica cortado) | 3A |
| A marca "Sopro Seguro" quebra em duas linhas a 390 px (já era assim) | 3A |
| ~~Bundle de 1,4 MB num chunk só~~: feito na 3A, parte 1 (ver lá os números; o chunk principal ainda passa de 500 kB) | — |
| ~~Zoom inicial das rodadas sobrepostas~~: feito na 3A, parte 2 (opção 1, `fimDoZoom`) | — |
| "Rodadas sem sopro": hoje são as 12; quando houver `attempts.csv`, conferir se a tabela continua útil ou vira só uma contagem | 3A |
| 4 avisos do `oxlint`: 3 de antes (`TemaProvider`, `Aviso`, `GraficoAoVivo`) e 1 novo em `GraficoECharts` (`setState` no efeito: é a regra "cores lidas num `useEffect`", aceito) | 3A |
| ~~O texto de exemplo do "Ao vivo" aponta um arquivo inexistente~~: achado errado, `esp32-esp8266/leituras.csv` existe (conferido 17/11) | — |
| ~~`/api/filtros` devolve as rodadas do simulador e rótulos com o caso cru~~: resolvido na 2C (a API manda `origem`; a tela filtra e monta o rótulo) | — |
| `applications/README.md` e `frontend/README.md` ainda não falam do nginx/8080 | 3C |

## Onda 2 — feita (17/11)

Feita em sequência por um agente só (não em worktrees). Verificado: 162 testes do Vitest,
`tsc -b`, `npm run build`, 22 testes da API contra o Postgres descartável, e2e (4 testes)
no Vite e no nginx (8080), screenshots das quatro seções a 1280 px nos dois temas e a 390 px.

**Peças comuns** (criadas por quem integrou, usadas pelas quatro frentes):
- `src/graficos/comum.ts`: `EntradaGrafico<T>` (`dados, cores, tema, animar`), `comAlfa`,
  `eixoValor` (números pt-BR: `3.000`, `0,25`), `eixoCategoria` (todos os rótulos, `interval: 0`),
  `dica`, `legenda`, `tituloGrade`, `rotuloSegundos` (`1:30`), `gradesEmpilhadas` (várias grades
  com o mesmo tempo; só a última mostra o eixo), `animacao(animar)` (300/250 ms, `cubicOut`).
- `src/graficos/testes/cores.ts` (`CORES_TESTE`); `src/analise/testes/montar.tsx`
  (`apiFalsa(rotas)` por prefixo de caminho, valor `Error` vira 503; `montar(ui)`).
- Token `--neutro-grafico` (meio cinza do heatmap) em `tokens.css`, lido em `temaEcharts.ts`.
- `src/layout/useMidia.ts`: `useMidia('(max-width: 640px)')`.
- `analise.css`: `.grade-analise` (5 colunas: inteira, estreita = 2, larga = 3; abaixo de
  1000 px tudo em largura total), `.seletor-rodada*`, `.tabela*`.

**Por frente:**
- **2A** `distribuicao.ts` (boxplot; abaixo de 640 px as três grades empilham, altura 720),
  `heatmap.ts` (`celulasHeatmap`, `limiteHeatmap`, rótulo com sinal `+81%`/`−3%`),
  `dispersao.ts`; `SecaoComparacao.tsx`.
- **2B** `sobrepostas.ts` (zoom inicial por `fimDoZoom`, série `id = rodada-grade`, dica com até 8
  linhas e "+N rodadas"); `SecaoRodadas.tsx` (altura 560; a descrição diz que o PPM só é exibido).
- **2C** `rodada.ts` (`faixasDeSopro`, `markArea` cinza); `src/analise/rodadas.ts`
  (`rodadasVisiveis`, `rotuloRodada` = `bebida · p01 · 06/11/2026 14:00 [· simulador]`,
  `escolherRodada`: se a escolhida sumiu, volta para a mais recente); `SecaoRodada.tsx`
  (`<select>` nativo com a bolinha da cor; skeleton enquanto a lista carrega).
- **2D** `subida.ts`; `SecaoSopros.tsx` com a tabela em **2 colunas** (Rodada = caso · participante
  com o arquivo embaixo, cortado com reticências e `title`; Início). Com 4 colunas não cabia no
  cartão estreito.
- **API:** `/api/filtros` passou a mandar `origem`, `participante` e `inicio` e **deixou de mandar
  `rotulo`**: o `to_char` do Postgres saía em UTC e o seletor mostrava 15:36 onde a tabela mostrava
  12:36. Testes em `applications/api/tests/test_consultas.py`.
- **3B (parte):** `e2e/analise.spec.ts` — `page.route` só em caminhos que começam com `/api/`
  (com `**/api/**` o Playwright pegava também os módulos `src/api/*` do Vite e a tela não subia).
  Teste 1: as quatro seções desenham um `canvas` e a tabela lista o arquivo. Teste 2: "Só o sopro"
  põe `janela=sopro` na URL e na consulta de `/api/distribuicao`; trocar a rodada põe `rodada=` na URL.

**Ajustes vindos dos screenshots:** nome do eixo y da dispersão cortado (grid `left: 28`);
barra de zoom das rodadas sobrepostas sem contraste (agora preenchida e com alças na cor da
tinta). Uma rodada de ambiente tem **3 h** (11.251 s). O zoom inicial não usa mais 0–300 s
fixos: `fimDoZoom` vai até a rodada mais longa fora do ambiente (ver 3A, parte 2).

**Revisão de código (padrões + plano), corrigido antes do commit:**
- Dica das rodadas sobrepostas usava as casas decimais da primeira grade para todas; agora cada
  linha diz a medida (`PPM · bebida: 0,50`) e usa as casas dela (teste novo).
- `CORES_TESTE` tinha cores de 3 dígitos (`#eee`), que `comAlfa` não entende; agora 6 dígitos.
- Heatmap com só "ambiente" marcado dizia "Precisa de rodadas de ambiente"; agora pede outro caso.
- e2e passou a trocar um chip de caso (URL com `caso=` e a consulta refeita), como pede o aceite.
- `numeroDica` sem uso removido; altura do heatmap virou `alturaHeatmap` em `heatmap.ts`.
- Mexer em `analise.css`, `tokens.css`, `aoVivo.ts` e `temaEcharts.ts` foi trabalho de integração
  (a regra "frente não toca CSS global" vale para frentes em paralelo).
- Boxplot: a 4.3 diz "lado a lado"; abaixo de 640 px empilha (senão os rótulos se cruzam a 390 px).

**Achados da revisão que ficaram (julgamento, não bloqueiam):**

| Achado | Quem cuida |
| --- | --- |
| ~~`?rodada=` com uma rodada do simulador e o interruptor desligado fica velho na URL~~: feito na 3A, parte 1 (a seção limpa o `rodada=`) | — |
| Lista de sensores (`MQ-3`, `MQ-135`, `Umidade (%)`) repetida em `distribuicao.ts`, `heatmap.ts` e `rodada.ts`; `comSinal` repetido em `heatmap.ts` e `subida.ts`; `axisPointer` + cabeçalho da dica repetidos em `rodada.ts` e `sobrepostas.ts`: juntar em `comum.ts` | 3A |
| As quatro seções repetem `useCallback((cores, animar) => opcoesX({ dados: x.data ?? [], cores, tema, animar }))`; um hook `useOpcoes` deixaria mais curto | 3A |
| `origem` é `string` comparada com `'simulador'`; `EntradaGrafico.tema` repete `'escuro' \| 'claro'` em vez de importar `Tema`; `CoresGrafico` (com `neutro`, só da análise) mora em `aoVivo.ts` | 3A |
| API: `filtros` devolve `inicio` como datetime e `rodadas_sem_sopro` faz `.isoformat()`; dá o mesmo JSON, mas são dois jeitos | 3C ou 4A |
| Breakpoint `640px` do boxplot solto no componente, sem relação com os 1000 px do CSS | 3A |

A Onda 2, o e2e e este plano entraram num commit só. Ficaram fora dele, de propósito,
`.claude/worktrees/` e `Relatório progressão projeto.md` (não são desta tarefa).

## 3A — acabamento: parte 1 feita (17/11)

Verificado: 181 testes do Vitest, `tsc -b`, e2e (4) no Vite e no nginx (8080).

- **Bundle:** `Analise` e `/design-system` entram com `lazy` + `Suspense`; `LimiteDeErro`
  isola a análise se o chunk falhar. O Vite separa `react`, `mqtt` e o runtime. O chunk
  principal ainda passa de 500 kB (React + ECharts do ao vivo); a análise só baixa quando
  a página precisa dela.
- **Animação ao filtrar:** `GraficoECharts` com `notMerge: false` e `replaceMerge` nas séries
  (cada série tem `id` estável). Enquanto a consulta nova chega, o cartão esmaece o gráfico
  antigo (não some o canvas).
- **BarraFiltros:** se `/api/filtros` falhar, mostra "Casos indisponíveis." + "Tentar de novo".
- **Âncora:** com a análise lazy, `/#sopros` não achava o alvo na carga; `Analise` rola de novo
  quando as primeiras consultas terminam (só se a pessoa não rolou no meio-tempo).
- **URL:** se `?rodada=` aponta uma rodada do simulador e o interruptor está desligado, a seção
  limpa o `rodada=` ao escolher a mais recente visível.

## 3A — parte 2 feita

| Item | O que ficou |
| --- | --- |
| Entrada orquestrada | `entrada` em `.cabecalho` (0 ms), `.estado` (80 ms) e `.aovivo-numeros`/`.resumo` (160 ms), 200 ms. As seções de análise não animam a entrada. |
| Tween dos números | `interpolar` + `useValorAnimado` no `Stat`, 200 ms, só quando o valor muda. `prefers-reduced-motion` pula. |
| Skeleton → gráfico | `.grafico-corpo` surge em 200 ms na primeira montagem. Trocar filtro não recria o elemento (esmaece o anterior). |
| Interações | Já estavam em `--rapido` (150 ms) ou `--medio` (220 ms) com `--sair`. O menu abre em 180 ms. |
| Barra a 390 px | A rolagem mostra uma barra fina (`scrollbar-width: thin`), em vez de escondê-la. |
| Marca | Abaixo de 760 px, "Sopro Seguro" não quebra (`white-space: nowrap`, 15 px). |
| Sinal dos gráficos | `comSinal` em `formato.ts`, usado pelo heatmap e pela subida. |
| Ficou de fora, de propósito | Juntar as três listas de sensores (os campos diferem), o hook `useOpcoes`, mover `CoresGrafico` e unificar o breakpoint de 640 px com o de 1000 px: mudança grande para pouco ganho. Desmarcar o último chip continua voltando a "todos", como no Grafana, até a equipe decidir o contrário. |
| Acessibilidade | `:focus-visible` global e link "Pular para o conteúdo". Lighthouse 100 em 17/11. |

## 3A — revisão das skills (17/11)

Rodaram a crítica de design, o detector do Impeccable, a revisão de animação e as Web Interface Guidelines.

Corrigido:
- A seção "Ao vivo" só diz "leituras chegando" quando há leitura (`descricaoAoVivo`).
- O atalho Comparação pousa no resumo, não debaixo da barra (`#comparacao` envolve o resumo; `scroll-margin-top: 140px`).
- O rótulo da rodada inclui o arquivo, porque as 12 importações caem no mesmo segundo e o seletor repetia o mesmo texto. `/api/filtros` passou a mandar `arquivo`.
- O comando de exemplo quebra em espaços, não no meio da palavra.
- Valores fora da escala do design: raio 2px virou `--raio-xs` (4px), o título no celular foi de 36px para 32px, a marca de 15px para 16px, e a sombra do interruptor usa 8% da tinta em vez de `#00000040`.
- A entrada do gráfico ganhou um deslocamento de 4px, para não ser só um fade.
- Link "Pular para o conteúdo".

Ficou de fora, de propósito: reescrever o vazio do ao vivo (o comando é o jeito de testar sem a placa), mudar o primeiro clique do chip (a equipe ainda não decidiu) e trocar a regra global de `prefers-reduced-motion`, que o plano pediu para desligar o movimento. O detector marcou as fontes Geist como aviso; o design system as prescreve.

**Zoom das rodadas sobrepostas — opção 1 aplicada.** `fimDoZoom` (`sobrepostas.ts`): 0 até o
fim da rodada mais longa que não é ambiente, arredondado para cima ao minuto, mínimo 300 s.
Com o banco de 17/11 a bebida de 368 s vira **0–7:00**; a rodada de ambiente de 3 h continua
no gráfico e a barra deixa de ocupar ~3%. A descrição do cartão diz o intervalo ("Mostra até
7:00"). Sem rodada fora do ambiente, a janela usa a mais longa de todas, ainda com o mínimo
de 5 min. A equipe ainda deve conferir se aquela sessão de ambiente de 3 h foi planejada assim.

### 3B — conferência com o Grafana: feita (17/11)

Critério de aceite da Etapa 4: os números batem com o Grafana local com os mesmos filtros.

**Como foi feito** (para repetir antes da Etapa 7): com o Grafana local de pé
(`docker compose --profile local up -d grafana`, admin/admin), um script lê o `rawSql` de cada
painel em `applications/grafana/dashboards/coleta.json`, troca as variáveis (`$caso` pela lista,
`$participante` por todos, `$janela`, `$incluir_simulador` = `sim`/`nao`), roda pelo próprio
Grafana (`POST http://localhost:3000/api/ds/query`, datasource `mq3-postgres`) e compara com a
rota da API (`http://localhost:8000/api/...`) com os mesmos filtros. Igualdade exigida: tolerância
relativa de 1e-6 (só ponto flutuante). O script ficou fora do repositório (vai embora com o Grafana);
o método acima basta para refazê-lo.

**Resultado (banco de 17/11: 12 rodadas, 11.941 leituras, 0 sopros, todas de origem `importador`):**

| Filtros | Resumo (rodadas / leituras) | Números comparados (boxplot + heatmap) | Diferenças |
| --- | --- | --- | --- |
| todos, arquivo inteiro | 12 / 11.941 | 60 | 0 |
| só bebida | 4 / 727 | 21 | 0 |
| ambiente + perfume | 8 / 11.214 | 39 | 0 |
| só ambiente | 7 / 11.112 | 18 (heatmap vazio nos dois) | 0 |
| todos, só o sopro | 12 / 0 | 0 (vazio nos dois: não há sopro marcado) | 0 |
| todos, com simulador | 12 / 11.941 (não há rodada de simulador no banco) | 60 | 0 |

Também iguais: as 12 linhas de "Rodadas sem sopro marcado" (mesmos arquivos); "Subida por sopro"
vazia nos dois; rodadas sobrepostas com os mesmos 11.941 pontos em 12 rodadas; "Leituras da rodada"
ponto a ponto nas 12 rodadas (tempo, MQ-3, MQ-135, umidade); a dispersão com os mesmos 902 pontos
(400 por caso, sorteio fixo por `md5`) com todos os casos e os mesmos 400 só com bebida.

Observação: o heatmap dos dois lados calcula a base do ambiente **sem** o filtro de caso (por isso
"só bebida" ainda mostra a bebida comparada ao ambiente). Está igual ao Grafana e faz sentido.

**Limites da conferência:** não havia sopro marcado nem rodada de simulador no banco, então a janela
"só o sopro", a subida por sopro e o interruptor do simulador só foram conferidos no vazio. Os testes
da API (`applications/api/tests/test_consultas.py`) cobrem esses casos com dados montados no teste.
Refazer a conferência quando houver `attempts.csv` com sopros marcados.

## Onda 2: como encaixar (frentes 2A–2D)

Cada frente **só preenche o seu `Secao*.tsx`** e cria **só os arquivos da sua linha** na
tabela de paralelismo (funções puras e testes em `src/graficos/`). Não mexer em `App.tsx`,
`package.json`, `analise.css`, CSS global, `GraficoECharts.tsx` nem neste plano; se
faltar algo neles, avise quem integra.

Contrato (`src/analise/tipos.ts`):

```ts
interface PropsSecao {
  filtros: Filtros            // { casos: string[] (vazio = todos), janela: 'arquivo'|'sopro', simulador: boolean, rodada: string|null }
  aoMudarFiltros: (mudanca: Partial<Filtros>) => void   // ex.: aoMudarFiltros({ rodada: id }) atualiza a URL
}
```

- **Seção:** mantenha `<Secao id titulo descricao>` (os textos já estão na casca) e ponha
  os cartões como `children` (hoje a casca não passa `children`, por isso aparece o
  "Esta seção entra nas próximas etapas.").
- **Dados** (`src/api/consultas.ts`): `useDistribuicao`, `useHeatmap`, `useDispersao`,
  `useSobrepostas`, `useSopros` recebem `filtros` direto (já é um `FiltrosApi`; a rodada
  escolhida não entra na chave do cache). `useRodadasSemSopro()` e `useFiltros()` não têm
  filtros. `useLeiturasRodada(filtros.rodada ?? maisRecente)`, com
  `maisRecente = useFiltros().data?.rodadas[0]?.id`: sem id a consulta fica desligada e o
  cartão deve mostrar o vazio.
- **Cartão** (`src/analise/CartaoGrafico.tsx`):
  `<CartaoGrafico titulo descricao consulta={query} vazio={dados.length === 0 ? 'mensagem' : undefined}>`
  mostra skeleton carregando, a mensagem de vazio, ou o erro da API com "Tentar de novo";
  os `children` só aparecem com dados. Com consulta desligada (`isLoading` falso, sem
  dados), passe `vazio`.
- **Gráfico** (`src/graficos/GraficoECharts.tsx`, todos os módulos já registrados):
  `<GraficoECharts opcoes={fn} rotulo="..." altura={360} />`, onde `fn(cores, animar)`
  devolve as opções e tem identidade estável: monte com `useCallback` sobre uma função
  pura de `src/graficos/` (testada), com os dados e `corDoCaso(caso, tema)` entrando por
  closure. Teste de componente: `vi.mock` do `GraficoECharts`.
- **Pronto quando:** `npm test`, `npx tsc -b`, `npm run build` e `npm run e2e` verdes;
  screenshot em 1280 e 390 px nos dois temas; `code-review` sobre o diff; um commit.

## Etapa 4 — Seções de análise (feita: 1A, Onda 2 e conferência com o Grafana)

**Objetivo:** as quatro seções abaixo do "Ao vivo" mostram os mesmos gráficos do
Grafana, com os mesmos filtros, lendo a API. Ao final, dá para comparar com o
Grafana local e ver os mesmos números.

**Referências para portar** (lógica e textos de cada gráfico):
`applications/grafana/paineis/{distribuicao,variacao,separacao,sobreposicao,rodada,subida}.js`
e as descrições dos painéis em `applications/grafana/montar_dashboard.py`.

### 4.1 Acesso à API e filtros

Frente **1A**. Além dos arquivos abaixo, criar os quatro componentes de seção vazios
(`src/analise/SecaoComparacao.tsx`, `SecaoRodadas.tsx`, `SecaoRodada.tsx`,
`SecaoSopros.tsx`), ligados no `App.tsx`, e o `src/graficos/GraficoECharts.tsx` com
todos os módulos do ECharts registrados (ver "Trabalho em paralelo").

Arquivos novos:
- `src/api/cliente.ts`: `buscar<T>(rota, filtros)` monta a query string (`caso` repetido, `participante`, `janela`, `simulador`) e faz `fetch('/api/...')`; lança erro com a mensagem da API se `!ok`.
- `src/api/consultas.ts`: um hook TanStack Query por rota (`useFiltros`, `useResumo`, `useDistribuicao`, `useHeatmap`, `useDispersao`, `useSobrepostas`, `useLeiturasRodada(id)`, `useSopros`, `useRodadasSemSopro`), com tipos espelhando a tabela da API acima. A chave da query inclui os filtros.
- `src/analise/filtros.ts`: estado dos filtros **na URL** (`?caso=..&janela=..&simulador=1&rodada=..`): `lerFiltros(search)`, `escreverFiltros(filtros)` e o hook `useFiltrosDaUrl()` (usa `history.replaceState`).
- `src/analise/BarraFiltros.tsx`: fixa abaixo do cabeçalho (`position: sticky; top: 64px`) quando a seção de análise está na tela. Chips de caso (cor do caso, `ordenarCasos`), `Segmentado` "Arquivo inteiro / Só o sopro", `Interruptor` "Incluir simulador". Participante não aparece (como no Grafana).

Testes primeiro:
- [x] `filtros.test.ts`: ida e volta URL ↔ filtros; nenhum caso marcado = todos; janela inválida na URL vira `arquivo`.
- [x] `cliente.test.ts` (com `fetch` falso): query string com `caso` repetido; erro da API vira exceção com a mensagem.
- [x] `BarraFiltros.test.tsx`: clicar num chip muda a URL; o segmentado troca a janela.

### 4.2 Resumo (topo da análise)

- [x] `src/analise/Resumo.tsx`: `Stat`s de rodadas e leituras (`/api/resumo`) com os filtros. Teste: mostra os números formatados (`11.941`).

### 4.3 "Comparação entre os casos"

Funções puras em `src/graficos/` (testar as `options`, não o canvas), uma por gráfico:

- [x] `distribuicao.ts` → **boxplot** em 3 grades lado a lado (MQ-3, MQ-135, Umidade %).
  - Caixa p25–p75 com mediana, bigodes p5–p95 (`type: 'boxplot'`, dados `[p5,p25,p50,p75,p95]`), losango da média (`scatter`, `symbol: 'diamond'`) com o valor ao lado.
  - Preenchimento com a cor do caso a 22% e borda na cor cheia.
  - Tooltip com n, mediana, quartis, percentis e média.
  - Testes: ordem dos casos; `[p5..p95]` no lugar certo; cor por caso; nome "ambiente" para `clean`.
- [x] `heatmap.ts` → **heatmap divergente** casos × sensores, célula = % arredondado.
  - Escala simétrica ±max(10, |máx|); polos = cor do `clean` (negativo) e do `drink` (positivo), **meio neutro cinza** (regra da skill `dataviz`).
  - Vazio sem `clean`: mensagem "Precisa de rodadas de ambiente".
  - Testes: escala mínima 10; valor arredondado; sem dados → vazio.
- [x] `dispersao.ts` → **dispersão** MQ-3 (x) × MQ-135 (y), uma série por caso, alfa 0,6, legenda.

Componente `src/analise/SecaoComparacao.tsx`: grade com o boxplot em largura total; heatmap (≈40%) e dispersão (≈60%) lado a lado; cada gráfico num `Cartao` com título e uma linha de explicação (texto das descrições do Grafana).

### 4.4 "Todas as rodadas juntas"

- [x] `sobrepostas.ts` → linhas sobrepostas em 3 grades empilhadas (Umidade %, MQ-135, PPM), uma linha por rodada na cor do caso, `sampling: 'lttb'`, `dataZoom` (inside + slider), ponteiro ligado entre as grades, legenda por caso (não por rodada).
  - Testes: uma série por rodada × grade; cor pela rodada/caso; zoom inicial por `fimDoZoom` (mínimo 0–300 s; ignora rodada longa de ambiente e arredonda ao minuto).

### 4.5 "Rodada selecionada"

- [x] Seletor de rodada (`<select>` estilizado ou lista) com os rótulos de `/api/filtros`, guardado na URL (`rodada=`). Padrão: a mais recente.
- [x] `rodada.ts` → 3 grades empilhadas (MQ-3, MQ-135, Umidade) na cor do caso, com faixas cinza onde `em_sopro` (sequências contíguas viram `markArea`).
  - Teste da função `faixasDeSopro(pontos)`: sequências contíguas → `[início, fim]`; sem sopro → `[]`.

### 4.6 "Sopros marcados"

- [x] `subida.ts` → dispersão subida MQ-3 (x) × subida MQ-135 (y), um ponto por sopro, cor do caso. Vazio: "Nenhum sopro marcado. Marque com Enter na ponte ou em attempts.csv."
- [x] Tabela "Rodadas sem sopro marcado" (`/api/rodadas-sem-sopro`): caso (com bolinha da cor), participante, arquivo, início (data pt-BR). Ficou em 2 colunas (ver "Onda 2 — feita"). Cabeçalho em `caption-mono`, linhas com hairline (DESIGN.md, `ex-data-table-cell`).

### 4.7 Estados de cada gráfico

- [x] Componente `src/analise/CartaoGrafico.tsx`: título, descrição e o conteúdo; mostra **skeleton** carregando, **mensagem** vazia e **erro** com o texto da API e um botão "Tentar de novo" (`refetch`). Teste dos três estados.
- [x] Um componente `GraficoECharts` genérico (o mesmo padrão de `GraficoAoVivo`: registra só os módulos usados e lê as cores com `coresDoTema` num `useEffect`).

### Critérios de aceite da Etapa 4

- [x] `npm test` e `npm run e2e` verdes; novo e2e: com a rota `/api/*` falsa (`page.route`), as 4 seções renderizam e trocar um filtro muda a URL e refaz as consultas (o e2e usa o segmentado "Só o sopro"; os chips já têm teste no Vitest).
- [x] Com o Compose e os CSVs importados, os números do boxplot, heatmap e resumo batem com o Grafana local (`docker compose --profile local up -d`, http://localhost:3000) com os mesmos filtros. Resultado em "3B — conferência com o Grafana".
- [x] Screenshots (escuro e claro, 1280 px e 390 px) sem sobreposição de rótulos.
- [x] Plano atualizado e revisão de código antes do commit.

---

## Etapa 5 — Animações, acabamento e revisão de design (frentes 1C e 3A)

Skills: `emil-design-eng`, `animate`, `review-animations`, `impeccable`, `web-design-guidelines`, `vercel-react-best-practices`.

- [x] Uma única entrada orquestrada na carga da página (cabeçalho → estado ao vivo → números), nada de fade em cada seção.
- [x] Números do ao vivo com tween curto (≤ 200 ms) ao mudar; contagens do resumo idem.
- [x] Animação do ECharts ao trocar filtro (`notMerge: false` + `replaceMerge`), com os dados anteriores esmaecidos enquanto os novos chegam (3A, parte 1).
- [x] Transição skeleton → gráfico (opacidade) na primeira carga.
- [x] Interações 150–250 ms com `--sair`; `prefers-reduced-motion` desliga tudo (já há a regra global em `index.css`).
- [x] **(5a, frente 1C)** Menu das seções no celular (hoje os atalhos somem abaixo de 760 px): botão no cabeçalho que abre a lista de seções; fecha ao escolher, com Esc e ao tocar fora; foco preso enquanto aberto.
- [x] O build avisa bundle > 500 kB (ECharts + mqtt.js): separar com `import()` dinâmico os gráficos de análise e a página `/design-system` (3A, parte 1; o aviso continua para o chunk principal, ver lá).
- [x] Rodar `/impeccable critique` e o detector do audit, mais `review-animations` e as Web Interface Guidelines; corrigir o que era defeito (ver "3A — revisão das skills").
- [x] Foco visível (`:focus-visible` global), controles nativos no teclado e link "Pular para o conteúdo".
- [x] Lighthouse de acessibilidade: 100 em http://localhost:5173 (Chromium do Playwright, 17/11). A meta era ≥ 95.

## Etapa 6 — Compose (nginx) e documentação (6a = frente 1B; 6b = frente 3C)

- [x] `applications/frontend/Dockerfile` multi-stage: `node:22` faz `npm ci && npm run build`; `nginx:1.27-alpine` serve `dist/`.
- [x] `applications/frontend/nginx.conf`: `try_files $uri /index.html` (rota `/design-system`), `location /api/ → http://api:8000`, `location /mqtt → http://mosquitto:9001` com `Upgrade`/`Connection` para WebSocket.
- [x] `docker-compose.yml`: serviço `frontend` em `127.0.0.1:8080`, depois da API saudável. A 9001 e a 8000 **ficam** no host, só em `127.0.0.1`: o `npm run dev` precisa das duas.
- [x] Conferido: `http://localhost:8080` carrega, `/api/saude` responde e o WebSocket `/mqtt` conecta. `PLAYWRIGHT_BASE_URL=http://localhost:8080 npm run e2e` passa (2 testes; o broker falso intercepta o `/mqtt`, então não precisa do simulador). O e2e da análise (3B) entra no mesmo comando.
- [x] **(6b)** Docs: `applications/frontend/README.md` (como adicionar um gráfico: função pura + teste + componente), `applications/README.md` (a tela substitui o dashboard), `ARCHITECTURE.md` (tela, nginx, portas) e `docs/roadmap.md` (estado).

## Etapa 7 — Remoção do Grafana (frente 4A, só depois da Etapa 4 conferida)

- [x] Conferir painel a painel que a tela mostra tudo o que o Grafana mostra (feito na 3B, 17/11; refazer se o banco ganhar sopros marcados antes da remoção).
- [ ] Apagar `applications/grafana/`, `applications/pdc/`, os serviços `pdc` e `grafana` do compose, as variáveis `GCLOUD_*` e `GRAFANA_*` do `.env.example` e `coleta/tests/test_dashboard.py`.
- [ ] Renomear o papel `grafana_leitor` para `leitor` em `applications/db/02-leitor.sh` + migração em `applications/db/migracoes/`; atualizar `API_PG_DSN` no compose.
- [ ] `ARCHITECTURE.md` e `applications/AGENTS.md` deixam de citar o Grafana e descrevem só a tela.
- Não mexer em `services/` (outro fluxo; decisão da equipe) nem no firmware.
