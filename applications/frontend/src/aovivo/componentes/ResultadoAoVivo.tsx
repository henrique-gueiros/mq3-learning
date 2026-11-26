import { rotuloTempo } from '../../graficos/aoVivo'
import { formatarProbabilidade, textoDaClassificacao } from '../../modelo/textos'
import type { Resultado } from '../mensagens'
import './aovivo.css'

/**
 * Classe do modelo para o último sopro da rodada, publicada pelo servidor do
 * modelo em mq3/<placa>/resultado. É o modelo de ML, diferente do cartão de
 * estado, que é a estimativa da tela.
 */
export function ResultadoAoVivo({ resultados }: { resultados: Resultado[] }) {
  const ultimo = resultados.at(-1)
  if (!ultimo) {
    return (
      <div className="aovivo-modelo" aria-live="polite">
        <p className="legenda">Modelo de ML</p>
        <p className="corpo-sm">
          A classe do modelo aparece cerca de 35 s depois do fim de cada sopro marcado, ou, com a placa sozinha,
          a cada 3 s, numa janela deslizante (o primeiro resultado sai uns 47 s depois da primeira leitura).
        </p>
      </div>
    )
  }

  const texto = textoDaClassificacao(ultimo)
  return (
    <div className="aovivo-modelo" data-classe={texto.classe} role="status" aria-live="polite">
      <p className="legenda">
        Modelo de ML ·{' '}
        {ultimo.origem === 'continuo'
          ? `janela de ${rotuloTempo(ultimo.t_ms / 1000)}`
          : `sopro que terminou em ${rotuloTempo(ultimo.t_ms / 1000)}`}
      </p>
      {texto.classe === 'sob_efeito' && (ultimo.origem !== 'continuo' || (ultimo.sob_efeito_seguidos ?? 0) >= 3) && (
        <p className="aovivo-modelo-alerta">Alerta de detecção.</p>
      )}
      <h3 className="display-md">{texto.titulo}</h3>
      <p className="corpo-sm">{texto.detalhe}</p>
      {ultimo.status === 'classificado' && (
        <dl className="aovivo-modelo-probs">
          <div>
            <dt className="legenda">sob efeito</dt>
            <dd className="mono">{formatarProbabilidade(ultimo.prob_sob_efeito)}</dd>
          </div>
          <div>
            <dt className="legenda">sem efeito</dt>
            <dd className="mono">{formatarProbabilidade(ultimo.prob_sem_efeito)}</dd>
          </div>
        </dl>
      )}
    </div>
  )
}
