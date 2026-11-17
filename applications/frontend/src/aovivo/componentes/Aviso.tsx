import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import type { Aviso as TipoAviso } from '../estado'
import './aovivo.css'

const DURACAO_MS = 4000

/** Aviso curto no canto (sopro detectado, sopro marcado, rodada encerrada). */
export function Aviso({ aviso }: { aviso: TipoAviso | null }) {
  const [visivel, setVisivel] = useState<TipoAviso | null>(null)

  useEffect(() => {
    if (!aviso) return
    setVisivel(aviso)
    const t = window.setTimeout(() => setVisivel(null), DURACAO_MS)
    return () => window.clearTimeout(t)
  }, [aviso])

  return (
    <div className="aviso-area" role="status" aria-live="polite">
      <AnimatePresence>
        {visivel && (
          <motion.div
            key={visivel.id}
            className="aviso"
            data-tipo={visivel.tipo}
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.24, ease: [0.23, 1, 0.32, 1] }}
          >
            <span className="aviso-ponto" aria-hidden />
            {visivel.texto}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
