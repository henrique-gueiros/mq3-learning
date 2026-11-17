import { describe, expect, it } from 'vitest'
import { escreverFiltros, FILTROS_PADRAO, lerFiltros } from './filtros'

describe('lerFiltros', () => {
  it('sem nada na URL devolve o padrão (nenhum caso = todos)', () => {
    expect(lerFiltros('')).toEqual(FILTROS_PADRAO)
    expect(FILTROS_PADRAO.casos).toEqual([])
  })

  it('lê caso repetido, janela, simulador e rodada', () => {
    expect(lerFiltros('?caso=drink&caso=perfume&janela=sopro&simulador=1&rodada=abc')).toEqual({
      casos: ['drink', 'perfume'],
      janela: 'sopro',
      simulador: true,
      rodada: 'abc',
    })
  })

  it('janela inválida vira arquivo', () => {
    expect(lerFiltros('?janela=qualquer').janela).toBe('arquivo')
  })

  it('ignora casos vazios e repetidos', () => {
    expect(lerFiltros('?caso=&caso=drink&caso=drink').casos).toEqual(['drink'])
  })
})

describe('escreverFiltros', () => {
  it('o padrão não deixa nada na URL', () => {
    expect(escreverFiltros(FILTROS_PADRAO)).toBe('')
  })

  it('ida e volta preserva os filtros', () => {
    const f = { casos: ['drink', 'clean'], janela: 'sopro' as const, simulador: true, rodada: 'r1' }
    expect(lerFiltros(escreverFiltros(f))).toEqual(f)
  })

  it('só escreve o que difere do padrão', () => {
    expect(escreverFiltros({ ...FILTROS_PADRAO, janela: 'sopro' })).toBe('?janela=sopro')
  })
})
