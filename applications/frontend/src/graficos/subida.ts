/**
 * Subida por sopro: um ponto por sopro marcado, com quanto o MQ-3 (x) e o MQ-135 (y)
 * subiram em relação à mediana dos 15 s antes do sopro (pico do sopro + 30 s).
 * Portado de `applications/grafana/paineis/subida.js`.
 */

import type { Sopro } from '../api/consultas'
import { corDoCaso, nomeDoCaso, ordenarCasos } from '../dominio/casos'
import { comSinal, formatarNumero } from '../dominio/formato'
import { animacao, dica, eixoValor, legenda, type EntradaGrafico, type Marca } from './comum'

export interface OpcoesSubida {
  xAxis: Marca & { name: string }
  yAxis: Marca & { name: string }
  series: { name: string; type: 'scatter'; data: [number, number][]; itemStyle: { color: string; [k: string]: unknown }; [k: string]: unknown }[]
  [k: string]: unknown
}

const rotuloSubida = (v: number) => comSinal(v, formatarNumero(Math.abs(v)))

/** Opções da dispersão da seção "Sopros marcados". */
export function opcoesSubida({ dados, cores, tema, animar = true }: EntradaGrafico<Sopro[]>): OpcoesSubida {
  return {
    ...animacao(animar),
    textStyle: { fontFamily: cores.fonte },
    legend: legenda(cores),
    grid: { left: 8, right: 16, top: 36, bottom: 28, containLabel: true },
    xAxis: eixoValor(cores, { name: 'subida do MQ-3', nameLocation: 'middle', nameGap: 28 }),
    yAxis: eixoValor(cores, { name: 'subida do MQ-135', nameLocation: 'middle', nameGap: 48 }),
    tooltip: dica(cores, {
      formatter: (x: { seriesName: string; value: [number, number] }) =>
        `<b>${x.seriesName}</b><br/>MQ-3 ${rotuloSubida(x.value[0])}<br/>MQ-135 ${rotuloSubida(x.value[1])}`,
    }),
    series: ordenarCasos(dados.map((d) => d.caso)).map((caso) => ({
      id: caso,
      name: nomeDoCaso(caso),
      type: 'scatter',
      symbolSize: 12,
      itemStyle: { color: corDoCaso(caso, tema), borderColor: cores.cartao, borderWidth: 2 },
      emphasis: { focus: 'series' },
      data: dados.filter((d) => d.caso === caso).map((d): [number, number] => [d.subida_mq3, d.subida_mq135]),
    })),
  }
}
