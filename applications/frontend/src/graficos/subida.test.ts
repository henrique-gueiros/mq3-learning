import { describe, expect, it } from 'vitest'
import type { Sopro } from '../api/consultas'
import { corDoCaso } from '../dominio/casos'
import { opcoesSubida } from './subida'
import { CORES_TESTE as cores } from './testes/cores'

const dados: Sopro[] = [
  { caso: 'drink', subida_mq3: 900, subida_mq135: 400 },
  { caso: 'perfume', subida_mq3: 1200, subida_mq135: 700 },
  { caso: 'drink', subida_mq3: 850, subida_mq135: 380 },
]

describe('opcoesSubida', () => {
  it('um ponto por sopro, [subida MQ-3, subida MQ-135], uma série por caso', () => {
    const o = opcoesSubida({ dados, cores, tema: 'escuro' })
    expect(o.series.map((s) => s.name)).toEqual(['bebida', 'perfume'])
    expect(o.series[0].data).toEqual([[900, 400], [850, 380]])
  })

  it('ponto cheio na cor do caso', () => {
    const o = opcoesSubida({ dados, cores, tema: 'claro' })
    expect(o.series[1].itemStyle.color).toBe(corDoCaso('perfume', 'claro'))
  })

  it('subida do MQ-3 no x e do MQ-135 no y', () => {
    const o = opcoesSubida({ dados, cores, tema: 'escuro' })
    expect(o.xAxis.name).toMatch(/MQ-3/)
    expect(o.yAxis.name).toMatch(/MQ-135/)
  })
})
