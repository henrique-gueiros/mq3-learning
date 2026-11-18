import { useIsFetching } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { BarraFiltros } from './BarraFiltros'
import { Resumo } from './Resumo'
import { SecaoComparacao } from './SecaoComparacao'
import { SecaoRodada } from './SecaoRodada'
import { SecaoRodadas } from './SecaoRodadas'
import { SecaoSopros } from './SecaoSopros'
import type { PropsSecao } from './tipos'

/**
 * Rola até a seção do endereço (`/#sopros`) ao montar e mais uma vez quando as primeiras
 * consultas terminam: os gráficos acima chegam com outra altura e empurram a seção.
 * A segunda só acontece se a pessoa não rolou a página nesse meio-tempo.
 */
function useRolarAteAncora() {
  const buscando = useIsFetching()
  const etapa = useRef<'esperando' | 'buscou' | 'feito'>('esperando')
  const posicao = useRef<number | null>(null)
  const rolar = () => {
    const id = decodeURIComponent(window.location.hash.slice(1))
    const alvo = id ? document.getElementById(id) : null
    if (!alvo) return
    alvo.scrollIntoView()
    posicao.current = window.scrollY
  }
  useEffect(rolar, [])
  useEffect(() => {
    if (etapa.current === 'esperando' && buscando > 0) etapa.current = 'buscou'
    else if (etapa.current === 'buscou' && buscando === 0) {
      etapa.current = 'feito'
      if (posicao.current !== null && window.scrollY === posicao.current) rolar()
    }
  }, [buscando])
}

/**
 * Toda a análise abaixo do "Ao vivo". O `App` carrega este módulo sob demanda (`lazy`),
 * então ele chega depois da página: se o endereço aponta uma seção daqui (`/#sopros`),
 * o navegador não achou a âncora na carga e a rolagem é feita aqui.
 */
export function Analise({ filtros, aoMudarFiltros }: PropsSecao) {
  useRolarAteAncora()
  const props = { filtros, aoMudarFiltros }
  return (
    <div className="analise">
      <BarraFiltros filtros={filtros} aoMudar={aoMudarFiltros} />
      <Resumo filtros={filtros} />
      <SecaoComparacao {...props} />
      <SecaoRodadas {...props} />
      <SecaoRodada {...props} />
      <SecaoSopros {...props} />
    </div>
  )
}

export default Analise
