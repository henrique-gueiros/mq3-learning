import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FILTROS_PADRAO } from './filtros'
import { Resumo } from './Resumo'

afterEach(() => vi.unstubAllGlobals())

const cliente = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })

const montar = () =>
  render(
    <QueryClientProvider client={cliente()}>
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

  it('ao trocar o filtro os números antigos ficam marcados como atualizando', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        url.includes('caso=drink')
          ? new Promise(() => {})
          : Promise.resolve({ ok: true, json: async () => ({ placa: 'parada', rodadas: 12, leituras: 11941 }) }),
      ),
    )
    const c = cliente()
    const { rerender } = render(
      <QueryClientProvider client={c}>
        <Resumo filtros={FILTROS_PADRAO} />
      </QueryClientProvider>,
    )
    const numero = await screen.findByText('11.941')
    expect(numero.closest('.resumo')).toHaveAttribute('aria-busy', 'false')
    rerender(
      <QueryClientProvider client={c}>
        <Resumo filtros={{ ...FILTROS_PADRAO, casos: ['drink'] }} />
      </QueryClientProvider>,
    )
    expect(screen.getByText('11.941').closest('.resumo')).toHaveAttribute('aria-busy', 'true')
  })

  it('carregando mostra traço e nenhum erro', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))
    montar()
    expect(screen.getAllByText('—')).toHaveLength(2)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('com a API fora mostra traço e o erro, sem confundir com carregando', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({ detail: 'Banco fora do ar.' }) }),
    )
    montar()
    expect(await screen.findByRole('alert')).toHaveTextContent('Banco fora do ar.')
    expect(screen.getAllByText('—')).toHaveLength(2)
  })
})
