import { useCallback } from 'react'
import { useSobrepostas } from '../api/consultas'
import type { CoresGrafico } from '../graficos/aoVivo'
import { GraficoECharts } from '../graficos/GraficoECharts'
import { fimDoZoom, opcoesSobrepostas } from '../graficos/sobrepostas'
import { rotuloSegundos } from '../graficos/comum'
import { Secao } from '../layout/Secao'
import { useTema } from '../tema/TemaProvider'
import { CartaoGrafico } from './CartaoGrafico'
import type { PropsSecao } from './tipos'

const ALTURA = 560

/** Frente 2B: rodadas sobrepostas (plano, 4.4). */
export function SecaoRodadas({ filtros }: PropsSecao) {
  const { tema } = useTema()
  const sobrepostas = useSobrepostas(filtros)
  const n = sobrepostas.data?.length ?? 0
  const opcoes = useCallback(
    (cores: CoresGrafico, animar: boolean) => opcoesSobrepostas({ dados: sobrepostas.data ?? [], cores, tema, animar }),
    [sobrepostas.data, tema],
  )
  return (
    <Secao id="rodadas" titulo="Todas as rodadas juntas." descricao="Uma linha por rodada, colorida pelo caso.">
      <CartaoGrafico
        titulo="Todas as rodadas sobrepostas"
        descricao={`Umidade, MQ-135 e PPM de cada rodada desde a primeira leitura. Mostra até ${rotuloSegundos(fimDoZoom(sobrepostas.data ?? []))}; arraste a barra de baixo para ver o resto. O PPM é calculado pelo firmware e só aparece aqui, não decide nada.`}
        consulta={sobrepostas}
        vazio={n === 0 ? 'Sem leituras para os filtros escolhidos.' : undefined}
        altura={ALTURA}
      >
        <GraficoECharts opcoes={opcoes} rotulo={`${n} rodadas sobrepostas: umidade, MQ-135 e PPM ao longo do tempo`} altura={ALTURA} />
      </CartaoGrafico>
    </Secao>
  )
}
