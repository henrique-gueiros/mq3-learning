import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FILTROS_PADRAO } from './filtros'
import { SecaoComparacao } from './SecaoComparacao'
import { apiFalsa, montar } from './testes/montar'

vi.mock('../graficos/GraficoECharts', () => ({
  GraficoECharts: ({ rotulo }: { rotulo: string }) => <div role="img" aria-label={rotulo} />,
}))

afterEach(() => vi.unstubAllGlobals())

const p = { p5: 1, p25: 2, p50: 3, p75: 4, p95: 5, media: 3 }

describe('SecaoComparacao', () => {
  it('mostra boxplot, heatmap e dispersão com os dados da API', async () => {
    apiFalsa({
      '/api/distribuicao': [{ caso: 'clean', n: 10, mq3: p, mq135: p, umid: p }],
      '/api/heatmap': [{ caso: 'drink', mq3: 50, mq135: 20, umid: 30 }],
      '/api/dispersao': [{ caso: 'clean', mq3_raw: 800, mq135_raw: 300 }],
    })
    montar(<SecaoComparacao filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(screen.getByRole('heading', { name: 'Comparação entre os casos.' })).toBeInTheDocument()
    expect(await screen.findByRole('img', { name: /distribuição/i })).toBeInTheDocument()
    expect(await screen.findByRole('img', { name: /em relação ao ambiente/i })).toBeInTheDocument()
    expect(await screen.findByRole('img', { name: /MQ-3 × MQ-135/i })).toBeInTheDocument()
  })

  it('sem rodadas de ambiente o heatmap explica o que falta', async () => {
    apiFalsa({ '/api/distribuicao': [], '/api/heatmap': [], '/api/dispersao': [] })
    montar(<SecaoComparacao filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(await screen.findByText(/Precisa de rodadas de ambiente/)).toBeInTheDocument()
    expect(screen.getAllByText(/Sem leituras para os filtros escolhidos/)).toHaveLength(2)
  })

  it('só "ambiente" marcado: o heatmap pede outro caso (não diz que falta ambiente)', async () => {
    apiFalsa({ '/api/distribuicao': [], '/api/heatmap': [], '/api/dispersao': [] })
    montar(<SecaoComparacao filtros={{ ...FILTROS_PADRAO, casos: ['clean'] }} aoMudarFiltros={() => {}} />)
    expect(await screen.findByText(/Marque outro caso além de ambiente/)).toBeInTheDocument()
    expect(screen.queryByText(/Precisa de rodadas de ambiente/)).not.toBeInTheDocument()
  })

  it('erro de uma rota fica só no cartão dela', async () => {
    apiFalsa({
      '/api/distribuicao': [{ caso: 'clean', n: 10, mq3: p, mq135: p, umid: p }],
      '/api/heatmap': new Error('Banco fora do ar.'),
      '/api/dispersao': [{ caso: 'clean', mq3_raw: 800, mq135_raw: 300 }],
    })
    montar(<SecaoComparacao filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Banco fora do ar.')
    expect(await screen.findByRole('img', { name: /distribuição/i })).toBeInTheDocument()
  })
})
