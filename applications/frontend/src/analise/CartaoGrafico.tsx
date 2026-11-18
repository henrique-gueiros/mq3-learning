import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Cartao } from '../componentes/exibicao'
import './analise.css'

/** O que o cartão precisa de uma consulta do TanStack Query. */
export type ConsultaMinima = Pick<UseQueryResult, 'isError' | 'error' | 'refetch'> & {
  /** Carregando pela primeira vez (`isLoading`; consulta desligada não conta). */
  isLoading: boolean
  /** Se já há dados, uma falha ao atualizar não troca o gráfico pelo erro. */
  data?: unknown
  /** Dados do filtro anterior, mostrados enquanto os do filtro novo chegam. */
  isPlaceholderData?: boolean
}

/**
 * Cartão de um gráfico com os três estados: skeleton enquanto carrega, mensagem
 * quando `vazio` é dado (texto) e erro com "Tentar de novo". Só com dados e sem
 * `vazio` mostra os `children`; com os dados do filtro anterior, esmaecidos.
 */
export function CartaoGrafico({
  titulo,
  descricao,
  consulta,
  vazio,
  children,
  className = '',
  altura,
}: {
  titulo: string
  descricao?: string
  consulta: ConsultaMinima
  /** Mensagem quando a consulta veio sem dados; deixe `undefined` se há o que desenhar. */
  vazio?: string
  children: ReactNode
  className?: string
  /** Altura do gráfico em px: o skeleton a reserva, para a página não pular quando os dados chegam. */
  altura?: number
}) {
  let corpo: ReactNode
  if (consulta.isError && consulta.data === undefined) {
    corpo = (
      <div className="grafico-estado grafico-erro" role="alert">
        <p className="corpo-sm">{consulta.error instanceof Error ? consulta.error.message : 'Não foi possível carregar.'}</p>
        <button type="button" className="botao-tentar" onClick={() => void consulta.refetch()}>
          Tentar de novo
        </button>
      </div>
    )
  } else if (consulta.isLoading) {
    corpo = (
      <div
        className="grafico-estado grafico-skeleton"
        role="status"
        aria-label="Carregando o gráfico"
        style={altura ? { minHeight: altura } : undefined}
      />
    )
  } else if (vazio) {
    corpo = (
      <div className="grafico-estado">
        <p className="corpo-sm">{vazio}</p>
      </div>
    )
  } else {
    const atualizando = consulta.isPlaceholderData === true
    corpo = (
      <div className={`grafico-corpo${atualizando ? ' atualizando' : ''}`} aria-busy={atualizando}>
        {children}
      </div>
    )
  }
  return (
    <Cartao className={`cartao-grafico ${className}`}>
      <h3 className="cartao-grafico-titulo">{titulo}</h3>
      {descricao && <p className="corpo-sm cartao-grafico-descricao">{descricao}</p>}
      {corpo}
    </Cartao>
  )
}
