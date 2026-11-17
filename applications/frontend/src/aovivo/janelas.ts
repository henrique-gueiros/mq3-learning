/**
 * Janelas de sopro marcadas à mão (Enter na ponte), com a mesma regra da view
 * v_janelas_sopro: termina no primeiro sopro_fim antes do próximo sopro, ou 5 s depois.
 */

export interface Janela {
  inicio_ms: number
  fim_ms: number
}

const SEM_FIM_MS = 5000

export function janelasMarcadas(eventos: { tipo: string; t_ms: number }[]): Janela[] {
  const inicios = eventos.filter((e) => e.tipo === 'sopro_inicio').map((e) => e.t_ms).sort((a, b) => a - b)
  const fins = eventos.filter((e) => e.tipo === 'sopro_fim').map((e) => e.t_ms).sort((a, b) => a - b)
  return inicios.map((inicio, i) => {
    const proximo = inicios[i + 1] ?? Infinity
    const fim = fins.find((f) => f > inicio && f < proximo)
    return { inicio_ms: inicio, fim_ms: fim ?? inicio + SEM_FIM_MS }
  })
}
