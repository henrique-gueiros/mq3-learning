import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SeloPlaca, Stat } from './exibicao'

describe('Stat', () => {
  it('mostra rótulo, valor, unidade e variação', () => {
    render(<Stat rotulo="Umidade" valor={61.25} casas={1} unidade="%" variacao={12.4} />)
    expect(screen.getByText('Umidade')).toBeInTheDocument()
    expect(screen.getByText('61,3')).toBeInTheDocument()
    expect(screen.getByText('+12,4%')).toBeInTheDocument()
  })

  it('sem valor mostra traço', () => {
    render(<Stat rotulo="PPM" valor={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})

describe('SeloPlaca', () => {
  it.each([
    ['recebendo', 'Recebendo'],
    ['parada', 'Sem leituras'],
    ['offline', 'Placa offline'],
  ] as const)('estado %s', (estado, texto) => {
    render(<SeloPlaca estado={estado} />)
    expect(screen.getByRole('status')).toHaveTextContent(texto)
  })
})
