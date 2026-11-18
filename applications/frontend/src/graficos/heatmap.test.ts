import { describe, expect, it } from 'vitest'
import type { CelulaHeatmap } from '../api/consultas'
import { corDoCaso } from '../dominio/casos'
import { celulasHeatmap, limiteHeatmap, opcoesHeatmap } from './heatmap'
import { CORES_TESTE as cores } from './testes/cores'

const dados: CelulaHeatmap[] = [
  { caso: 'perfume', mq3: 152.4, mq135: 210.6, umid: -3.2 },
  { caso: 'drink', mq3: 80.5, mq135: 60.1, umid: 41.7 },
]

describe('celulasHeatmap', () => {
  it('uma célula [sensor, caso, % arredondado] por valor, casos na ordem do protocolo', () => {
    const { casos, celulas } = celulasHeatmap(dados)
    expect(casos).toEqual(['drink', 'perfume'])
    expect(celulas).toContainEqual([0, 0, 81])
    expect(celulas).toContainEqual([2, 1, -3])
    expect(celulas).toHaveLength(6)
  })

  it('valor ausente não vira célula', () => {
    const { celulas } = celulasHeatmap([{ caso: 'drink', mq3: 10, mq135: null, umid: 5 }])
    expect(celulas).toHaveLength(2)
  })
})

describe('limiteHeatmap', () => {
  it('escala simétrica no maior valor absoluto, nunca menor que 10', () => {
    expect(limiteHeatmap([[0, 0, -250], [1, 0, 30]])).toBe(250)
    expect(limiteHeatmap([[0, 0, 3]])).toBe(10)
    expect(limiteHeatmap([])).toBe(10)
  })
})

describe('opcoesHeatmap', () => {
  it('escala divergente: ambiente embaixo, cinza no meio, bebida em cima', () => {
    const o = opcoesHeatmap({ dados, cores, tema: 'escuro' })
    expect(o.visualMap.min).toBe(-211)
    expect(o.visualMap.max).toBe(211)
    expect(o.visualMap.inRange.color).toEqual([corDoCaso('clean', 'escuro'), cores.neutro, corDoCaso('drink', 'escuro')])
  })

  it('linhas com o nome dos casos e colunas com os sensores', () => {
    const o = opcoesHeatmap({ dados, cores, tema: 'escuro' })
    expect(o.yAxis.data).toEqual(['bebida', 'perfume'])
    expect(o.xAxis.data).toEqual(['MQ-3', 'MQ-135', 'Umidade (%)'])
  })

  it('rótulo da célula com sinal: +81% e −3%', () => {
    const o = opcoesHeatmap({ dados, cores, tema: 'escuro' })
    const rotulo = o.series[0].label.formatter
    expect(rotulo({ value: [0, 0, 81] })).toBe('+81%')
    expect(rotulo({ value: [2, 1, -3] })).toBe('−3%')
    expect(rotulo({ value: [2, 1, 0] })).toBe('0%')
  })
})
