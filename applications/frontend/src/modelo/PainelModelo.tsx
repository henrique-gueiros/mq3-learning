import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useId, useRef, useState } from 'react'
import { corDoCaso } from '../dominio/casos'
import { formatarNumero } from '../dominio/formato'
import { useTema } from '../tema/TemaProvider'
import { classificarSopro } from './cliente'
import './modelo.css'
import { resumoDoSopro, SOPROS } from './sopros'
import { formatarProbabilidade, textoDaClassificacao } from './textos'
import type { IdSopro, ResultadoModelo, SoproDemo } from './tipos'

type Fase =
  | { tipo: 'ocioso' }
  | { tipo: 'enviando'; id: IdSopro }
  | { tipo: 'pronto'; id: IdSopro; resultado: ResultadoModelo }
  | { tipo: 'falha'; id: IdSopro; mensagem: string }

/** Três sopros de exemplo e a classe que o modelo devolveu para o último envio. */
export function PainelModelo() {
  const { tema } = useTema()
  const reduzir = useReducedMotion()
  const [fase, setFase] = useState<Fase>({ tipo: 'ocioso' })
  const tituloRef = useRef<HTMLHeadingElement>(null)
  const tituloId = useId()

  useEffect(() => {
    if (fase.tipo === 'ocioso' || fase.tipo === 'enviando') return
    tituloRef.current?.focus()
  }, [fase])

  async function enviar(sopro: SoproDemo) {
    setFase({ tipo: 'enviando', id: sopro.id })
    try {
      const resultado = await classificarSopro(sopro)
      setFase({ tipo: 'pronto', id: sopro.id, resultado })
    } catch (erro) {
      const mensagem = erro instanceof Error ? erro.message : 'O modelo não respondeu.'
      setFase({ tipo: 'falha', id: sopro.id, mensagem })
    }
  }

  const enviando = fase.tipo === 'enviando'
  const soproAtivo = fase.tipo === 'ocioso' ? undefined : SOPROS.find((s) => s.id === fase.id)
  const apresentacao = montarApresentacao(fase, soproAtivo)

  return (
    <div className="modelo">
      <div
        className="modelo-palco"
        data-classe={apresentacao.classe}
        role="status"
        aria-live="polite"
        aria-labelledby={tituloId}
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={apresentacao.chave}
            initial={reduzir ? { opacity: 0 } : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduzir ? { opacity: 0 } : { opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: [0.23, 1, 0.32, 1] }}
          >
            {apresentacao.alerta && <p className="modelo-alerta">Alerta de detecção.</p>}
            <h3 id={tituloId} className="display-xl" tabIndex={-1} ref={tituloRef}>
              {apresentacao.titulo}
            </h3>
            <p className="corpo-lg modelo-detalhe">{apresentacao.detalhe}</p>
          </motion.div>
        </AnimatePresence>
        <div className="modelo-palco-rodape">
          {apresentacao.resultado?.status === 'classificado' && (
            <dl className="modelo-probs">
              <div>
                <dt className="legenda">sob efeito</dt>
                <dd className="mono">{formatarProbabilidade(apresentacao.resultado.prob_sob_efeito)}</dd>
              </div>
              <div>
                <dt className="legenda">sem efeito</dt>
                <dd className="mono">{formatarProbabilidade(apresentacao.resultado.prob_sem_efeito)}</dd>
              </div>
            </dl>
          )}
          <div className="modelo-palco-notas">
            <p className="legenda">
              {soproAtivo
                ? `Enviado: ${soproAtivo.rotulo} · ${soproAtivo.origem}`
                : 'Nenhum sopro enviado ainda.'}
            </p>
            <p className="legenda">Classificação do modelo treinado. Não é laudo e não mede mg/L.</p>
          </div>
        </div>
      </div>

      <ul className="modelo-casos">
        {SOPROS.map((sopro) => {
          const resumo = resumoDoSopro(sopro)
          const ativo = soproAtivo?.id === sopro.id
          return (
            <li key={sopro.id}>
              <article className="modelo-caso" data-ativo={ativo || undefined}>
                <header className="modelo-caso-topo">
                  <span className="modelo-ponto" style={{ background: corDoCaso(sopro.caso, tema) }} aria-hidden />
                  <h3 className="display-sm">{sopro.rotulo}</h3>
                </header>
                <p className="corpo-sm">{sopro.detalhe}</p>
                <dl className="modelo-numeros">
                  <div>
                    <dt className="legenda">PPM</dt>
                    <dd className="mono">{formatarNumero(resumo.ppm, 2)}</dd>
                  </div>
                  <div>
                    <dt className="legenda">MQ-135</dt>
                    <dd className="mono">{formatarNumero(resumo.mq135)}</dd>
                  </div>
                  <div>
                    <dt className="legenda">Umidade</dt>
                    <dd className="mono">{formatarNumero(resumo.umidade, 1)}%</dd>
                  </div>
                </dl>
                <p className="legenda">Pico do sopro e dos 30 s seguintes. {sopro.leituras.length} leituras no recorte.</p>
                <button
                  type="button"
                  className="modelo-enviar"
                  disabled={enviando}
                  aria-label={`Classificar o sopro de ${sopro.rotulo}`}
                  onClick={() => void enviar(sopro)}
                >
                  {fase.tipo === 'enviando' && fase.id === sopro.id ? 'Classificando…' : 'Classificar'}
                </button>
              </article>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function montarApresentacao(fase: Fase, sopro: SoproDemo | undefined) {
  if (fase.tipo === 'enviando') {
    return {
      chave: `enviando-${fase.id}`,
      titulo: 'Classificando.',
      detalhe: `O recorte de ${sopro?.rotulo.toLocaleLowerCase('pt-BR')} está no modelo.`,
      classe: undefined,
      alerta: false,
      resultado: undefined,
    }
  }
  if (fase.tipo === 'falha') {
    return {
      chave: `falha-${fase.id}-${fase.mensagem}`,
      titulo: 'O modelo não respondeu.',
      detalhe: fase.mensagem,
      classe: 'atencao',
      alerta: false,
      resultado: undefined,
    }
  }
  if (fase.tipo === 'pronto') {
    const texto = textoDaClassificacao(fase.resultado)
    return {
      chave: `pronto-${fase.id}-${texto.titulo}`,
      titulo: texto.titulo,
      detalhe: texto.detalhe,
      classe: texto.classe,
      alerta: texto.classe === 'sob_efeito',
      resultado: fase.resultado,
    }
  }
  return {
    chave: 'ocioso',
    titulo: 'Aguardando um sopro.',
    detalhe: 'Escolha perfume, bebida ou sem bebida. A classe do modelo aparece aqui.',
    classe: undefined,
    alerta: false,
    resultado: undefined,
  }
}
