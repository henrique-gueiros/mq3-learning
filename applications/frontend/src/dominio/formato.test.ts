import { describe, expect, it } from 'vitest'
import { comSinal, formatarDataHora, formatarNumero, formatarVariacao, interpolar, TWEEN_MS } from './formato'

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

  it('sinal tipográfico, zero sem sinal', () => {
    expect(comSinal(81, '81%')).toBe('+81%')
    expect(comSinal(-3, '3%')).toBe('−3%')
    expect(comSinal(0, '0%')).toBe('0%')
  })

  it('interpolação começa no valor antigo, termina no novo e dura no máximo 200 ms', () => {
    expect(interpolar(10, 20, 0)).toBe(10)
    expect(interpolar(10, 20, 1)).toBe(20)
    expect(interpolar(10, 20, 0.5)).toBeGreaterThan(10)
    expect(interpolar(10, 20, 0.5)).toBeLessThan(20)
    expect(TWEEN_MS).toBeLessThanOrEqual(200)
  })

  it('data e hora no fuso do navegador, DD/MM/AAAA HH:MM', () => {
    expect(formatarDataHora(new Date(2026, 10, 5, 9, 7).toISOString())).toBe('05/11/2026 09:07')
    expect(formatarDataHora(null)).toBe('—')
    expect(formatarDataHora('não é data')).toBe('—')
  })
})
