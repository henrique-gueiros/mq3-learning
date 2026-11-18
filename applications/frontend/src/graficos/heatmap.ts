/**
 * Heatmap divergente casos × sensores: quanto a média de cada caso difere da média do
 * ambiente (`clean`), em %. Abaixo do ambiente puxa para a cor do ambiente, acima para a
 * da bebida, e o meio é cinza neutro (regra da skill `dataviz` para escalas divergentes).
 * Portado de `applications/grafana/paineis/variacao.js`.
 */

import type { CelulaHeatmap } from '../api/consultas'
import { corDoCaso, nomeDoCaso, ordenarCasos } from '../dominio/casos'
import { comSinal } from '../dominio/formato'
import { animacao, dica, eixoCategoria, type EntradaGrafico, type Marca } from './comum'

const SENSORES: { chave: 'mq3' | 'mq135' | 'umid'; rotulo: string }[] = [
  { chave: 'mq3', rotulo: 'MQ-3' },
  { chave: 'mq135', rotulo: 'MQ-135' },
  { chave: 'umid', rotulo: 'Umidade (%)' },
]

/** `[índice do sensor, índice do caso, % arredondado]`. */
export type Celula = [number, number, number]

/** Casos na ordem do protocolo e uma célula por valor presente. */
export function celulasHeatmap(dados: CelulaHeatmap[]): { casos: string[]; celulas: Celula[] } {
  const casos = ordenarCasos(dados.map((d) => d.caso))
  const celulas: Celula[] = []
  casos.forEach((caso, linha) => {
    const d = dados.find((x) => x.caso === caso)!
    SENSORES.forEach(({ chave }, coluna) => {
      const v = d[chave]
      if (v != null && !Number.isNaN(v)) celulas.push([coluna, linha, Math.round(v)])
    })
  })
  return { casos, celulas }
}

/** Escala simétrica no maior |valor|, com mínimo de 10 para diferenças pequenas não parecerem enormes. */
export function limiteHeatmap(celulas: Celula[]): number {
  return Math.max(10, ...celulas.map((c) => Math.abs(c[2])))
}

/** Altura do gráfico: cresce com o número de casos (linhas). */
export const alturaHeatmap = (casos: number) => Math.max(220, 96 + 44 * casos)

/** `+81%`, `−3%` (sinal tipográfico), `0%`. */
const rotuloPercentual = (v: number) => comSinal(v, `${Math.abs(v)}%`)

export interface OpcoesHeatmap {
  xAxis: Marca & { data: string[] }
  yAxis: Marca & { data: string[] }
  visualMap: { min: number; max: number; inRange: { color: string[] }; [k: string]: unknown }
  series: { type: 'heatmap'; data: Celula[]; label: { formatter: (x: { value: Celula }) => string; [k: string]: unknown }; [k: string]: unknown }[]
  [k: string]: unknown
}

/** Opções do heatmap da seção "Comparação entre os casos". */
export function opcoesHeatmap({ dados, cores, tema, animar = true }: EntradaGrafico<CelulaHeatmap[]>): OpcoesHeatmap {
  const { casos, celulas } = celulasHeatmap(dados)
  const limite = limiteHeatmap(celulas)
  return {
    ...animacao(animar),
    textStyle: { fontFamily: cores.fonte },
    grid: { left: 0, right: 8, top: 4, bottom: 52, containLabel: true },
    xAxis: eixoCategoria(cores, SENSORES.map((s) => s.rotulo), { position: 'top', axisLine: { show: false }, splitArea: { show: false } }),
    yAxis: eixoCategoria(cores, casos.map(nomeDoCaso), { inverse: true, axisLine: { show: false } }),
    visualMap: {
      min: -limite,
      max: limite,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 12,
      itemHeight: 160,
      text: ['acima do ambiente', 'abaixo'],
      textStyle: { color: cores.mudo, fontFamily: cores.fonte, fontSize: 11 },
      inRange: { color: [corDoCaso('clean', tema), cores.neutro ?? cores.linha, corDoCaso('drink', tema)] },
    },
    tooltip: dica(cores, {
      formatter: (x: { value: Celula }) =>
        `<b>${nomeDoCaso(casos[x.value[1]])} · ${SENSORES[x.value[0]].rotulo}</b><br/>${rotuloPercentual(x.value[2])} em relação ao ambiente`,
    }),
    series: [
      {
        id: 'variacao',
        type: 'heatmap',
        data: celulas,
        itemStyle: { borderColor: cores.cartao, borderWidth: 2, borderRadius: 4 },
        emphasis: { itemStyle: { borderColor: cores.tinta } },
        label: {
          show: true,
          color: cores.tinta,
          fontFamily: cores.fonteMono,
          fontSize: 12,
          formatter: (x: { value: Celula }) => rotuloPercentual(x.value[2]),
        },
      },
    ],
  }
}
