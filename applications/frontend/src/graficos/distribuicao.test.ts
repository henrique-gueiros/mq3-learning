import { describe, expect, it } from 'vitest'
import type { DistribuicaoCaso, Percentis } from '../api/consultas'
import { corDoCaso } from '../dominio/casos'
import { opcoesDistribuicao } from './distribuicao'
import { CORES_TESTE as cores } from './testes/cores'

const p = (base: number): Percentis => ({ p5: base, p25: base + 1, p50: base + 2, p75: base + 3, p95: base + 4, media: base + 2.5 })

const dados: DistribuicaoCaso[] = [
  { caso: 'perfume', n: 50, mq3: p(2000), mq135: p(1100), umid: p(55) },
  { caso: 'drink', n: 80, mq3: p(1500), mq135: p(700), umid: p(80) },
  { caso: 'clean', n: 120, mq3: p(800), mq135: p(300), umid: p(45) },
]

const boxplots = (o: ReturnType<typeof opcoesDistribuicao>) => o.series.filter((s) => s.type === 'boxplot')

describe('opcoesDistribuicao', () => {
  it('um boxplot por sensor (MQ-3, MQ-135, Umidade), cada um na sua grade', () => {
    const o = opcoesDistribuicao({ dados, cores, tema: 'escuro' })
    expect(o.grid).toHaveLength(3)
    expect(boxplots(o).map((s) => s.name)).toEqual(['MQ-3', 'MQ-135', 'Umidade (%)'])
    expect(boxplots(o).map((s) => s.xAxisIndex)).toEqual([0, 1, 2])
  })

  it('lado a lado por padrão; empilhado (tela estreita) uma grade embaixo da outra, na largura toda', () => {
    const lado = opcoesDistribuicao({ dados, cores, tema: 'escuro' })
    expect(lado.grid.map((g) => g.left)).toEqual(['0%', '34%', '68%'])
    const pilha = opcoesDistribuicao({ dados, cores, tema: 'escuro', empilhado: true })
    expect(pilha.grid.map((g) => g.left)).toEqual([0, 0, 0])
    expect(pilha.title.map((t) => t.left)).toEqual([0, 0, 0])
    const topos = pilha.grid.map((g) => parseFloat(String(g.top)))
    expect(topos[0]).toBeLessThan(topos[1])
    expect(topos[1]).toBeLessThan(topos[2])
  })

  it('casos na ordem do protocolo, com o nome em português ("ambiente" para clean)', () => {
    const o = opcoesDistribuicao({ dados, cores, tema: 'escuro' })
    expect(o.xAxis[0].data).toEqual(['ambiente', 'bebida', 'perfume'])
  })

  it('caixa com [p5, p25, p50, p75, p95] no lugar certo', () => {
    const o = opcoesDistribuicao({ dados, cores, tema: 'escuro' })
    const mq3 = boxplots(o)[0].data as { value: number[] }[]
    expect(mq3[0].value).toEqual([800, 801, 802, 803, 804])
    expect(mq3[1].value).toEqual([1500, 1501, 1502, 1503, 1504])
  })

  it('caixa na cor do caso: preenchimento translúcido e borda cheia', () => {
    const o = opcoesDistribuicao({ dados, cores, tema: 'claro' })
    const caixa = (boxplots(o)[0].data as { itemStyle: { color: string; borderColor: string } }[])[1]
    expect(caixa.itemStyle.borderColor).toBe(corDoCaso('drink', 'claro'))
    expect(caixa.itemStyle.color).toMatch(/^rgba\(.*, 0\.22\)$/)
  })

  it('losango da média por caso, com o valor ao lado', () => {
    const o = opcoesDistribuicao({ dados, cores, tema: 'escuro' })
    const medias = o.series.filter((s) => s.type === 'scatter')
    expect(medias).toHaveLength(3)
    expect(medias[0].symbol).toBe('diamond')
    expect((medias[0].data as { value: [string, number] }[])[0].value).toEqual(['ambiente', 802.5])
  })

  it('tooltip com n, mediana, quartis, percentis e média', () => {
    const o = opcoesDistribuicao({ dados, cores, tema: 'escuro' })
    const formatar = (boxplots(o)[2].tooltip as { formatter: (x: { dataIndex: number }) => string }).formatter
    const texto = formatar({ dataIndex: 1 })
    expect(texto).toContain('bebida')
    expect(texto).toContain('80 leituras')
    expect(texto).toContain('mediana 82,0')
    expect(texto).toContain('média 82,5')
  })
})
