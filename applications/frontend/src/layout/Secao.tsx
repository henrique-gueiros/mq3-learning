import type { ReactNode } from 'react'
import './layout.css'

/** Uma seção da tela: título no tom do design system (frase curta com ponto) e conteúdo. */
export function Secao({
  id,
  titulo,
  descricao,
  acoes,
  children,
}: {
  id: string
  titulo: string
  descricao?: string
  acoes?: ReactNode
  children?: ReactNode
}) {
  return (
    <section id={id} className="secao" aria-labelledby={`${id}-titulo`}>
      <div className="recipiente">
        <div className="secao-topo">
          <div className="secao-texto">
            <h2 id={`${id}-titulo`} className="display-lg">
              {titulo}
            </h2>
            {descricao && <p className="corpo-lg">{descricao}</p>}
          </div>
          {acoes && <div className="secao-acoes">{acoes}</div>}
        </div>
        {children ?? <div className="secao-vazia corpo-sm">Esta seção entra nas próximas etapas.</div>}
      </div>
    </section>
  )
}
