/**
 * Uma rodada: MQ-3, MQ-135 e Umidade em grades empilhadas, na cor do caso, com faixa
 * cinza onde a leitura cai na janela de sopro (sopro + 30 s).
 * Portado do antigo painel do Grafana (removido em 24/11/2026).
 */

import type { LeiturasRodada, PontoRodada } from '../api/consultas'
import { corDoCaso } from '../dominio/casos'
import { formatarNumero } from '../dominio/formato'
import type { Serie } from './aoVivo'
import { animacao, comAlfa, dica, gradesEmpilhadas, rotuloSegundos, type EntradaGrafico, type Marca } from './comum'

const SENSORES: { campo: 'mq3_raw' | 'mq135_raw' | 'humidity_pct'; rotulo: string; casas: number }[] = [
  { campo: 'mq3_raw', rotulo: 'MQ-3', casas: 0 },
  { campo: 'mq135_raw', rotulo: 'MQ-135', casas: 0 },
  { campo: 'humidity_pct', rotulo: 'Umidade (%)', casas: 1 },
]

/** Trechos contíguos com `em_sopro`, como `[tempo da primeira, tempo da última]`. */
export function faixasDeSopro(pontos: PontoRodada[]): [number, number][] {
  const faixas: [number, number][] = []
  let inicio: number | null = null
  pontos.forEach((p, k) => {
    if (p.em_sopro && inicio === null) inicio = p.tempo_s
    if (!p.em_sopro && inicio !== null) {
      faixas.push([inicio, pontos[k - 1].tempo_s])
      inicio = null
    }
  })
  if (inicio !== null) faixas.push([inicio, pontos[pontos.length - 1].tempo_s])
  return faixas
}

export interface OpcoesRodada {
  grid: Marca[]
  series: Serie[]
  [k: string]: unknown
}

/** Opções da seção "Rodada selecionada". */
export function opcoesRodada({ dados, cores, tema, animar = true }: EntradaGrafico<LeiturasRodada>): OpcoesRodada {
  const cor = corDoCaso(dados.caso, tema)
  const faixas = faixasDeSopro(dados.pontos).map(([a, b]): [Marca, Marca] => [{ xAxis: a }, { xAxis: b }])
  return {
    ...animacao(animar),
    textStyle: { fontFamily: cores.fonte },
    ...gradesEmpilhadas(cores, SENSORES.map((s) => s.rotulo), { topo: 2, fundo: 4 }),
    axisPointer: { link: [{ xAxisIndex: 'all' }], lineStyle: { color: cores.corpo, width: 1 } },
    tooltip: dica(cores, {
      trigger: 'axis',
      formatter: (itens: { seriesName: string; value: [number, number | null] }[]) => {
        if (!itens.length) return ''
        const linhas = itens.map((p) => {
          const s = SENSORES.find((x) => x.rotulo === p.seriesName)!
          return `${p.seriesName}: ${formatarNumero(p.value[1], s.casas)}`
        })
        return [`<span style="color:${cores.mudo}">${rotuloSegundos(itens[0].value[0])}</span>`, ...linhas].join('<br/>')
      },
    }),
    series: SENSORES.map((s, i) => ({
      id: s.campo,
      name: s.rotulo,
      type: 'line',
      xAxisIndex: i,
      yAxisIndex: i,
      showSymbol: false,
      connectNulls: false,
      lineStyle: { color: cor, width: 2 },
      itemStyle: { color: cor },
      emphasis: { disabled: true },
      data: dados.pontos.map((p) => [p.tempo_s, p[s.campo]]),
      markArea: { silent: true, itemStyle: { color: comAlfa(cores.tinta, 0.1) }, data: faixas },
    })),
  }
}
