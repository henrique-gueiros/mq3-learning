import { describe, expect, it } from 'vitest'
import type { RodadaOpcao } from '../api/consultas'
import { escolherRodada, rodadasVisiveis, rotuloRodada } from './rodadas'

const r = (id: string, caso: string, origem = 'ponte'): RodadaOpcao => ({
  id,
  caso,
  participante: 'p01',
  origem,
  inicio: new Date(2026, 10, 6, 14, 0).toISOString(),
})

describe('rodadasVisiveis', () => {
  const todas = [r('a', 'drink', 'simulador'), r('b', 'clean'), r('c', 'perfume', 'importador')]

  it('esconde as rodadas do simulador com o interruptor desligado', () => {
    expect(rodadasVisiveis(todas, false).map((x) => x.id)).toEqual(['b', 'c'])
  })

  it('com o interruptor ligado mostra todas, na ordem da API', () => {
    expect(rodadasVisiveis(todas, true).map((x) => x.id)).toEqual(['a', 'b', 'c'])
  })
})

describe('rotuloRodada', () => {
  it('caso em português, participante e início no fuso do navegador', () => {
    expect(rotuloRodada(r('a', 'drink'))).toBe('bebida · p01 · 06/11/2026 14:00')
    expect(rotuloRodada(r('b', 'clean'))).toBe('ambiente · p01 · 06/11/2026 14:00')
  })

  it('marca as rodadas do simulador', () => {
    expect(rotuloRodada(r('a', 'drink', 'simulador'))).toBe('bebida · p01 · 06/11/2026 14:00 · simulador')
  })
})

describe('escolherRodada', () => {
  const visiveis = [r('b', 'clean'), r('c', 'perfume')]

  it('sem escolha usa a mais recente (a primeira)', () => {
    expect(escolherRodada(null, visiveis)).toBe('b')
  })

  it('mantém a escolha quando ela está na lista', () => {
    expect(escolherRodada('c', visiveis)).toBe('c')
  })

  it('escolha que sumiu da lista (simulador desligado) volta para a mais recente', () => {
    expect(escolherRodada('a', visiveis)).toBe('b')
  })

  it('sem rodadas não há escolha', () => {
    expect(escolherRodada('a', [])).toBeNull()
  })
})
