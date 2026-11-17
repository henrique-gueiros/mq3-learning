import { useResumo } from '../api/consultas'
import { Stat } from '../componentes/exibicao'
import type { Filtros } from './filtros'
import './analise.css'

/**
 * Total de rodadas e de leituras dos filtros atuais. Carregando mostra traço; com a
 * API fora mostra traço e a mensagem do erro, para não parecer que ainda está carregando.
 */
export function Resumo({ filtros }: { filtros: Filtros }) {
  const { data, isError, error } = useResumo(filtros)
  return (
    <div className="recipiente resumo">
      <Stat rotulo="Rodadas" valor={data?.rodadas} />
      <Stat rotulo="Leituras" valor={data?.leituras} />
      {isError && data === undefined && (
        <p className="corpo-sm resumo-erro" role="alert">
          {error instanceof Error ? error.message : 'Não foi possível carregar o resumo.'}
        </p>
      )}
    </div>
  )
}
