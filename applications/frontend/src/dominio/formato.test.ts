import { describe, expect, it } from 'vitest'
import { formatarNumero, formatarVariacao } from './formato'

describe('formato', () => {
  it('usa vírgula decimal e separador de milhar', () => {
    expect(formatarNumero(11941)).toBe('11.941')
    expect(formatarNumero(0.4321, 2)).toBe('0,43')
  })

  it('mostra traço quando não há valor', () => {
    expect(formatarNumero(null)).toBe('—')
    expect(formatarVariacao(undefined)).toBe('—')
  })

  it('variação sempre com sinal e uma casa', () => {
    expect(formatarVariacao(12.44)).toBe('+12,4%')
    expect(formatarVariacao(-3)).toBe('−3,0%')
    expect(formatarVariacao(0)).toBe('0,0%')
  })
})
