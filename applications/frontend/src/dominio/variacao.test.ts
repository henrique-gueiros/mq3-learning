import { describe, expect, it } from 'vitest'
import { variacao } from './variacao'

describe('variacao', () => {
  it('é a diferença percentual em relação à base', () => {
    expect(variacao(560, 250)).toBeCloseTo(124)
    expect(variacao(45, 50)).toBeCloseTo(-10)
  })
  it('sem valor, sem base ou base zero não tem variação', () => {
    expect(variacao(null, 250)).toBeNull()
    expect(variacao(10, null)).toBeNull()
    expect(variacao(10, 0)).toBeNull()
  })
})
