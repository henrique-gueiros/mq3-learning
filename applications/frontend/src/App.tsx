import { Cabecalho } from './layout/Cabecalho'
import { Secao } from './layout/Secao'
import { DesignSystem } from './paginas/DesignSystem'

/** Tela única do sistema; /design-system mostra os tokens e componentes. */
export default function App() {
  if (window.location.pathname.replace(/\/$/, '') === '/design-system') {
    return (
      <>
        <Cabecalho />
        <DesignSystem />
      </>
    )
  }
  return (
    <>
      <Cabecalho />
      <main>
        <Secao id="ao-vivo" titulo="Ao vivo." descricao="Leituras chegando da placa agora: PPM, MQ-135 e umidade." />
        <Secao id="comparacao" titulo="Comparação entre os casos." descricao="Como cada sensor se comporta em ambiente, bebida, perfume e nos outros casos." />
        <Secao id="rodadas" titulo="Todas as rodadas juntas." descricao="Uma linha por rodada, colorida pelo caso." />
        <Secao id="rodada" titulo="Rodada selecionada." descricao="Os três sensores de uma rodada, com as janelas de sopro." />
        <Secao id="sopros" titulo="Sopros marcados." descricao="Quanto cada sopro fez os sensores subirem." />
      </main>
    </>
  )
}
