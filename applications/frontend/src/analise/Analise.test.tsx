import { screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import { Analise } from './Analise'
import { FILTROS_PADRAO } from './filtros'
import { apiFalsa, montar } from './testes/montar'

vi.mock('../graficos/GraficoECharts', () => ({
  GraficoECharts: ({ rotulo }: { rotulo: string }) => <div role="img" aria-label={rotulo} />,
}))

let rolar: Mock<Element['scrollIntoView']>
beforeEach(() => {
  rolar = vi.fn<Element['scrollIntoView']>()
  Element.prototype.scrollIntoView = rolar
})
afterEach(() => {
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
  window.scrollY = 0
  delete (Element.prototype as Partial<Element>).scrollIntoView
})

const vazio = { casos: [], participantes: [], rodadas: [] }
const terminou = () => screen.findByText(/Nenhum sopro marcado/)

describe('Analise', () => {
  it('mostra a barra de filtros, o resumo e as quatro seções', async () => {
    apiFalsa({ '/api/filtros': vazio, '/api/resumo': { placa: 'parada', rodadas: 0, leituras: 0 }, '/api/': [] })
    montar(<Analise filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    for (const titulo of ['Comparação entre os casos.', 'Todas as rodadas juntas.', 'Rodada selecionada.', 'Sopros marcados.']) {
      expect(screen.getByRole('heading', { name: titulo })).toBeInTheDocument()
    }
    expect(screen.getByRole('radio', { name: 'Só o sopro' })).toBeInTheDocument()
    await terminou()
  })

  it('carregada depois da página, rola até a seção do endereço (#sopros) e de novo quando os gráficos chegam', async () => {
    apiFalsa({ '/api/': [] })
    window.history.replaceState(null, '', '/#sopros')
    montar(<Analise filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(rolar).toHaveBeenCalledTimes(1)
    // os gráficos acima mudam de altura ao chegar; a segunda rolagem corrige o lugar, uma vez só
    await waitFor(() => expect(rolar).toHaveBeenCalledTimes(2))
    expect(rolar.mock.contexts.every((alvo) => alvo === document.getElementById('sopros'))).toBe(true)
  })

  it('se a pessoa rolou enquanto carregava, não puxa de volta', async () => {
    apiFalsa({ '/api/': [] })
    window.history.replaceState(null, '', '/#sopros')
    montar(<Analise filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    expect(rolar).toHaveBeenCalledTimes(1)
    window.scrollY = 500
    await terminou()
    expect(rolar).toHaveBeenCalledTimes(1)
  })

  it('sem âncora no endereço não rola', async () => {
    apiFalsa({ '/api/': [] })
    montar(<Analise filtros={FILTROS_PADRAO} aoMudarFiltros={() => {}} />)
    await terminou()
    expect(rolar).not.toHaveBeenCalled()
  })
})
