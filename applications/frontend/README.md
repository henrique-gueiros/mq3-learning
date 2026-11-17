# Tela do MQ-3 (frontend)

Tela única do sistema: leituras ao vivo da placa e os gráficos de análise de
todas as coletas. Substitui o dashboard do Grafana quando cobrir todos os painéis.

- React + TypeScript (Vite), gráficos em ECharts, animações com Motion.
- Design system: [`DESIGN.md`](DESIGN.md) (Vercel / Geist), traduzido em
  `src/styles/tokens.css`. A referência viva fica em `/design-system`.
- Ao vivo: MQTT por WebSocket (`/mqtt`). Análise: a API de `../api` (`/api`).

## Rodar em desenvolvimento

Com o Compose de pé na raiz (`docker compose up -d --build`):

```bash
cd applications/frontend
npm install
npm run dev        # http://localhost:5173
```

O `vite.config.ts` manda `/api` para `127.0.0.1:8000` e `/mqtt` para `127.0.0.1:9001`.

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
| `src/layout` | Cabeçalho e seções |
| `src/paginas` | Páginas além da tela principal (`/design-system`) |
| `src/aovivo` | Seção "Ao vivo": MQTT (`useAoVivo`), estado (`estado.ts`), detector ambiente × sopro (`detector.ts`) e componentes |
| `src/graficos` | Opções do ECharts como funções puras (testadas) e leitura das cores do tema |
| `e2e` | Testes ponta a ponta com Playwright |
| `src/styles` | Tokens e fontes Geist |
