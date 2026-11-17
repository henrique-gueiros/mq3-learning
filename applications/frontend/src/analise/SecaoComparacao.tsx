import { Secao } from '../layout/Secao'
import type { PropsSecao } from './tipos'

/** Frente 2A: boxplot, heatmap e dispersão (plano, 4.3). Hoje só a casca. */
export function SecaoComparacao(_props: PropsSecao) {
  return (
    <Secao
      id="comparacao"
      titulo="Comparação entre os casos."
      descricao="Como cada sensor se comporta em ambiente, bebida, perfume e nos outros casos."
    />
  )
}
