import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FILTROS_PADRAO } from './filtros'
import { SecaoRodadas } from './SecaoRodadas'
import { apiFalsa, montar } from './testes/montar'

vi.mock('../graficos/GraficoECharts', () => ({
  GraficoECharts: ({ rotulo }: { rotulo: string }) => <div role="img" aria-label={rotulo} />,
}))

afterEach(() => vi.unstubAllGlobals())

describe('SecaoRodadas', () => {
  it('desenha as rodadas sobrepostas e diz quantas são', async () => {
    apiFalsa({
      '/api/sobrepostas': [
        { rodada: 'r1', caso: 'drink', pontos: [[0, 50, 400, 0.4]] },
        { rodada: 'r2', caso: 'clean', pontos: [[0, 45, 300, 0.3]] },
      ],
    })
    montar(<SecaoRodadas filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(screen.getByRole('heading', { name: 'Todas as rodadas juntas.' })).toBeInTheDocument()
    expect(await screen.findByRole('img', { name: /2 rodadas sobrepostas/i })).toBeInTheDocument()
  })

  it('sem rodadas mostra o vazio', async () => {
    apiFalsa({ '/api/sobrepostas': [] })
    montar(<SecaoRodadas filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(await screen.findByText(/Sem leituras para os filtros escolhidos/)).toBeInTheDocument()
  })
})
