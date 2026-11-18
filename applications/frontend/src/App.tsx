import { lazy, Suspense } from 'react'
import { useFiltrosDaUrl } from './analise/filtros'
import { Aviso } from './aovivo/componentes/Aviso'
import { PainelAoVivo } from './aovivo/componentes/PainelAoVivo'
import { SeloAoVivo } from './aovivo/componentes/SeloAoVivo'
import { useAoVivo } from './aovivo/useAoVivo'
import { Cabecalho } from './layout/Cabecalho'
import { LimiteDeErro } from './layout/LimiteDeErro'
import { Secao } from './layout/Secao'

// Carregados sob demanda: o "Ao vivo" aparece sem esperar os gráficos de análise nem o design system.
const Analise = lazy(() => import('./analise/Analise'))
const DesignSystem = lazy(() => import('./paginas/DesignSystem').then((m) => ({ default: m.DesignSystem })))

function TelaPrincipal() {
  const { estado, conexao } = useAoVivo()
  const [filtros, mudarFiltros] = useFiltrosDaUrl()
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
        <LimiteDeErro mensagem="A análise não carregou. O ao vivo continua funcionando.">
          <Suspense fallback={<div className="analise-carregando" role="status" aria-label="Carregando a análise" />}>
            <Analise filtros={filtros} aoMudarFiltros={mudarFiltros} />
          </Suspense>
        </LimiteDeErro>
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
        <Suspense fallback={null}>
          <DesignSystem />
        </Suspense>
      </>
    )
  }
  return <TelaPrincipal />
}
