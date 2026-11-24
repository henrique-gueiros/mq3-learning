/**
 * Todas as rodadas juntas: uma linha por rodada, colorida pelo caso, em três grades
 * empilhadas (Umidade, MQ-135, PPM). O tempo é contado desde a primeira leitura de
 * cada rodada. O PPM é só exibido (regra do AGENTS.md: não decide nada).
 * Portado do antigo painel do Grafana (removido em 24/11/2026).
 */

import type { SerieSobreposta } from '../api/consultas'
import { corDoCaso, nomeDoCaso, ordenarCasos } from '../dominio/casos'
import { formatarNumero } from '../dominio/formato'
import type { Serie } from './aoVivo'
import { animacao, comAlfa, dica, gradesEmpilhadas, legenda, rotuloSegundos, type EntradaGrafico, type Marca } from './comum'

/** Posição de cada medida em `PontoSobreposto` e casas decimais na dica. */
const MEDIDAS = [
  { rotulo: 'Umidade (%)', indice: 1, casas: 1 },
  { rotulo: 'MQ-135', indice: 2, casas: 0 },
  { rotulo: 'PPM', indice: 3, casas: 2 },
] as const

/** Mínimo da janela inicial: os sopros cabem nos primeiros 5 min. */
export const ZOOM_MINIMO_S = 300

/**
 * Fim do zoom inicial, em segundos: o fim da rodada mais longa que não é ambiente,
 * arredondado para cima ao minuto, nunca abaixo de 5 min. Uma rodada de ambiente de
 * horas não manda na janela (continua no gráfico; a barra mostra o resto). Sem
 * rodada fora do ambiente, usa todas.
 */
export function fimDoZoom(dados: SerieSobreposta[]): number {
  const fora = dados.filter((r) => r.caso !== 'clean')
  const base = fora.length ? fora : dados
  const fim = base.reduce((maior, r) => Math.max(maior, ...r.pontos.map((p) => p[0])), 0)
  return Math.max(ZOOM_MINIMO_S, Math.ceil(fim / 60) * 60)
}

const LINHAS_NA_DICA = 8

export interface OpcoesSobrepostas {
  title: Marca[]
  grid: Marca[]
  legend: Marca & { data: string[] }
  dataZoom: (Marca & { startValue: number; endValue: number; xAxisIndex: number[] })[]
  series: Serie[]
  [k: string]: unknown
}

/** Opções da seção "Todas as rodadas juntas". */
export function opcoesSobrepostas({ dados, cores, tema, animar = true }: EntradaGrafico<SerieSobreposta[]>): OpcoesSobrepostas {
  const grades = gradesEmpilhadas(cores, MEDIDAS.map((m) => m.rotulo), { topo: 8, fundo: 6 })
  const todas = MEDIDAS.map((_, i) => i)

  const series: Serie[] = MEDIDAS.flatMap((m, i) =>
    dados.map((r) => ({
      id: `${r.rodada}-${i}`,
      name: nomeDoCaso(r.caso),
      type: 'line',
      xAxisIndex: i,
      yAxisIndex: i,
      showSymbol: false,
      sampling: 'lttb',
      connectNulls: false,
      lineStyle: { color: corDoCaso(r.caso, tema), width: 1.4, opacity: 0.75 },
      itemStyle: { color: corDoCaso(r.caso, tema) },
      emphasis: { focus: 'series', lineStyle: { width: 2.4, opacity: 1 } },
      data: r.pontos.map((p) => [p[0], p[m.indice]]),
    })),
  )

  const zoom = { xAxisIndex: todas, startValue: 0, endValue: fimDoZoom(dados), filterMode: 'none' }

  return {
    ...animacao(animar),
    textStyle: { fontFamily: cores.fonte },
    ...grades,
    legend: legenda(cores, { left: 'auto', right: 0, data: ordenarCasos(dados.map((r) => r.caso)).map(nomeDoCaso) }),
    dataZoom: [
      { type: 'inside', ...zoom },
      {
        type: 'slider',
        ...zoom,
        bottom: 4,
        height: 22,
        borderColor: cores.linha,
        fillerColor: comAlfa(cores.tinta, 0.14),
        handleStyle: { color: cores.tinta, borderColor: cores.tinta },
        moveHandleStyle: { color: cores.mudo },
        dataBackground: { lineStyle: { color: cores.mudo, opacity: 0.6 }, areaStyle: { color: 'transparent' } },
        textStyle: { color: cores.mudo, fontFamily: cores.fonteMono, fontSize: 11 },
        labelFormatter: (v: number) => rotuloSegundos(v),
      },
    ],
    axisPointer: { link: [{ xAxisIndex: 'all' }], lineStyle: { color: cores.corpo, width: 1 } },
    tooltip: dica(cores, {
      trigger: 'axis',
      formatter: (itens: { seriesName: string; seriesIndex: number; color: string; value: [number, number | null] }[]) => {
        if (!itens.length) return ''
        // as séries vêm em blocos de uma grade (medida) por vez, na ordem de MEDIDAS
        const medida = (seriesIndex: number) => MEDIDAS[Math.floor(seriesIndex / Math.max(1, dados.length))] ?? MEDIDAS[0]
        const visiveis = itens.filter((p) => p.value[1] != null)
        const linhas = visiveis.slice(0, LINHAS_NA_DICA).map((p) => {
          const m = medida(p.seriesIndex)
          return `<span style="color:${p.color}">●</span> ${m.rotulo} · ${p.seriesName}: ${formatarNumero(p.value[1], m.casas)}`
        })
        const resto = visiveis.length - linhas.length
        return [`<span style="color:${cores.mudo}">${rotuloSegundos(itens[0].value[0])}</span>`, ...linhas, ...(resto > 0 ? [`+${resto} rodadas`] : [])].join('<br/>')
      },
    }),
    series,
  }
}
