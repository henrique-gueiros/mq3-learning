import type { ReactNode } from 'react'
import { formatarNumero, formatarVariacao } from '../dominio/formato'
import './componentes.css'

/** Superfície padrão: cartão com anel de 1 px e sombra empilhada. */
export function Cartao({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`cartao ${className}`}>{children}</div>
}

/** Um número com o rótulo; a variação em relação à linha de base aparece embaixo. */
export function Stat({
  rotulo,
  valor,
  casas = 0,
  unidade,
  variacao,
  destaque = false,
}: {
  rotulo: string
  valor: number | null | undefined
  casas?: number
  unidade?: string
  variacao?: number | null
  destaque?: boolean
}) {
  return (
    <div className="stat" data-destaque={destaque || undefined}>
      <span className="stat-rotulo">{rotulo}</span>
      <span className="stat-valor mono">
        {formatarNumero(valor, casas)}
        {unidade && valor != null && <span className="stat-unidade">{unidade}</span>}
      </span>
      {variacao !== undefined && <span className="stat-variacao mono">{formatarVariacao(variacao)}</span>}
    </div>
  )
}

export type EstadoPlaca = 'recebendo' | 'parada' | 'offline' | 'aguardando' | 'sem-broker'

const TEXTO_PLACA: Record<EstadoPlaca, string> = {
  recebendo: 'Recebendo',
  parada: 'Sem leituras',
  offline: 'Placa offline',
  aguardando: 'Aguardando placa',
  'sem-broker': 'Sem conexão',
}

/** Situação da placa; o ponto pulsa enquanto chegam leituras. */
export function SeloPlaca({ estado }: { estado: EstadoPlaca }) {
  return (
    <span className="selo-placa" role="status" data-estado={estado}>
      <span className="selo-ponto" aria-hidden />
      {TEXTO_PLACA[estado]}
    </span>
  )
}
