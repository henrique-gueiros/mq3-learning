/**
 * Boxplot por caso, um gráfico por sensor (MQ-3, MQ-135, Umidade), lado a lado.
 * Caixa do 1º ao 3º quartil com a mediana; bigodes nos percentis 5 e 95; losango na média.
 * Portado de `applications/grafana/paineis/distribuicao.js`.
 */

import type { DistribuicaoCaso, Percentis } from '../api/consultas'
import { corDoCaso, nomeDoCaso, ordenarCasos } from '../dominio/casos'
import { formatarNumero } from '../dominio/formato'
import type { Serie } from './aoVivo'
import { animacao, comAlfa, dica, eixoCategoria, eixoValor, tituloGrade, type EntradaGrafico, type Marca } from './comum'

type Chave = 'mq3' | 'mq135' | 'umid'

export const SENSORES_DISTRIBUICAO: { chave: Chave; rotulo: string; casas: number }[] = [
  { chave: 'mq3', rotulo: 'MQ-3', casas: 0 },
  { chave: 'mq135', rotulo: 'MQ-135', casas: 0 },
  { chave: 'umid', rotulo: 'Umidade (%)', casas: 1 },
]

const caixa = (p: Percentis) => [p.p5, p.p25, p.p50, p.p75, p.p95]

export interface OpcoesDistribuicao {
  title: Marca[]
  grid: Marca[]
  xAxis: (Marca & { data: string[] })[]
  yAxis: Marca[]
  series: Serie[]
  [k: string]: unknown
}

/** Altura do gráfico: as três grades lado a lado ou empilhadas (tela estreita). */
export const alturaDistribuicao = (empilhado: boolean) => (empilhado ? 720 : 340)

/**
 * Opções do boxplot da seção "Comparação entre os casos". `empilhado` põe as três
 * grades uma embaixo da outra, para caber no celular.
 */
export function opcoesDistribuicao({
  dados,
  cores,
  tema,
  animar = true,
  empilhado = false,
}: EntradaGrafico<DistribuicaoCaso[]> & { empilhado?: boolean }): OpcoesDistribuicao {
  const linhas = ordenarCasos(dados.map((d) => d.caso)).map((c) => dados.find((d) => d.caso === c)!)
  const nomes = linhas.map((l) => nomeDoCaso(l.caso))
  const cor = (caso: string) => corDoCaso(caso, tema)

  const title: Marca[] = []
  const grid: Marca[] = []
  const xAxis: OpcoesDistribuicao['xAxis'] = []
  const yAxis: Marca[] = []
  const series: Serie[] = []

  SENSORES_DISTRIBUICAO.forEach(({ chave, rotulo, casas }, i) => {
    if (empilhado) {
      const topo = (i * 100) / 3
      title.push(tituloGrade(cores, rotulo, { left: 0, top: `${topo}%` }))
      // à direita cabe o número da média da última caixa
      grid.push({ left: 0, right: 44, top: `${topo + 4}%`, height: '24%', containLabel: true })
    } else {
      const esquerda = `${i * 34}%`
      title.push(tituloGrade(cores, rotulo, { left: esquerda, top: 0 }))
      grid.push({ left: esquerda, width: '30%', top: 32, bottom: 8, containLabel: true })
    }
    xAxis.push(eixoCategoria(cores, nomes, { gridIndex: i, axisLabel: { color: cores.corpo, fontFamily: cores.fonte, fontSize: 11, interval: 0, rotate: nomes.length > 3 ? 30 : 0 } }))
    yAxis.push(eixoValor(cores, { gridIndex: i, scale: true, splitNumber: 4 }))
    const f = (v: number | null) => formatarNumero(v, casas)
    series.push({
      id: `caixa-${chave}`,
      name: rotulo,
      type: 'boxplot',
      xAxisIndex: i,
      yAxisIndex: i,
      boxWidth: [10, 36],
      data: linhas.map((l) => ({
        value: caixa(l[chave]),
        itemStyle: { color: comAlfa(cor(l.caso), 0.22), borderColor: cor(l.caso), borderWidth: 2 },
      })),
      tooltip: {
        formatter: ({ dataIndex: k }: { dataIndex: number }) => {
          const l = linhas[k]
          const p = l[chave]
          return (
            `<b>${rotulo} · ${nomes[k]}</b><br/>${formatarNumero(l.n)} leituras<br/>` +
            `mediana ${f(p.p50)}<br/>` +
            `quartis ${f(p.p25)} a ${f(p.p75)}<br/>` +
            `percentis 5 a 95: ${f(p.p5)} a ${f(p.p95)}<br/>` +
            `média ${f(p.media)}`
          )
        },
      },
    })
    series.push({
      id: `media-${chave}`,
      name: `${rotulo} (média)`,
      type: 'scatter',
      xAxisIndex: i,
      yAxisIndex: i,
      symbol: 'diamond',
      symbolSize: 11,
      z: 10,
      data: linhas.map((l, k) => ({
        value: [nomes[k], l[chave].media],
        itemStyle: { color: cor(l.caso), borderColor: cores.cartao, borderWidth: 2 },
      })),
      label: {
        show: true,
        position: 'right',
        // fora da caixa (meia largura máxima de 18 px), para o número não cruzar a borda
        distance: 22,
        color: cores.tinta,
        fontFamily: cores.fonteMono,
        fontSize: 10,
        formatter: (x: { value: [string, number | null] }) => f(x.value[1]),
      },
      tooltip: { show: false },
    })
  })

  return { ...animacao(animar), textStyle: { fontFamily: cores.fonte }, title, grid, xAxis, yAxis, series, tooltip: dica(cores, { trigger: 'item' }) }
}
