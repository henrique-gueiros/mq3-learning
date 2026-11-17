import { useResumo } from '../api/consultas'
import { Stat } from '../componentes/exibicao'
import type { Filtros } from './filtros'
import './analise.css'

/** Total de rodadas e de leituras dos filtros atuais. Com a API fora, mostra traço. */
export function Resumo({ filtros }: { filtros: Filtros }) {
  const { data } = useResumo(filtros)
  return (
    <div className="recipiente resumo">
      <Stat rotulo="Rodadas" valor={data?.rodadas} />
      <Stat rotulo="Leituras" valor={data?.leituras} />
    </div>
  )
}
