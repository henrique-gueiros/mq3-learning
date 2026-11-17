import { describe, expect, it } from 'vitest'
import { corDoCaso, nomeDoCaso, ordenarCasos } from './casos'

describe('casos', () => {
  it('mostra o ambiente e a bebida com nomes em português', () => {
    expect(nomeDoCaso('clean')).toBe('ambiente')
    expect(nomeDoCaso('drink')).toBe('bebida')
    expect(nomeDoCaso('alcohol70_spray')).toBe('álcool 70 (spray)')
  })

  it('mantém o nome de um caso desconhecido', () => {
    expect(nomeDoCaso('alcohol_cup')).toBe('alcohol_cup')
  })

  it('ordena na ordem do protocolo, desconhecidos no fim e sem repetir', () => {
    expect(ordenarCasos(['zeta', 'perfume', 'clean', 'drink', 'clean', 'alfa'])).toEqual([
      'clean', 'drink', 'perfume', 'alfa', 'zeta',
    ])
  })

  it('cada caso tem uma cor por tema, e o desconhecido usa a cor de "outro"', () => {
    expect(corDoCaso('clean', 'escuro')).not.toBe(corDoCaso('clean', 'claro'))
    expect(corDoCaso('drink', 'escuro')).not.toBe(corDoCaso('clean', 'escuro'))
    expect(corDoCaso('alcohol_cup', 'claro')).toBe(corDoCaso('outro_qualquer', 'claro'))
  })
})
