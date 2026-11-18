import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FILTROS_PADRAO } from './filtros'
import { SecaoRodada } from './SecaoRodada'
import { apiFalsa, montar } from './testes/montar'

vi.mock('../graficos/GraficoECharts', () => ({
  GraficoECharts: ({ rotulo }: { rotulo: string }) => <div role="img" aria-label={rotulo} />,
}))

afterEach(() => vi.unstubAllGlobals())

const opcoes = {
  casos: ['clean', 'drink'],
  participantes: ['p01'],
  rodadas: [
    { id: 'sim', caso: 'drink', participante: 'p00', origem: 'simulador', inicio: new Date(2026, 10, 7, 10, 0).toISOString() },
    { id: 'nova', caso: 'drink', participante: 'p01', origem: 'ponte', inicio: new Date(2026, 10, 6, 14, 0).toISOString() },
    { id: 'antiga', caso: 'clean', participante: 'p01', origem: 'ponte', inicio: new Date(2026, 10, 5, 9, 0).toISOString() },
  ],
}

const leituras = (rodada: string, caso: string) => ({
  rodada,
  caso,
  pontos: [{ tempo_s: 0, t_ms: 0, mq3_raw: 800, mq135_raw: 300, humidity_pct: 45, ppm: 0.4, em_sopro: false }],
})

describe('SecaoRodada', () => {
  it('sem escolha mostra a rodada mais recente fora do simulador', async () => {
    const fetchFalso = apiFalsa({
      '/api/filtros': opcoes,
      '/api/rodadas/nova/leituras': leituras('nova', 'drink'),
    })
    montar(<SecaoRodada filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(await screen.findByRole('img', { name: /bebida · p01 · 06\/11\/2026 14:00/ })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Rodada' })).toHaveValue('nova')
    expect(screen.queryByRole('option', { name: /simulador/ })).not.toBeInTheDocument()
    expect(fetchFalso).toHaveBeenCalledWith('/api/rodadas/nova/leituras')
  })

  it('trocar a rodada guarda a escolha nos filtros (na URL)', async () => {
    apiFalsa({ '/api/filtros': opcoes, '/api/rodadas/': leituras('nova', 'drink') })
    const aoMudar = vi.fn()
    montar(<SecaoRodada filtros={FILTROS_PADRAO} aoMudarFiltros={aoMudar} />)
    await userEvent.selectOptions(await screen.findByRole('combobox', { name: 'Rodada' }), 'antiga')
    expect(aoMudar).toHaveBeenCalledWith({ rodada: 'antiga' })
  })

  it('com o simulador ligado a rodada simulada aparece marcada', async () => {
    apiFalsa({ '/api/filtros': opcoes, '/api/rodadas/': leituras('sim', 'drink') })
    montar(<SecaoRodada filtros={{ ...FILTROS_PADRAO, simulador: true }} aoMudarFiltros={() => {}} />)
    expect(await screen.findByRole('option', { name: /bebida · p00 · 07\/11\/2026 10:00 · simulador/ })).toBeInTheDocument()
  })

  it('rodada da URL que sumiu da lista (simulador desligado) sai da URL', async () => {
    apiFalsa({ '/api/filtros': opcoes, '/api/rodadas/': leituras('nova', 'drink') })
    const aoMudar = vi.fn()
    montar(<SecaoRodada filtros={{ ...FILTROS_PADRAO, rodada: 'sim' }} aoMudarFiltros={aoMudar} />)
    expect(await screen.findByRole('combobox', { name: 'Rodada' })).toHaveValue('nova')
    expect(aoMudar).toHaveBeenCalledWith({ rodada: null })
  })

  it('rodada da URL que está na lista fica', async () => {
    apiFalsa({ '/api/filtros': opcoes, '/api/rodadas/': leituras('antiga', 'clean') })
    const aoMudar = vi.fn()
    montar(<SecaoRodada filtros={{ ...FILTROS_PADRAO, rodada: 'antiga' }} aoMudarFiltros={aoMudar} />)
    expect(await screen.findByRole('combobox', { name: 'Rodada' })).toHaveValue('antiga')
    expect(aoMudar).not.toHaveBeenCalled()
  })

  it('sem rodadas explica o vazio', async () => {
    apiFalsa({ '/api/filtros': { ...opcoes, rodadas: [] } })
    montar(<SecaoRodada filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(await screen.findByText(/Nenhuma rodada gravada ainda/)).toBeInTheDocument()
  })
})
