import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { rotuloTempo } from '../../graficos/aoVivo'
import type { EstadoSopro } from '../detector'
import './aovivo.css'

const TEXTOS: Record<EstadoSopro, { titulo: string; detalhe: string }> = {
  calibrando: { titulo: 'Calibrando.', detalhe: 'Medindo o ar do ambiente para a linha de base.' },
  ambiente: { titulo: 'Ambiente.', detalhe: 'Nenhum sopro no sensor.' },
  sopro: { titulo: 'Sopro detectado.', detalhe: 'Umidade e gás subiram juntos.' },
  recuperando: { titulo: 'Recuperando.', detalhe: 'Os sensores estão voltando à linha de base.' },
}

// o gradiente da marca "respira" no sopro: é o único destaque da tela
const BRILHO: Record<EstadoSopro, number> = { calibrando: 0, ambiente: 0, sopro: 1, recuperando: 0.35 }

/** O estado do detector em letra grande, com o tempo no estado. */
export function CartaoEstado({
  estado,
  segundosNoEstado,
  temDados,
}: {
  estado: EstadoSopro
  segundosNoEstado: number
  temDados: boolean
}) {
  const reduzir = useReducedMotion()
  const texto = temDados ? TEXTOS[estado] : { titulo: 'Aguardando a placa.', detalhe: 'Nenhuma leitura chegou ainda.' }
  const chave = temDados ? estado : 'sem-dados'

  return (
    <div className="estado" data-estado={chave}>
      <motion.div
        className="estado-brilho"
        aria-hidden
        initial={false}
        animate={{ opacity: temDados ? BRILHO[estado] : 0, scale: estado === 'sopro' && !reduzir ? [1, 1.08, 1] : 1 }}
        transition={{
          opacity: { duration: 0.6, ease: [0.23, 1, 0.32, 1] },
          scale: { duration: 2.4, repeat: estado === 'sopro' ? Infinity : 0, ease: 'easeInOut' },
        }}
      />
      <div className="estado-conteudo" aria-live="polite">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.div
            key={chave}
            className="estado-texto"
            initial={reduzir ? { opacity: 0 } : { opacity: 0, y: 12, filter: 'blur(4px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            exit={reduzir ? { opacity: 0 } : { opacity: 0, y: -12, filter: 'blur(4px)' }}
            transition={{ duration: 0.32, ease: [0.23, 1, 0.32, 1] }}
          >
            <h3 className="display-xl">{texto.titulo}</h3>
            <p className="corpo-lg">{texto.detalhe}</p>
          </motion.div>
        </AnimatePresence>
        <div className="estado-rodape">
          {temDados && <span className="mono legenda">há {rotuloTempo(segundosNoEstado)}</span>}
          <span className="legenda">Estimativa da tela a partir da umidade e do gás; não é o modelo de ML.</span>
        </div>
      </div>
    </div>
  )
}
