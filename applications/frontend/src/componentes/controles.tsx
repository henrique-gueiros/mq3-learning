import './componentes.css'

interface Opcao<T extends string> {
  valor: T
  rotulo: string
}

/** Escolha única entre poucas opções, como "arquivo / sopro". */
export function Segmentado<T extends string>({
  rotulo,
  opcoes,
  valor,
  aoMudar,
}: {
  rotulo: string
  opcoes: Opcao<T>[]
  valor: T
  aoMudar: (valor: T) => void
}) {
  return (
    <div className="segmentado" role="radiogroup" aria-label={rotulo}>
      {opcoes.map((o) => (
        <button
          key={o.valor}
          type="button"
          role="radio"
          aria-checked={o.valor === valor}
          className="segmentado-opcao"
          onClick={() => aoMudar(o.valor)}
        >
          {o.rotulo}
        </button>
      ))}
    </div>
  )
}

/** Filtro que liga e desliga; a bolinha mostra a cor do caso. */
export function Chip({
  rotulo,
  ativo,
  aoAlternar,
  cor,
}: {
  rotulo: string
  ativo: boolean
  aoAlternar: () => void
  cor?: string
}) {
  return (
    <button type="button" className="chip" aria-pressed={ativo} onClick={aoAlternar}>
      {cor && <span className="chip-cor" style={{ background: cor }} aria-hidden />}
      {rotulo}
    </button>
  )
}

/** Chave liga/desliga com o rótulo ao lado. */
export function Interruptor({
  rotulo,
  ligado,
  aoMudar,
}: {
  rotulo: string
  ligado: boolean
  aoMudar: (ligado: boolean) => void
}) {
  return (
    <button type="button" role="switch" aria-checked={ligado} className="interruptor" onClick={() => aoMudar(!ligado)}>
      <span className="interruptor-trilho" aria-hidden>
        <span className="interruptor-botao" />
      </span>
      {rotulo}
    </button>
  )
}
