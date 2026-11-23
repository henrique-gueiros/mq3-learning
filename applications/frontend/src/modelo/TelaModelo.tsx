import { Cabecalho } from '../layout/Cabecalho'
import { Secao } from '../layout/Secao'
import { PainelModelo } from './PainelModelo'

/** Aba ao lado do painel: classifica sopros de exemplo sem a placa. */
export function TelaModelo() {
  return (
    <>
      <a className="pular" href="#modelo">Pular para o conteúdo</a>
      <Cabecalho pagina="modelo" />
      <main>
        <Secao
          id="modelo"
          titulo="Modelo."
          descricao="Três sopros da coleta da equipe, para classificar sem a placa. O botão envia o recorte ao modelo; a classe aparece em seguida."
        >
          <PainelModelo />
        </Secao>
      </main>
    </>
  )
}
