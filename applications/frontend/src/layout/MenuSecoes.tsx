import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import '../componentes/componentes.css'
import { SECOES } from './secoes'

/**
 * Menu das seções para telas pequenas (o CSS esconde o botão acima de 760 px).
 * Fecha ao escolher um link, com Esc (devolvendo o foco ao botão) e ao clicar fora.
 * Tab circula só entre os links enquanto o painel está aberto.
 */
export function MenuSecoes() {
  const [aberto, setAberto] = useState(false)
  const raiz = useRef<HTMLDivElement>(null)
  const botao = useRef<HTMLButtonElement>(null)
  const painelId = useId()

  useEffect(() => {
    if (!aberto) return
    raiz.current?.querySelector<HTMLAnchorElement>('.menu-secoes-painel a')?.focus()
    const fecharFora = (e: PointerEvent) => {
      if (!raiz.current?.contains(e.target as Node)) setAberto(false)
    }
    const fecharEsc = (e: globalThis.KeyboardEvent) => {
      if (e.key !== 'Escape') return
      setAberto(false)
      botao.current?.focus()
    }
    const larga = window.matchMedia?.('(min-width: 761px)')
    const fecharLarga = (e: MediaQueryListEvent) => e.matches && setAberto(false)
    larga?.addEventListener?.('change', fecharLarga)
    document.addEventListener('pointerdown', fecharFora)
    document.addEventListener('keydown', fecharEsc)
    return () => {
      document.removeEventListener('pointerdown', fecharFora)
      document.removeEventListener('keydown', fecharEsc)
      larga?.removeEventListener?.('change', fecharLarga)
    }
  }, [aberto])

  function prenderTab(e: KeyboardEvent<HTMLElement>) {
    if (e.key !== 'Tab') return
    const links = e.currentTarget.querySelectorAll<HTMLAnchorElement>('a')
    const primeiro = links[0]
    const ultimo = links[links.length - 1]
    if (e.shiftKey && document.activeElement === primeiro) {
      e.preventDefault()
      ultimo.focus()
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault()
      primeiro.focus()
    }
  }

  return (
    <div
      className="menu-secoes"
      ref={raiz}
      onBlur={(e) => {
        const para = e.relatedTarget as Node | null
        if (aberto && para && !e.currentTarget.contains(para)) setAberto(false)
      }}
    >
      <button
        ref={botao}
        type="button"
        className="botao-icone"
        aria-label={aberto ? 'Fechar menu das seções' : 'Abrir menu das seções'}
        aria-expanded={aberto}
        aria-controls={aberto ? painelId : undefined}
        onClick={() => setAberto((a) => !a)}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
          {aberto ? (
            <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          ) : (
            <path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          )}
        </svg>
      </button>
      {aberto && (
        <nav id={painelId} className="menu-secoes-painel" aria-label="Seções (menu)" onKeyDown={prenderTab}>
          {SECOES.map((s) => (
            <a key={s.href} href={s.href} onClick={() => {
                setAberto(false)
                botao.current?.focus()
              }}
            >
              {s.rotulo}
            </a>
          ))}
        </nav>
      )}
    </div>
  )
}
