import { LineChart } from 'echarts/charts'
import { AxisPointerComponent, GridComponent, MarkAreaComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import { useEffect, useMemo, useState } from 'react'
import { opcoesAoVivo } from '../../graficos/aoVivo'
import { coresDoTema, semMovimento } from '../../graficos/temaEcharts'
import { useTema } from '../../tema/TemaProvider'
import type { Base } from '../detector'
import type { Trecho } from '../estado'
import type { Janela } from '../janelas'
import type { Leitura } from '../mensagens'

echarts.use([LineChart, GridComponent, TooltipComponent, AxisPointerComponent, MarkAreaComponent, MarkLineComponent, CanvasRenderer])

/** PPM, MQ-135 e umidade ao vivo, empilhados no mesmo tempo. */
export function GraficoAoVivo({
  leituras,
  base,
  trechos,
  marcadas,
  corDaRodada,
}: {
  leituras: Leitura[]
  base: Base | null
  trechos: Trecho[]
  marcadas: Janela[]
  corDaRodada?: string
}) {
  const { tema } = useTema()
  // os tokens são lidos do CSS depois que o tema foi aplicado no <html> (efeito roda após o commit)
  const [cores, setCores] = useState(() => coresDoTema(corDaRodada))
  useEffect(() => setCores(coresDoTema(corDaRodada)), [tema, corDaRodada])
  const opcoes = useMemo(
    () => opcoesAoVivo({ leituras, base, trechos, marcadas, cores, animar: !semMovimento() }),
    [leituras, base, trechos, marcadas, cores],
  )
  return (
    <div className="grafico-aovivo" role="img" aria-label="Gráfico ao vivo de PPM, MQ-135 e umidade nos últimos 3 minutos">
      <ReactEChartsCore echarts={echarts} option={opcoes} style={{ height: '100%', width: '100%' }} notMerge={false} lazyUpdate />
    </div>
  )
}
