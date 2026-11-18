import { useResumo } from '../api/consultas'
import { Stat } from '../componentes/exibicao'
import type { Filtros } from './filtros'
import './analise.css'

/**
 * Total de rodadas e de leituras dos filtros atuais. Carregando mostra traço; com a
 * API fora mostra traço e a mensagem do erro, para não parecer que ainda está carregando.
 * Ao trocar o filtro, os números anteriores ficam esmaecidos até chegarem os novos.
 */
export function Resumo({ filtros }: { filtros: Filtros }) {
  const { data, isError, error, isPlaceholderData } = useResumo(filtros)
  return (
    <div className={`recipiente resumo${isPlaceholderData ? ' atualizando' : ''}`} aria-busy={isPlaceholderData}>
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
