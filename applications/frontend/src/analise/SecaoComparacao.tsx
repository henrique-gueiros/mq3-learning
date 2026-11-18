import { useCallback } from 'react'
import { useDispersao, useDistribuicao, useHeatmap } from '../api/consultas'
import type { CoresGrafico } from '../graficos/aoVivo'
import { opcoesDispersao } from '../graficos/dispersao'
import { alturaDistribuicao, opcoesDistribuicao } from '../graficos/distribuicao'
import { GraficoECharts } from '../graficos/GraficoECharts'
import { alturaHeatmap, opcoesHeatmap } from '../graficos/heatmap'
import { Secao } from '../layout/Secao'
import { useMidia } from '../layout/useMidia'
import { useTema } from '../tema/TemaProvider'
import { CartaoGrafico } from './CartaoGrafico'
import type { PropsSecao } from './tipos'

const SEM_LEITURAS = 'Sem leituras para os filtros escolhidos.'
const ALTURA_DISPERSAO = 320

/** O heatmap compara com o ambiente: vazio porque falta ambiente, ou porque só ele está marcado. */
const vazioHeatmap = (casos: string[]) =>
  casos.length === 1 && casos[0] === 'clean'
    ? 'Marque outro caso além de ambiente para comparar com ele.'
    : 'Precisa de rodadas de ambiente para comparar.'

/** Frente 2A: boxplot, heatmap e dispersão (plano, 4.3). */
export function SecaoComparacao({ filtros }: PropsSecao) {
  const { tema } = useTema()
  const distribuicao = useDistribuicao(filtros)
  const heatmap = useHeatmap(filtros)
  const dispersao = useDispersao(filtros)

  const estreita = useMidia('(max-width: 640px)')

  const fDistribuicao = useCallback(
    (cores: CoresGrafico, animar: boolean) =>
      opcoesDistribuicao({ dados: distribuicao.data ?? [], cores, tema, animar, empilhado: estreita }),
    [distribuicao.data, tema, estreita],
  )
  const fHeatmap = useCallback(
    (cores: CoresGrafico, animar: boolean) => opcoesHeatmap({ dados: heatmap.data ?? [], cores, tema, animar }),
    [heatmap.data, tema],
  )
  const fDispersao = useCallback(
    (cores: CoresGrafico, animar: boolean) => opcoesDispersao({ dados: dispersao.data ?? [], cores, tema, animar }),
    [dispersao.data, tema],
  )

  return (
    <Secao
      id="comparacao"
      titulo="Comparação entre os casos."
      descricao="Como cada sensor se comporta em ambiente, bebida, perfume e nos outros casos."
    >
      <div className="grade-analise">
        <CartaoGrafico
          className="grade-inteira"
          titulo="Distribuição das leituras por caso"
          descricao="Caixa: do 1º ao 3º quartil, com a mediana. Linhas: percentis 5 e 95. Losango: média."
          consulta={distribuicao}
          vazio={distribuicao.data?.length === 0 ? SEM_LEITURAS : undefined}
          altura={alturaDistribuicao(estreita)}
        >
          <GraficoECharts opcoes={fDistribuicao} rotulo="Boxplot da distribuição de MQ-3, MQ-135 e umidade por caso" altura={alturaDistribuicao(estreita)} />
        </CartaoGrafico>
        <CartaoGrafico
          className="grade-estreita"
          titulo="Média em relação ao ambiente"
          descricao="Quanto a média de cada caso difere da do ambiente (ar sem álcool), por sensor."
          consulta={heatmap}
          vazio={heatmap.data?.length === 0 ? vazioHeatmap(filtros.casos) : undefined}
          altura={alturaHeatmap(heatmap.data?.length ?? 0)}
        >
          <GraficoECharts
            opcoes={fHeatmap}
            rotulo="Heatmap da média de cada caso em relação ao ambiente"
            altura={alturaHeatmap(heatmap.data?.length ?? 0)}
          />
        </CartaoGrafico>
        <CartaoGrafico
          className="grade-larga"
          titulo="MQ-3 × MQ-135 por leitura"
          descricao="Até 400 leituras por caso. Se os casos formam grupos separados, os dois sensores já os distinguem."
          consulta={dispersao}
          vazio={dispersao.data?.length === 0 ? SEM_LEITURAS : undefined}
          altura={ALTURA_DISPERSAO}
        >
          <GraficoECharts opcoes={fDispersao} rotulo="Dispersão MQ-3 × MQ-135 por leitura, colorida pelo caso" altura={ALTURA_DISPERSAO} />
        </CartaoGrafico>
      </div>
    </Secao>
  )
}
