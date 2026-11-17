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
```

## Organização

| Pasta | O quê |
| --- | --- |
| `src/dominio` | Regras sem tela: casos (nome, cor, ordem), formato dos números |
| `src/tema` | Tema escuro/claro (padrão escuro), guardado no navegador |
| `src/componentes` | Blocos base: cartão, número, filtros, selo da placa |
| `src/layout` | Cabeçalho e seções |
| `src/paginas` | Páginas além da tela principal (`/design-system`) |
| `src/styles` | Tokens e fontes Geist |
