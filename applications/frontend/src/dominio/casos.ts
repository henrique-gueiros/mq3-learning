/**
 * Casos do protocolo de coleta: nome em português, ordem fixa e cor por tema.
 * As cores e os nomes vêm do dashboard do Grafana (grafana/paineis/comum.js),
 * para os dois mostrarem a mesma coisa do mesmo jeito.
 */

export type Tema = 'escuro' | 'claro'

const NOMES: Record<string, string> = {
  clean: 'ambiente',
  drink: 'bebida',
  perfume: 'perfume',
  alcohol70_spray: 'álcool 70 (spray)',
  alcohol70_hands: 'álcool 70 (mãos)',
  mouthwash: 'enxaguante',
}

const ORDEM = Object.keys(NOMES)

const CORES: Record<Tema, Record<string, string>> = {
  claro: {
    clean: '#2a78d6', drink: '#eb6834', perfume: '#1baf7a', alcohol70_spray: '#eda100',
    alcohol70_hands: '#e87ba4', mouthwash: '#008300', outro: '#6250d6',
  },
  escuro: {
    clean: '#3987e5', drink: '#d95926', perfume: '#199e70', alcohol70_spray: '#c98500',
    alcohol70_hands: '#d55181', mouthwash: '#0ca30c', outro: '#9085e9',
  },
}

/** Nome do caso para mostrar na tela; um caso novo aparece com o nome técnico. */
export function nomeDoCaso(caso: string): string {
  return NOMES[caso] ?? caso
}

/** Cor do caso no tema; um caso fora do protocolo usa a cor de "outro". */
export function corDoCaso(caso: string, tema: Tema): string {
  return CORES[tema][caso] ?? CORES[tema].outro
}

/** Casos sem repetição, na ordem do protocolo; os desconhecidos vão para o fim, em ordem alfabética. */
export function ordenarCasos(casos: Iterable<string>): string[] {
  const posicao = (c: string) => (ORDEM.includes(c) ? ORDEM.indexOf(c) : ORDEM.length)
  return [...new Set(casos)].sort((a, b) => posicao(a) - posicao(b) || a.localeCompare(b))
}
