import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TemaProvider } from '../tema/TemaProvider'
import { BarraFiltros } from './BarraFiltros'
import { FILTROS_PADRAO, type Filtros } from './filtros'

afterEach(() => vi.unstubAllGlobals())

function montar(filtros: Filtros = FILTROS_PADRAO) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ casos: ['drink', 'clean', 'perfume'], participantes: ['equipe'], rodadas: [] }),
    }),
  )
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

  it('não oferece filtro de participante', () => {
    montar()
    expect(screen.queryByText(/participante/i)).not.toBeInTheDocument()
  })
})
