import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TemaProvider } from '../tema/TemaProvider'
import { BarraFiltros } from './BarraFiltros'
import { FILTROS_PADRAO, type Filtros } from './filtros'

afterEach(() => vi.unstubAllGlobals())

const RESPOSTA_OK = {
  ok: true,
  json: async () => ({ casos: ['drink', 'clean', 'perfume'], participantes: ['equipe'], rodadas: [] }),
}

function montar(filtros: Filtros = FILTROS_PADRAO, fetchFalso = vi.fn().mockResolvedValue(RESPOSTA_OK)) {
  vi.stubGlobal('fetch', fetchFalso)
  const aoMudar = vi.fn()
  render(
    <TemaProvider>
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <BarraFiltros filtros={filtros} aoMudar={aoMudar} />
      </QueryClientProvider>
    </TemaProvider>,
  )
  return aoMudar
}

describe('BarraFiltros', () => {
  it('mostra um chip por caso, na ordem do protocolo, com nome em português', async () => {
    montar()
    const chips = await screen.findAllByRole('button', { name: /ambiente|bebida|perfume/ })
    expect(chips.map((c) => c.textContent)).toEqual(['ambiente', 'bebida', 'perfume'])
    // nenhum caso marcado = todos: os chips aparecem todos ativos
    chips.forEach((c) => expect(c).toHaveAttribute('aria-pressed', 'true'))
  })

  it('clicar num chip escolhe só aquele caso', async () => {
    const aoMudar = montar()
    await userEvent.click(await screen.findByRole('button', { name: 'bebida' }))
    expect(aoMudar).toHaveBeenCalledWith({ casos: ['drink'] })
  })

  it('desmarcar o último caso volta a todos', async () => {
    const aoMudar = montar({ ...FILTROS_PADRAO, casos: ['drink'] })
    await userEvent.click(await screen.findByRole('button', { name: 'bebida' }))
    expect(aoMudar).toHaveBeenCalledWith({ casos: [] })
  })

  it('o segmentado troca a janela', async () => {
    const aoMudar = montar()
    await userEvent.click(screen.getByRole('radio', { name: 'Só o sopro' }))
    expect(aoMudar).toHaveBeenCalledWith({ janela: 'sopro' })
  })

  it('o interruptor inclui o simulador', async () => {
    const aoMudar = montar()
    await userEvent.click(screen.getByRole('switch', { name: 'Incluir simulador' }))
    expect(aoMudar).toHaveBeenCalledWith({ simulador: true })
  })

  it('sem /api/filtros avisa que os casos não vieram e tenta de novo', async () => {
    const fetchFalso = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: 'Banco fora do ar.' }) })
      .mockResolvedValue(RESPOSTA_OK)
    montar(FILTROS_PADRAO, fetchFalso)
    expect(await screen.findByText('Casos indisponíveis.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(await screen.findByRole('button', { name: 'bebida' })).toBeInTheDocument()
  })

  it('não oferece filtro de participante', () => {
    montar()
    expect(screen.queryByText(/participante/i)).not.toBeInTheDocument()
  })
})
