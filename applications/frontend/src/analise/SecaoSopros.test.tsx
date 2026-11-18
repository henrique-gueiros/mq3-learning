import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FILTROS_PADRAO } from './filtros'
import { SecaoSopros } from './SecaoSopros'
import { apiFalsa, montar } from './testes/montar'

vi.mock('../graficos/GraficoECharts', () => ({
  GraficoECharts: ({ rotulo }: { rotulo: string }) => <div role="img" aria-label={rotulo} />,
}))

afterEach(() => vi.unstubAllGlobals())

const semSopro = [
  { rodada_id: 'r1', caso: 'drink', participante: 'p01', arquivo: '2026-11-12_equipe_drink_4.csv', inicio: new Date(2026, 10, 12, 20, 5).toISOString() },
]

describe('SecaoSopros', () => {
  it('mostra a dispersão das subidas e a tabela das rodadas sem sopro', async () => {
    apiFalsa({
      '/api/sopros': [{ caso: 'drink', subida_mq3: 900, subida_mq135: 400 }],
      '/api/rodadas-sem-sopro': semSopro,
    })
    montar(<SecaoSopros filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(screen.getByRole('heading', { name: 'Sopros marcados.' })).toBeInTheDocument()
    expect(await screen.findByRole('img', { name: /subida por sopro/i })).toBeInTheDocument()
    const tabela = await screen.findByRole('table', { name: /rodadas sem sopro marcado/i })
    const [cabecalho, linha] = within(tabela).getAllByRole('row')
    expect(within(cabecalho).getAllByRole('columnheader').map((c) => c.textContent)).toEqual(['Rodada', 'Início'])
    const [rodada, inicio] = within(linha).getAllByRole('cell')
    expect(within(rodada).getByText('bebida · p01')).toBeInTheDocument()
    expect(within(rodada).getByText('2026-11-12_equipe_drink_4.csv')).toHaveAttribute('title', '2026-11-12_equipe_drink_4.csv')
    expect(inicio).toHaveTextContent('12/11/2026 20:05')
  })

  it('sem sopros explica como marcar', async () => {
    apiFalsa({ '/api/sopros': [], '/api/rodadas-sem-sopro': [] })
    montar(<SecaoSopros filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(await screen.findByText(/Nenhum sopro marcado\. Marque com Enter na ponte ou em attempts\.csv\./)).toBeInTheDocument()
    expect(await screen.findByText(/Todas as rodadas têm sopro marcado/)).toBeInTheDocument()
  })
})
