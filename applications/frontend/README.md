# Sopro Seguro — tela (frontend)

Tela única do sistema: leituras ao vivo da placa e os gráficos de análise de
todas as coletas. Substitui o dashboard do Grafana quando cobrir todos os painéis.

- React + TypeScript (Vite), gráficos em ECharts.
- Design system: [`DESIGN.md`](DESIGN.md) (Vercel / Geist), traduzido em
  `src/styles/tokens.css`. A referência viva fica em `/design-system`.
- Ao vivo: MQTT por WebSocket (`/mqtt`). Análise: a API de `../api` (`/api`).
- Aba Modelo (`/modelo`): três sopros de exemplo da coleta. O botão envia o recorte
  para `POST /modelo/classificar` e a classe aparece na mesma tela.

## Rodar em desenvolvimento

Com o Compose de pé na raiz (`docker compose up -d --build`):

```bash
cd applications/frontend
npm install
npm run dev        # http://localhost:5173
```

O `vite.config.ts` manda `/api` para `127.0.0.1:8000`, `/modelo/` para `127.0.0.1:8010`
e `/mqtt` para `127.0.0.1:9001`.

O classificador, sem subir o Compose inteiro (com o `ml/.venv` ativo, na raiz):

```bash
PYTHONPATH=services:ml python -m mq3mqtt.classificar_http
```

Ele lê `ml/models/sob_efeito.joblib`. Sem esse arquivo a aba responde "Sem modelo."
No Compose da raiz o mesmo processo é o serviço `model`.

O Compose também serve a tela pronta, com nginx, em http://localhost:8080
(`Dockerfile` + `nginx.conf`: `/api/` vai para a API, `/modelo/` para o classificador
e `/mqtt` para o Mosquitto).
Reconstruir depois de mudar a tela: `docker compose up -d --build frontend`, na raiz.

## Testes

```bash
npm test           # Vitest: domínio, componentes e transformações dos gráficos
npm run e2e        # Playwright; o broker MQTT é simulado (e2e/brokerFalso.ts)
```

Para ver dados ao vivo sem a placa, rode o simulador de `applications/` (ver `../README.md`).

## Detector ambiente × sopro

A seção "Ao vivo" estima se há alguém soprando no sensor: umidade **e** gás (MQ-135
ou MQ-3 cru) subindo juntos em relação à linha de base do ambiente. É uma heurística
para a demonstração, não o modelo de ML, e os limiares (`LIMIARES` em
`src/aovivo/detector.ts`) são hipótese a revisar com os dados. O `ppm` do firmware é
só mostrado, nunca usado na decisão.

## Organização

| Pasta | O quê |
| --- | --- |
| `src/dominio` | Regras sem tela: casos (nome, cor, ordem), formato dos números |
| `src/tema` | Tema escuro/claro (padrão escuro), guardado no navegador |
| `src/componentes` | Blocos base: cartão, número, filtros, selo da placa |
| `src/layout` | Cabeçalho, seções e menu do celular |
| `src/paginas` | Páginas além da tela principal (`/design-system`) |
| `src/aovivo` | Seção "Ao vivo": MQTT (`useAoVivo`), estado (`estado.ts`), detector ambiente × sopro (`detector.ts`) e componentes |
| `src/modelo` | Aba Modelo: sopros de exemplo, pedido ao classificador e a classe na tela |
| `src/analise` | Filtros na URL, resumo e as quatro seções de análise |
| `src/graficos` | Opções do ECharts como funções puras (testadas) e leitura das cores do tema |

## Como adicionar um gráfico

1. Função pura em `src/graficos/`, recebendo `{ dados, cores, tema, animar }` e
   devolvendo as opções do ECharts. Reaproveite `src/graficos/comum.ts` (eixos,
   dica, legenda). O PPM pode aparecer; não entra em regra nenhuma.
2. Teste ao lado (`*.test.ts`) com `CORES_TESTE`: confira séries, cores e textos,
   não o canvas.
3. Um `CartaoGrafico` na seção (`src/analise/Secao*.tsx`) com
   `<GraficoECharts opcoes={fn} rotulo="..." />`. A `fn` vem de um `useCallback`
   para o gráfico não redesenhar à toa. Se a rota da API ainda não existe, ela
   entra em `applications/api/consultas.py` e o hook em `src/api/consultas.ts`.
| `e2e` | Testes ponta a ponta com Playwright |
| `src/styles` | Tokens e fontes Geist |
