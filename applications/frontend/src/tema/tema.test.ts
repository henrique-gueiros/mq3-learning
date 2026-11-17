import { describe, expect, it } from 'vitest'
import { lerTema, salvarTema } from './tema'

const memoria = () => {
  const dados = new Map<string, string>()
  return {
    getItem: (k: string) => dados.get(k) ?? null,
    setItem: (k: string, v: string) => void dados.set(k, v),
  }
}

describe('tema', () => {
  it('começa escuro quando nada foi salvo', () => {
    expect(lerTema(memoria())).toBe('escuro')
  })

  it('lembra a escolha salva', () => {
    const m = memoria()
    salvarTema(m, 'claro')
    expect(lerTema(m)).toBe('claro')
  })

  it('ignora valor inválido e armazenamento que falha', () => {
    const m = memoria()
    m.setItem('mq3-tema', 'roxo')
    expect(lerTema(m)).toBe('escuro')
    const quebrado = { getItem: () => { throw new Error('bloqueado') }, setItem: () => { throw new Error('bloqueado') } }
    expect(lerTema(quebrado)).toBe('escuro')
    expect(() => salvarTema(quebrado, 'claro')).not.toThrow()
  })
})
