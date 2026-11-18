import { describe, expect, it } from 'vitest'
import type { PontoDispersao } from '../api/consultas'
import { corDoCaso } from '../dominio/casos'
import { opcoesDispersao } from './dispersao'
import { CORES_TESTE as cores } from './testes/cores'

const dados: PontoDispersao[] = [
  { caso: 'perfume', mq3_raw: 2100, mq135_raw: 1150 },
  { caso: 'clean', mq3_raw: 800, mq135_raw: 300 },
  { caso: 'clean', mq3_raw: 820, mq135_raw: 310 },
]

describe('opcoesDispersao', () => {
  it('uma série por caso, na ordem do protocolo, com os pontos [MQ-3, MQ-135]', () => {
    const o = opcoesDispersao({ dados, cores, tema: 'escuro' })
    expect(o.series.map((s) => s.name)).toEqual(['ambiente', 'perfume'])
    expect(o.series[0].data).toEqual([[800, 300], [820, 310]])
  })

  it('pontos na cor do caso com alfa 0,6 e legenda por caso', () => {
    const o = opcoesDispersao({ dados, cores, tema: 'claro' })
    const n = parseInt(corDoCaso('perfume', 'claro').slice(1), 16)
    expect(o.series[1].itemStyle.color).toBe(`rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, 0.6)`)
    expect(o.legend.show).not.toBe(false)
  })

  it('MQ-3 no eixo x e MQ-135 no eixo y', () => {
    const o = opcoesDispersao({ dados, cores, tema: 'escuro' })
    expect(o.xAxis.name).toMatch(/MQ-3/)
    expect(o.yAxis.name).toMatch(/MQ-135/)
  })
})
