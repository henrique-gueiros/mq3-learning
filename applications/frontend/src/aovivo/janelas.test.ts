import { describe, expect, it } from 'vitest'
import { janelasMarcadas } from './janelas'

describe('janelasMarcadas', () => {
  it('cada sopro termina no primeiro sopro_fim antes do próximo sopro', () => {
    expect(
      janelasMarcadas([
        { tipo: 'sopro_inicio', t_ms: 20000 },
        { tipo: 'sopro_fim', t_ms: 23000 },
        { tipo: 'sopro_inicio', t_ms: 80000 },
      ]),
    ).toEqual([
      { inicio_ms: 20000, fim_ms: 23000 },
      { inicio_ms: 80000, fim_ms: 85000 },
    ])
  })

  it('sem sopro_fim usa 5 s e ignora fim que pertence ao próximo sopro', () => {
    expect(
      janelasMarcadas([
        { tipo: 'sopro_inicio', t_ms: 1000 },
        { tipo: 'sopro_inicio', t_ms: 9000 },
        { tipo: 'sopro_fim', t_ms: 10000 },
        { tipo: 'rodada_fim', t_ms: 50000 },
      ]),
    ).toEqual([
      { inicio_ms: 1000, fim_ms: 6000 },
      { inicio_ms: 9000, fim_ms: 10000 },
    ])
  })

  it('a ordem de chegada não importa', () => {
    expect(janelasMarcadas([{ tipo: 'sopro_fim', t_ms: 3000 }, { tipo: 'sopro_inicio', t_ms: 1000 }])).toEqual([
      { inicio_ms: 1000, fim_ms: 3000 },
    ])
  })
})
