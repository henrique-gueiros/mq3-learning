import type { CoresGrafico } from './aoVivo'

/** Lê os tokens do tema atual (no <html>) para os gráficos acompanharem a troca de tema. */
export function lerToken(nome: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(`--${nome}`).trim()
}

/** Cores dos gráficos no tema atual; `linhaSerie` é a cor do caso da rodada. */
export function coresDoTema(linhaSerie?: string): CoresGrafico {
  return {
    tinta: lerToken('tinta'),
    corpo: lerToken('corpo'),
    mudo: lerToken('mudo'),
    linha: lerToken('linha'),
    cartao: lerToken('cartao'),
    linhaSerie: linhaSerie ?? lerToken('tinta'),
    sopro: lerToken('rosa'),
    recuperando: lerToken('ambar'),
    fonte: lerToken('fonte'),
    fonteMono: lerToken('fonte-mono'),
    neutro: lerToken('neutro-grafico'),
  }
}

/** O visitante pediu menos movimento no sistema operacional. */
export const semMovimento = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
