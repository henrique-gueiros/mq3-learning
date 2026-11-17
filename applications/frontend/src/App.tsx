import { BarraFiltros } from './analise/BarraFiltros'
import { useFiltrosDaUrl } from './analise/filtros'
import { Resumo } from './analise/Resumo'
import { SecaoComparacao } from './analise/SecaoComparacao'
import { SecaoRodada } from './analise/SecaoRodada'
import { SecaoRodadas } from './analise/SecaoRodadas'
import { SecaoSopros } from './analise/SecaoSopros'
import { Aviso } from './aovivo/componentes/Aviso'
import { PainelAoVivo } from './aovivo/componentes/PainelAoVivo'
import { SeloAoVivo } from './aovivo/componentes/SeloAoVivo'
import { useAoVivo } from './aovivo/useAoVivo'
import { Cabecalho } from './layout/Cabecalho'
import { Secao } from './layout/Secao'
import { DesignSystem } from './paginas/DesignSystem'

function TelaPrincipal() {
  const { estado, conexao } = useAoVivo()
  const [filtros, mudarFiltros] = useFiltrosDaUrl()
  const propsSecao = { filtros, aoMudarFiltros: mudarFiltros }
  return (
    <>
      <Cabecalho direita={<SeloAoVivo estado={estado} conexao={conexao} />} />
      <main>
        <Secao
          id="ao-vivo"
          titulo="Ao vivo."
          descricao={
            conexao === 'sem-broker'
              ? 'Sem conexão com o broker MQTT. Confira se o Compose está de pé; a tela reconecta sozinha.'
              : 'Leituras chegando da placa agora: PPM, MQ-135 e umidade.'
          }
        >
          <PainelAoVivo estado={estado} />
        </Secao>
        <div className="analise">
          <BarraFiltros filtros={filtros} aoMudar={mudarFiltros} />
          <Resumo filtros={filtros} />
          <SecaoComparacao {...propsSecao} />
          <SecaoRodadas {...propsSecao} />
          <SecaoRodada {...propsSecao} />
          <SecaoSopros {...propsSecao} />
        </div>
      </main>
      <Aviso aviso={estado.aviso} />
    </>
  )
}

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
  return <TelaPrincipal />
}
