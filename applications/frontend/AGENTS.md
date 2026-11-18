# AGENTS.md — applications/frontend/

A tela única do Sopro Seguro (React + TypeScript + Vite). Uso e organização em
`README.md`; plano e próximas etapas em `docs/planejamento/plans/2026-11-17-frontend-react.md`.

## Design

- O design system é o `DESIGN.md` (Vercel/Geist), traduzido em `src/styles/tokens.css`. Componentes usam só as variáveis de lá; cor nova entra primeiro como token, nos dois temas.
- Escuro é o padrão; `[data-theme='claro']` é a alternativa. Toda tela é conferida nos dois temas e em 390 px.
- O gradiente da marca é o único elemento decorativo e aparece só no `CartaoEstado`. O resto fica quieto: hierarquia por tipografia, espaço e anel de 1 px.
- Números em Geist Mono com `tabular-nums`; títulos de seção em frase curta com ponto final.
- Movimento só para mostrar mudança de estado, 150–250 ms, com `--sair`; `prefers-reduced-motion` desliga.

## Gráficos

- As opções do ECharts são funções puras em `src/graficos/`, com teste; o componente só registra os módulos usados e passa as opções.
- Cores: casos via `src/dominio/casos.ts` (validadas com a skill `dataviz`); escalas diferentes vão em grades separadas, um eixo y por grade.
- Cores do tema lidas com `coresDoTema()` num `useEffect`, depois que o tema foi aplicado.

## Ao vivo

- O estado vem de `reduzir()` em `src/aovivo/estado.ts` (puro); o hook `useAoVivo` só alimenta.
- O detector (`src/aovivo/detector.ts`) é uma heurística, não o modelo; `LIMIARES` são hipótese. Mudou um limiar? Reavalie nas sessões reais (veja o plano) e registre o resultado no plano.

## Testes

- `npm test` (Vitest: domínio, estado, opções de gráfico, componentes) e `npm run e2e` (Playwright com o broker falso de `e2e/brokerFalso.ts`, sem Mosquitto nem banco).
- O canvas do ECharts não roda no jsdom: teste as opções, e nos componentes faça `vi.mock` do gráfico.
