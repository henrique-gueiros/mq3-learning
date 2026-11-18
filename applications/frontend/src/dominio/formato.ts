/** Números no formato brasileiro, para a tela inteira usar o mesmo. */

const TRACO = '—'

export function formatarNumero(valor: number | null | undefined, casas = 0): string {
  if (valor == null || Number.isNaN(valor)) return TRACO
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
}

/** `DD/MM/AAAA HH:MM` no fuso do navegador; texto que não é data vira traço. */
export function formatarDataHora(iso: string | null | undefined): string {
  const d = iso ? new Date(iso) : null
  if (!d || Number.isNaN(d.getTime())) return TRACO
  const dois = (n: number) => String(n).padStart(2, '0')
  return `${dois(d.getDate())}/${dois(d.getMonth() + 1)}/${d.getFullYear()} ${dois(d.getHours())}:${dois(d.getMinutes())}`
}

/** Variação em %, sempre com sinal (o menos é o sinal tipográfico, não o hífen). */
export function formatarVariacao(valor: number | null | undefined): string {
  if (valor == null || Number.isNaN(valor)) return TRACO
  const texto = formatarNumero(Math.abs(valor), 1)
  if (Math.abs(valor) < 0.05) return `${formatarNumero(0, 1)}%`
  return `${valor > 0 ? '+' : '−'}${texto}%`
}
