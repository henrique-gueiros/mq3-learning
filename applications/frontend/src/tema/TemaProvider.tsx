import { createContext, useCallback, useContext, useLayoutEffect, useState, type ReactNode } from 'react'
import { flushSync } from 'react-dom'
import { semMovimento } from '../graficos/temaEcharts'
import { lerTema, salvarTema, type Tema } from './tema'

interface ValorTema {
  tema: Tema
  alternar: () => void
}

const ContextoTema = createContext<ValorTema | null>(null)

function armazenamento() {
  try {
    return window.localStorage
  } catch {
    return { getItem: () => null, setItem: () => {} }
  }
}

/** Guarda o tema, aplica no <html> (data-theme) e anima a troca quando o navegador sabe. */
export function TemaProvider({ children }: { children: ReactNode }) {
  const [tema, setTema] = useState<Tema>(() => lerTema(armazenamento()))

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = tema
  }, [tema])

  const alternar = useCallback(() => {
    const proximo: Tema = tema === 'escuro' ? 'claro' : 'escuro'
    const trocar = () => {
      flushSync(() => setTema(proximo))
      salvarTema(armazenamento(), proximo)
    }
    if (document.startViewTransition && !semMovimento()) {
      document.startViewTransition(trocar)
    } else {
      trocar()
    }
  }, [tema])

  return <ContextoTema.Provider value={{ tema, alternar }}>{children}</ContextoTema.Provider>
}

export function useTema(): ValorTema {
  const valor = useContext(ContextoTema)
  if (!valor) throw new Error('useTema precisa estar dentro de <TemaProvider>')
  return valor
}
