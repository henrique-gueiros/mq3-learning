import { BoxplotChart, HeatmapChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import { useEffect, useMemo, useState } from 'react'
import { useTema } from '../tema/TemaProvider'
import type { CoresGrafico } from './aoVivo'
import { coresDoTema, semMovimento } from './temaEcharts'

// Todos os módulos que os gráficos de análise usam ficam registrados aqui, num lugar só.
echarts.use([
  BoxplotChart,
  HeatmapChart,
  ScatterChart,
  LineChart,
  VisualMapComponent,
  DataZoomComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
  GridComponent,
  TitleComponent,
  AxisPointerComponent,
  CanvasRenderer,
])

type Opcoes = Parameters<ReturnType<typeof echarts.init>['setOption']>[0]

// Trocados a cada desenho: as séries mudam com os casos do filtro, e grades e títulos mudam de
// layout no boxplot empilhado (no merge comum sobrariam séries velhas e o `width` antigo da grade).
// Eixos e zoom seguem no merge comum, que preserva o zoom escolhido ao trocar de filtro.
const SUBSTITUIR = ['series', 'grid', 'title']

/**
 * Gráfico genérico. `opcoes` é uma função pura (de `src/graficos/`) que recebe as cores
 * do tema atual e diz se pode animar; ela deve ter identidade estável (módulo ou
 * `useCallback`) para o gráfico só redesenhar quando os dados mudarem.
 */
export function GraficoECharts({
  opcoes,
  rotulo,
  altura = 360,
}: {
  opcoes: (cores: CoresGrafico, animar: boolean) => Opcoes
  /** Descrição para leitores de tela. */
  rotulo: string
  altura?: number
}) {
  const { tema } = useTema()
  // os tokens são lidos do CSS depois que o tema foi aplicado no <html> (efeito roda após o commit)
  const [cores, setCores] = useState(() => coresDoTema())
  useEffect(() => {
    const novas = coresDoTema()
    // só troca se algo mudou: evita um segundo desenho logo na montagem
    setCores((atuais) => (JSON.stringify(atuais) === JSON.stringify(novas) ? atuais : novas))
  }, [tema])
  const option = useMemo(() => opcoes(cores, !semMovimento()), [opcoes, cores])
  return (
    <div role="img" aria-label={rotulo} style={{ height: altura, width: '100%' }}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        style={{ height: '100%', width: '100%' }}
        notMerge={false}
        replaceMerge={SUBSTITUIR}
        lazyUpdate
      />
    </div>
  )
}
