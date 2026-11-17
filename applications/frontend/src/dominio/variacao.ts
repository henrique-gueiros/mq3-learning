/** Quanto (%) um valor está acima ou abaixo da base. */
export function variacao(valor: number | null | undefined, base: number | null | undefined): number | null {
  if (valor == null || base == null || base === 0) return null
  return (valor / base - 1) * 100
}
