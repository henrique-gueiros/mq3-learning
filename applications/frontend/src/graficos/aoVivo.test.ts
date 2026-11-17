import { describe, expect, it } from 'vitest'
import type { Leitura } from '../aovivo/mensagens'
import { JANELA_GRAFICO_S, opcoesAoVivo, type CoresGrafico } from './aoVivo'

const cores: CoresGrafico = {
  tinta: '#eee', corpo: '#aaa', mudo: '#888', linha: '#222', cartao: '#0a0a0a',
  linhaSerie: '#3987e5', sopro: '#ff0080', recuperando: '#f5a623', fonte: 'Geist', fonteMono: 'Geist Mono',
}

const leituras = (n: number): Leitura[] =>
  Array.from({ length: n }, (_, i) => ({
    rodada_id: 'r', amostra: i, t_ms: i * 1000, mq3_raw: 800, ppm: 0.4 + i / 1000, mq135_raw: 250 + i, temperature_c: 28, humidity_pct: 45,
  }))

const base = { umid: 45, mq135: 250, mq3: 650, ppm: 0.4 }

describe('opcoesAoVivo', () => {
  it('três gráficos empilhados: PPM, MQ-135 e umidade, um eixo y cada', () => {
    const o = opcoesAoVivo({ leituras: leituras(20), base, trechos: [], marcadas: [], cores })
    expect(o.grid).toHaveLength(3)
    expect(o.yAxis).toHaveLength(3)
    const linhas = o.series.filter((s) => s.type === 'line' && s.name)
    expect(linhas.map((s) => s.name)).toEqual(['PPM', 'MQ-135', 'Umidade'])
    expect(linhas[1].data[3]).toEqual([3, 253])
  })

  it(`mostra só os últimos ${JANELA_GRAFICO_S} s, com o tempo da sessão em segundos`, () => {
    const o = opcoesAoVivo({ leituras: leituras(400), base, trechos: [], marcadas: [], cores })
    expect(o.xAxis[0].max).toBe(399)
    expect(o.xAxis[0].min).toBe(399 - JANELA_GRAFICO_S)
    const curta = opcoesAoVivo({ leituras: leituras(10), base, trechos: [], marcadas: [], cores })
    expect(curta.xAxis[0].min).toBe(0)
    expect(curta.xAxis[0].max).toBe(JANELA_GRAFICO_S)
  })

  it('linha tracejada da base em cada gráfico', () => {
    const o = opcoesAoVivo({ leituras: leituras(20), base, trechos: [], marcadas: [], cores })
    const bases = o.series.filter((s) => s.name).map((s) => s.markLine?.data?.[0]?.yAxis)
    expect(bases).toEqual([0.4, 250, 45])
  })

  it('sem base (calibrando) a linha da base fica vazia, para apagar a anterior', () => {
    const o = opcoesAoVivo({ leituras: leituras(5), base: null, trechos: [], marcadas: [], cores })
    expect(o.series.filter((s) => s.name).every((s) => s.markLine?.data.length === 0)).toBe(true)
  })

  it('pinta os trechos de sopro e recuperação e contorna os sopros marcados', () => {
    const o = opcoesAoVivo({
      leituras: leituras(60),
      base,
      trechos: [
        { estado: 'ambiente', inicio_ms: 0, fim_ms: 29000 },
        { estado: 'sopro', inicio_ms: 30000, fim_ms: 40000 },
        { estado: 'recuperando', inicio_ms: 41000, fim_ms: 59000 },
      ],
      marcadas: [{ inicio_ms: 31000, fim_ms: 34000 }],
      cores,
    })
    const estados = o.series.filter((s) => s.id?.startsWith('estados'))
    expect(estados).toHaveLength(3)
    const areas = estados[0].markArea!.data
    expect(areas).toHaveLength(2)
    expect(areas[0][0]).toMatchObject({ xAxis: 30 })
    expect(areas[0][1]).toMatchObject({ xAxis: 40 })
    const marcadas = o.series.filter((s) => s.id?.startsWith('marcadas'))
    expect(marcadas[0].markArea!.data[0][0]).toMatchObject({ xAxis: 31 })
  })

  it('valores vazios do DHT11 viram buracos na linha, não zero', () => {
    const l = leituras(3)
    l[1] = { ...l[1], humidity_pct: null }
    const o = opcoesAoVivo({ leituras: l, base, trechos: [], marcadas: [], cores })
    expect(o.series.find((s) => s.name === 'Umidade')!.data[1]).toEqual([1, null])
  })
})
