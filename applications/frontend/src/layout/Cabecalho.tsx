import type { ReactNode } from 'react'
import { BotaoTema } from '../tema/BotaoTema'
import { MenuSecoes } from './MenuSecoes'
import { SECOES } from './secoes'
import './layout.css'

/** Barra fixa no topo: marca, abas Painel/Modelo, atalhos das seções e troca de tema. */
export function Cabecalho({ direita, pagina = 'painel' }: { direita?: ReactNode; pagina?: 'painel' | 'modelo' }) {
  return (
    <header className="cabecalho">
      <div className="recipiente cabecalho-linha">
        <a className="marca" href="/" aria-label="Sopro Seguro, início">
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
          <span>Sopro Seguro</span>
        </a>
        <nav className="abas" aria-label="Telas">
          <a href="/" aria-current={pagina === 'painel' ? 'page' : undefined}>
            Painel
          </a>
          <a href="/modelo" aria-current={pagina === 'modelo' ? 'page' : undefined}>
            Modelo
          </a>
        </nav>
        {pagina === 'painel' && (
          <nav className="cabecalho-nav" aria-label="Seções">
            {SECOES.map((l) => (
              <a key={l.href} href={l.href}>
                {l.rotulo}
              </a>
            ))}
          </nav>
        )}
        <div className="cabecalho-acoes">
          {direita}
          <BotaoTema />
          {pagina === 'painel' && <MenuSecoes />}
        </div>
      </div>
    </header>
  )
}
