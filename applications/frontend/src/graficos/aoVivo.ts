/**
 * Opções do ECharts para o gráfico ao vivo: PPM, MQ-135 e umidade em três
 * gráficos empilhados (escalas diferentes não dividem eixo), com o mesmo tempo.
 *
 * Em cada um: a linha da leitura, a linha tracejada da base do ambiente, os trechos
 * em que o detector viu sopro (faixa cheia) ou recuperação (faixa clara) e os
 * sopros marcados à mão na ponte (contorno tracejado).
 */

import type { Base, EstadoSopro } from '../aovivo/detector'
import type { Trecho } from '../aovivo/estado'
import type { Janela } from '../aovivo/janelas'
import type { Leitura } from '../aovivo/mensagens'
import { formatarNumero } from '../dominio/formato'

/** O gráfico mostra os últimos 3 min; a tela guarda 5 min. */
export const JANELA_GRAFICO_S = 180

export interface CoresGrafico {
  tinta: string
  corpo: string
  mudo: string
  linha: string
  cartao: string
  /** Cor da rodada atual (a cor do caso). */
  linhaSerie: string
  sopro: string
  recuperando: string
  fonte: string
  fonteMono: string
  /** Meio neutro das escalas divergentes (heatmap). */
  neutro?: string
}

type Marca = Record<string, unknown>

export interface Serie {
  id?: string
  name?: string
  type: string
  data: unknown[]
  markLine?: { data: { yAxis: number }[]; [k: string]: unknown }
  markArea?: { data: [Marca, Marca][]; [k: string]: unknown }
  [k: string]: unknown
}

export interface OpcoesGrafico {
  grid: Marca[]
  xAxis: (Marca & { min: number; max: number })[]
  yAxis: Marca[]
  series: Serie[]
  [k: string]: unknown
}

interface Medida {
  nome: string
  casas: number
  unidade: string
  valor: (l: Leitura) => number | null
  base: (b: Base) => number | null
}

const MEDIDAS: Medida[] = [
  { nome: 'PPM', casas: 2, unidade: '', valor: (l) => l.ppm, base: (b) => b.ppm },
  { nome: 'MQ-135', casas: 0, unidade: '', valor: (l) => l.mq135_raw, base: (b) => b.mq135 },
  { nome: 'Umidade', casas: 1, unidade: '%', valor: (l) => l.humidity_pct, base: (b) => b.umid },
]

const segundos = (ms: number) => Math.round(ms / 100) / 10

/** mm:ss do tempo da sessão. */
export function rotuloTempo(s: number): string {
  const total = Math.max(0, Math.round(s))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

function comAlfa(hex: string, alfa: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alfa})`
}

const ALFA_ESTADO: Partial<Record<EstadoSopro, number>> = { sopro: 0.16, recuperando: 0.07 }

/** Monta as opções do ECharts do gráfico ao vivo a partir do estado da tela. */
export function opcoesAoVivo({
  leituras,
  base,
  trechos,
  marcadas,
  cores,
  animar = true,
}: {
  leituras: Leitura[]
  base: Base | null
  trechos: Trecho[]
  marcadas: Janela[]
  cores: CoresGrafico
  animar?: boolean
}): OpcoesGrafico {
  const ultimo = leituras.length ? segundos(leituras[leituras.length - 1].t_ms) : 0
  const max = Math.max(ultimo, JANELA_GRAFICO_S)
  const min = max - JANELA_GRAFICO_S

  // três faixas verticais iguais, com espaço para o título de cada uma
  const topo = (i: number) => `${4 + i * 33}%`
  // margem esquerda fixa para os rótulos do eixo y (o containLabel virou opcional no ECharts 6)
  const grid = MEDIDAS.map((_, i) => ({ left: 56, right: 20, top: topo(i), height: '24%' }))

  const xAxis = MEDIDAS.map((_, i) => ({
    type: 'value' as const,
    gridIndex: i,
    min,
    max,
    axisLine: { lineStyle: { color: cores.linha } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: {
      show: i === MEDIDAS.length - 1,
      hideOverlap: true,
      color: cores.mudo,
      fontFamily: cores.fonteMono,
      fontSize: 11,
      formatter: rotuloTempo,
    },
  }))

  const yAxis = MEDIDAS.map((m, i) => ({
    type: 'value' as const,
    gridIndex: i,
    scale: true,
    name: m.nome + (m.unidade ? ` (${m.unidade})` : ''),
    nameLocation: 'end',
    nameGap: 8,
    nameTextStyle: { color: cores.corpo, fontFamily: cores.fonte, fontSize: 12, align: 'left', padding: [0, 0, 0, -8] },
    splitNumber: 3,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: cores.mudo,
      fontFamily: cores.fonteMono,
      fontSize: 11,
      formatter: (v: number) => formatarNumero(v, m.casas),
    },
    splitLine: { lineStyle: { color: cores.linha } },
  }))

  const faixa = (inicio_ms: number, fim_ms: number, estilo: Marca): [Marca, Marca] => [
    { xAxis: segundos(inicio_ms), itemStyle: estilo },
    { xAxis: segundos(fim_ms) },
  ]

  const series: Serie[] = MEDIDAS.flatMap((m, i) => {
    const valorBase = base ? m.base(base) : null
    const linha: Serie = {
      name: m.nome,
      type: 'line',
      xAxisIndex: i,
      yAxisIndex: i,
      showSymbol: false,
      connectNulls: false,
      lineStyle: { width: 2, color: cores.linhaSerie },
      itemStyle: { color: cores.linhaSerie },
      emphasis: { disabled: true },
      data: leituras.map((l) => [segundos(l.t_ms), m.valor(l)]),
    }
    // sempre presente, mesmo vazio: o ECharts mescla opções e manteria a base antiga
    linha.markLine = {
      silent: true,
      symbol: 'none',
      lineStyle: { color: cores.mudo, type: [4, 4], width: 1 },
      label: { show: false },
      data: valorBase === null ? [] : [{ yAxis: valorBase }],
    }
    const estados: Serie = {
      id: `estados-${i}`,
      type: 'line',
      xAxisIndex: i,
      yAxisIndex: i,
      data: [],
      silent: true,
      markArea: {
        silent: true,
        data: trechos
          .filter((t) => ALFA_ESTADO[t.estado])
          .map((t) => faixa(t.inicio_ms, t.fim_ms, { color: comAlfa(t.estado === 'sopro' ? cores.sopro : cores.recuperando, ALFA_ESTADO[t.estado]!) })),
      },
    }
    const marcadasSerie: Serie = {
      id: `marcadas-${i}`,
      type: 'line',
      xAxisIndex: i,
      yAxisIndex: i,
      data: [],
      silent: true,
      markArea: {
        silent: true,
        data: marcadas.map((j) =>
          faixa(j.inicio_ms, j.fim_ms, { color: 'transparent', borderColor: cores.corpo, borderWidth: 1, borderType: [3, 3] }),
        ),
      },
    }
    return [linha, estados, marcadasSerie]
  })

  return {
    animation: animar,
    animationDurationUpdate: animar ? 300 : 0,
    animationEasingUpdate: 'linear',
    textStyle: { fontFamily: cores.fonte },
    grid,
    xAxis,
    yAxis,
    axisPointer: { link: [{ xAxisIndex: 'all' }], lineStyle: { color: cores.corpo, width: 1 } },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', snap: true },
      backgroundColor: cores.cartao,
      borderColor: cores.linha,
      textStyle: { color: cores.tinta, fontSize: 12, fontFamily: cores.fonte },
      formatter: (itens: { seriesName?: string; value: [number, number | null] }[]) => {
        const linhas = itens.filter((p) => p.seriesName)
        if (!linhas.length) return ''
        const corpo = linhas
          .map((p) => {
            const m = MEDIDAS.find((x) => x.nome === p.seriesName)!
            return `${p.seriesName}: <b style="font-family:${cores.fonteMono}">${formatarNumero(p.value[1], m.casas)}${m.unidade}</b>`
          })
          .join('<br/>')
        return `<span style="color:${cores.mudo}">${rotuloTempo(linhas[0].value[0])}</span><br/>${corpo}`
      },
    },
    series,
  }
}
