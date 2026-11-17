import { afterEach, describe, expect, it, vi } from 'vitest'
import { buscar, montarQuery } from './cliente'

afterEach(() => vi.unstubAllGlobals())

describe('montarQuery', () => {
  it('repete caso e só manda simulador quando ligado', () => {
    expect(montarQuery({ casos: ['drink', 'perfume'], janela: 'sopro', simulador: false })).toBe(
      '?caso=drink&caso=perfume&janela=sopro',
    )
    expect(montarQuery({ casos: [], janela: 'arquivo', simulador: true })).toBe('?janela=arquivo&simulador=true')
  })

  it('sem filtros não tem query', () => {
    expect(montarQuery()).toBe('')
  })
})

describe('buscar', () => {
  it('chama /api com a query e devolve o JSON', async () => {
    const fetchFalso = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ rodadas: 12 }) })
    vi.stubGlobal('fetch', fetchFalso)
    const r = await buscar<{ rodadas: number }>('/resumo', { casos: ['drink'], janela: 'arquivo', simulador: false })
    expect(r.rodadas).toBe(12)
    expect(fetchFalso.mock.calls[0][0]).toBe('/api/resumo?caso=drink&janela=arquivo')
  })

  it('erro da API vira exceção com a mensagem', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ detail: 'Rodada não encontrada.' }) }),
    )
    await expect(buscar('/rodadas/x/leituras')).rejects.toThrow('Rodada não encontrada.')
  })

  it('erro sem corpo JSON usa o status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => {
          throw new Error('sem json')
        },
      }),
    )
    await expect(buscar('/resumo')).rejects.toThrow('502')
  })
})
