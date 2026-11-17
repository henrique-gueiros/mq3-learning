import type { ReactNode } from 'react'
import { BotaoTema } from '../tema/BotaoTema'
import './layout.css'

const LINKS = [
  { href: '/#ao-vivo', rotulo: 'Ao vivo' },
  { href: '/#comparacao', rotulo: 'Comparação' },
  { href: '/#rodadas', rotulo: 'Rodadas' },
  { href: '/#sopros', rotulo: 'Sopros' },
]

/** Barra fixa no topo: marca, atalhos para as seções e troca de tema. */
export function Cabecalho({ direita }: { direita?: ReactNode }) {
  return (
    <header className="cabecalho">
      <div className="recipiente cabecalho-linha">
        <a className="marca" href="/" aria-label="MQ-3, início">
          <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
            <path
              d="M4 19c3 0 3-7 6-7s3 10 6 10 3-14 6-14 3 11 6 11"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span>MQ-3</span>
        </a>
        <nav className="cabecalho-nav" aria-label="Seções">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href}>
              {l.rotulo}
            </a>
          ))}
        </nav>
        <div className="cabecalho-acoes">
          {direita}
          <BotaoTema />
        </div>
      </div>
    </header>
  )
}
