import { describe, expect, it } from 'vitest'
import type { LeiturasRodada, PontoRodada } from '../api/consultas'
import { corDoCaso } from '../dominio/casos'
import { faixasDeSopro, opcoesRodada } from './rodada'
import { CORES_TESTE as cores } from './testes/cores'

const ponto = (tempo_s: number, em_sopro = false): PontoRodada => ({
  tempo_s, t_ms: tempo_s * 1000, mq3_raw: 800 + tempo_s, mq135_raw: 300, humidity_pct: 45, ppm: 0.4, em_sopro,
})

describe('faixasDeSopro', () => {
  it('sequências contíguas em sopro viram [início, fim]', () => {
    const pontos = [ponto(0), ponto(1, true), ponto(2, true), ponto(3), ponto(4, true), ponto(5)]
    expect(faixasDeSopro(pontos)).toEqual([[1, 2], [4, 4]])
  })

  it('sopro até a última leitura fecha na última', () => {
    expect(faixasDeSopro([ponto(0), ponto(1, true), ponto(2, true)])).toEqual([[1, 2]])
  })

  it('sem sopro devolve lista vazia', () => {
    expect(faixasDeSopro([ponto(0), ponto(1)])).toEqual([])
    expect(faixasDeSopro([])).toEqual([])
  })
})

describe('opcoesRodada', () => {
  const dados: LeiturasRodada = { rodada: 'r1', caso: 'perfume', pontos: [ponto(0), ponto(1, true), ponto(2)] }

  it('três grades empilhadas: MQ-3, MQ-135 e Umidade', () => {
    const o = opcoesRodada({ dados, cores, tema: 'escuro' })
    expect(o.grid).toHaveLength(3)
    expect(o.series.map((s) => s.name)).toEqual(['MQ-3', 'MQ-135', 'Umidade (%)'])
    expect(o.series[0].data).toEqual([[0, 800], [1, 801], [2, 802]])
  })

  it('linhas na cor do caso da rodada', () => {
    const o = opcoesRodada({ dados, cores, tema: 'claro' })
    expect((o.series[1].lineStyle as { color: string }).color).toBe(corDoCaso('perfume', 'claro'))
  })

  it('faixa cinza nas janelas de sopro, em todas as grades', () => {
    const o = opcoesRodada({ dados, cores, tema: 'escuro' })
    for (const s of o.series) {
      expect(s.markArea!.data).toEqual([[{ xAxis: 1 }, { xAxis: 1 }]])
    }
  })
})
