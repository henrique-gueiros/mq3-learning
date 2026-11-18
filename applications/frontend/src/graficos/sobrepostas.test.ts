import { describe, expect, it } from 'vitest'
import type { SerieSobreposta } from '../api/consultas'
import { corDoCaso } from '../dominio/casos'
import { opcoesSobrepostas } from './sobrepostas'
import { CORES_TESTE as cores } from './testes/cores'

const dados: SerieSobreposta[] = [
  { rodada: 'r1', caso: 'drink', pontos: [[0, 50, 400, 0.4], [1, 55, 420, 0.5]] },
  { rodada: 'r2', caso: 'clean', pontos: [[0, 45, 300, 0.3], [1, null, 310, 0.3]] },
  { rodada: 'r3', caso: 'drink', pontos: [[0, 60, 500, 0.6]] },
]

describe('opcoesSobrepostas', () => {
  it('três grades empilhadas: Umidade, MQ-135 e PPM', () => {
    const o = opcoesSobrepostas({ dados, cores, tema: 'escuro' })
    expect(o.grid).toHaveLength(3)
    expect(o.title.map((t) => t.text)).toEqual(['Umidade (%)', 'MQ-135', 'PPM'])
  })

  it('uma série por rodada em cada grade, com os pontos [tempo, valor]', () => {
    const o = opcoesSobrepostas({ dados, cores, tema: 'escuro' })
    expect(o.series).toHaveLength(9)
    const mq135 = o.series.filter((s) => s.xAxisIndex === 1)
    expect(mq135.map((s) => s.id)).toEqual(['r1-1', 'r2-1', 'r3-1'])
    expect(mq135[0].data).toEqual([[0, 400], [1, 420]])
    expect(o.series.find((s) => s.id === 'r2-0')!.data).toEqual([[0, 45], [1, null]])
  })

  it('linha na cor do caso da rodada e nome do caso (a legenda agrupa por caso)', () => {
    const o = opcoesSobrepostas({ dados, cores, tema: 'claro' })
    const r2 = o.series.find((s) => s.id === 'r2-2')!
    expect(r2.name).toBe('ambiente')
    expect((r2.lineStyle as { color: string }).color).toBe(corDoCaso('clean', 'claro'))
    expect(o.legend.data).toEqual(['ambiente', 'bebida'])
  })

  it('dica com as três grades: cada linha diz a medida e usa as casas dela', () => {
    const o = opcoesSobrepostas({ dados, cores, tema: 'escuro' })
    const formatar = (o.tooltip as { formatter: (itens: unknown[]) => string }).formatter
    const item = (seriesIndex: number, valor: number) => ({ seriesName: 'bebida', seriesIndex, color: '#f00', value: [1, valor] })
    const texto = formatar([item(0, 55), item(3, 420), item(6, 0.5)])
    expect(texto).toContain('Umidade (%) · bebida: 55,0')
    expect(texto).toContain('MQ-135 · bebida: 420')
    expect(texto).toContain('PPM · bebida: 0,50')
  })

  it('reduz pontos com lttb e começa com o zoom em 0–300 s, ligado nas três grades', () => {
    const o = opcoesSobrepostas({ dados, cores, tema: 'escuro' })
    expect(o.series.every((s) => s.sampling === 'lttb')).toBe(true)
    expect(o.dataZoom).toHaveLength(2)
    for (const z of o.dataZoom) {
      expect(z.startValue).toBe(0)
      expect(z.endValue).toBe(300)
      expect(z.xAxisIndex).toEqual([0, 1, 2])
    }
  })
})
