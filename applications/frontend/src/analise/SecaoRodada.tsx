import { Secao } from '../layout/Secao'
import type { PropsSecao } from './tipos'

/** Frente 2C: rodada selecionada, guardada em `filtros.rodada` (plano, 4.5). Hoje só a casca. */
export function SecaoRodada(_props: PropsSecao) {
  return <Secao id="rodada" titulo="Rodada selecionada." descricao="Os três sensores de uma rodada, com as janelas de sopro." />
}
