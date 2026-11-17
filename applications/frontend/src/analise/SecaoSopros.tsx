import { Secao } from '../layout/Secao'
import type { PropsSecao } from './tipos'

/** Frente 2D: subida por sopro e rodadas sem sopro (plano, 4.6). Hoje só a casca. */
export function SecaoSopros(_props: PropsSecao) {
  return <Secao id="sopros" titulo="Sopros marcados." descricao="Quanto cada sopro fez os sensores subirem." />
}
