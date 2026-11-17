import { useTema } from './TemaProvider'
import '../componentes/componentes.css'

/** Botão redondo de troca de tema: o ícone mostra o tema de destino. */
export function BotaoTema() {
  const { tema, alternar } = useTema()
  const destino = tema === 'escuro' ? 'claro' : 'escuro'
  return (
    <button type="button" className="botao-icone" onClick={alternar} aria-label={`Usar tema ${destino}`} title={`Usar tema ${destino}`}>
      {destino === 'claro' ? (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
          <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3.05 3.05l1.06 1.06M11.89 11.89l1.06 1.06M3.05 12.95l1.06-1.06M11.89 4.11l1.06-1.06"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  )
}
