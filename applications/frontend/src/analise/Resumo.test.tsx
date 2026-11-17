import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FILTROS_PADRAO } from './filtros'
import { Resumo } from './Resumo'

afterEach(() => vi.unstubAllGlobals())

const montar = () =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <Resumo filtros={FILTROS_PADRAO} />
    </QueryClientProvider>,
  )

describe('Resumo', () => {
  it('mostra rodadas e leituras formatadas', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ placa: 'parada', rodadas: 12, leituras: 11941 }) }),
    )
    montar()
    expect(await screen.findByText('11.941')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('Rodadas')).toBeInTheDocument()
    expect(screen.getByText('Leituras')).toBeInTheDocument()
  })

  it('com a API fora mostra traço, não quebra', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('rede')))
    montar()
    expect(await screen.findAllByText('—')).toHaveLength(2)
  })
})
