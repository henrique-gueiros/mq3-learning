import { useCallback, useEffect, useMemo } from 'react'
import { useFiltros, useLeiturasRodada } from '../api/consultas'
import { corDoCaso } from '../dominio/casos'
import type { CoresGrafico } from '../graficos/aoVivo'
import { GraficoECharts } from '../graficos/GraficoECharts'
import { opcoesRodada } from '../graficos/rodada'
import { Secao } from '../layout/Secao'
import { useTema } from '../tema/TemaProvider'
import { CartaoGrafico } from './CartaoGrafico'
import { escolherRodada, rodadasVisiveis, rotuloRodada } from './rodadas'
import type { PropsSecao } from './tipos'

const ALTURA = 480

/** Frente 2C: rodada selecionada, guardada em `filtros.rodada` (plano, 4.5). */
export function SecaoRodada({ filtros, aoMudarFiltros }: PropsSecao) {
  const { tema } = useTema()
  const opcoes = useFiltros()
  const visiveis = useMemo(() => rodadasVisiveis(opcoes.data?.rodadas ?? [], filtros.simulador), [opcoes.data, filtros.simulador])
  const id = escolherRodada(filtros.rodada, visiveis)
  const escolhida = visiveis.find((r) => r.id === id)
  const leituras = useLeiturasRodada(id)

  // a escolhida saiu da lista (ex.: era do simulador e o interruptor desligou): a URL volta à mais recente
  const sumiu = opcoes.data !== undefined && filtros.rodada !== null && filtros.rodada !== id
  useEffect(() => {
    if (sumiu) aoMudarFiltros({ rodada: null })
  }, [sumiu, aoMudarFiltros])

  const fRodada = useCallback(
    (cores: CoresGrafico, animar: boolean) =>
      opcoesRodada({ dados: leituras.data ?? { rodada: '', caso: '', pontos: [] }, cores, tema, animar }),
    [leituras.data, tema],
  )

  const semRodadas = opcoes.data !== undefined && visiveis.length === 0
  const vazio = semRodadas
    ? 'Nenhuma rodada gravada ainda. Rode a ponte ou importe um CSV.'
    : leituras.data?.pontos.length === 0
      ? 'Esta rodada não tem leituras.'
      : undefined

  const seletor = visiveis.length > 0 && (
    <label className="seletor-rodada">
      <span className="seletor-rodada-rotulo">Rodada</span>
      <span className="seletor-rodada-caixa">
        {escolhida && <span className="chip-cor seletor-rodada-cor" style={{ background: corDoCaso(escolhida.caso, tema) }} aria-hidden />}
        <select value={id ?? ''} onChange={(e) => aoMudarFiltros({ rodada: e.target.value })}>
          {visiveis.map((r) => (
            <option key={r.id} value={r.id}>
              {rotuloRodada(r)}
            </option>
          ))}
        </select>
      </span>
    </label>
  )

  return (
    <Secao
      id="rodada"
      titulo="Rodada selecionada."
      descricao="Os três sensores de uma rodada, com as janelas de sopro."
      acoes={seletor || undefined}
    >
      <CartaoGrafico
        titulo={escolhida ? rotuloRodada(escolhida) : 'Leituras da rodada'}
        descricao="Um gráfico por sensor. A faixa cinza é a janela de sopro (sopro + 30 s), quando há sopro marcado."
        consulta={opcoes.data === undefined || semRodadas ? opcoes : leituras}
        vazio={vazio}
        altura={ALTURA}
      >
        <GraficoECharts
          opcoes={fRodada}
          rotulo={`Leituras de MQ-3, MQ-135 e umidade da rodada ${escolhida ? rotuloRodada(escolhida) : ''}`}
          altura={ALTURA}
        />
      </CartaoGrafico>
    </Secao>
  )
}
