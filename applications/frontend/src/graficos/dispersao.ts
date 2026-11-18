/**
 * Dispersão MQ-3 (x) × MQ-135 (y), um ponto por leitura, uma série por caso. Se os casos
 * formam grupos separados, os dois sensores juntos já os distinguem.
 * Portado de `applications/grafana/paineis/separacao.js`.
 */

import type { PontoDispersao } from '../api/consultas'
import { corDoCaso, nomeDoCaso, ordenarCasos } from '../dominio/casos'
import { formatarNumero } from '../dominio/formato'
import { animacao, comAlfa, dica, eixoValor, legenda, type EntradaGrafico, type Marca } from './comum'

export interface OpcoesDispersao {
  legend: Marca
  xAxis: Marca & { name: string }
  yAxis: Marca & { name: string }
  series: { name: string; type: 'scatter'; data: [number, number][]; itemStyle: { color: string; [k: string]: unknown }; [k: string]: unknown }[]
  [k: string]: unknown
}

/** Opções da dispersão da seção "Comparação entre os casos". */
export function opcoesDispersao({ dados, cores, tema, animar = true }: EntradaGrafico<PontoDispersao[]>): OpcoesDispersao {
  const casos = ordenarCasos(dados.map((d) => d.caso))
  return {
    ...animacao(animar),
    textStyle: { fontFamily: cores.fonte },
    legend: legenda(cores),
    grid: { left: 28, right: 16, top: 36, bottom: 28, containLabel: true },
    xAxis: eixoValor(cores, { name: 'MQ-3 (leitura bruta)', nameLocation: 'middle', nameGap: 28, scale: true }),
    yAxis: eixoValor(cores, { name: 'MQ-135 (leitura bruta)', nameLocation: 'middle', nameGap: 44, scale: true }),
    tooltip: dica(cores, {
      formatter: (x: { seriesName: string; value: [number, number] }) =>
        `<b>${x.seriesName}</b><br/>MQ-3 ${formatarNumero(x.value[0])}<br/>MQ-135 ${formatarNumero(x.value[1])}`,
    }),
    series: casos.map((caso) => ({
      name: nomeDoCaso(caso),
      type: 'scatter',
      symbolSize: 6,
      large: true,
      itemStyle: { color: comAlfa(corDoCaso(caso, tema), 0.6) },
      emphasis: { focus: 'series' },
      data: dados.filter((d) => d.caso === caso).map((d): [number, number] => [d.mq3_raw, d.mq135_raw]),
    })),
  }
}
