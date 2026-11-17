import { Secao } from '../layout/Secao'
import type { PropsSecao } from './tipos'

/** Frente 2B: rodadas sobrepostas (plano, 4.4). Hoje só a casca. */
export function SecaoRodadas(_props: PropsSecao) {
  return <Secao id="rodadas" titulo="Todas as rodadas juntas." descricao="Uma linha por rodada, colorida pelo caso." />
}
