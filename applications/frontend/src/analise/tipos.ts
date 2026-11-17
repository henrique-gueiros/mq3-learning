import type { Filtros } from './filtros'

/**
 * Contrato das quatro seções de análise (`SecaoComparacao`, `SecaoRodadas`,
 * `SecaoRodada`, `SecaoSopros`). Cada uma renderiza a sua `<Secao>` e busca os dados
 * com os hooks de `src/api/consultas.ts`, passando `filtros` (já compatível com
 * `FiltrosApi`). Dentro do `CartaoGrafico`, use `GraficoECharts` com opções puras de
 * `src/graficos/`.
 */
export interface PropsSecao {
  /** Filtros atuais, vindos da URL. `casos` vazio = todos os casos. */
  filtros: Filtros
  /** Muda parte dos filtros e atualiza a URL (ex.: a rodada escolhida: `aoMudarFiltros({ rodada: id })`). */
  aoMudarFiltros: (mudanca: Partial<Filtros>) => void
}
