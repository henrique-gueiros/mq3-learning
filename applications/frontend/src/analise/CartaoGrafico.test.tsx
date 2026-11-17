import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CartaoGrafico } from './CartaoGrafico'

const ok = { isLoading: false, isError: false, error: null, refetch: vi.fn() }

describe('CartaoGrafico', () => {
  it('carregando mostra o skeleton e esconde o conteúdo', () => {
    render(
      <CartaoGrafico titulo="Boxplot" consulta={{ ...ok, isLoading: true }}>
        <p>conteúdo</p>
      </CartaoGrafico>,
    )
    expect(screen.getByRole('status', { name: /carregando/i })).toBeInTheDocument()
    expect(screen.queryByText('conteúdo')).not.toBeInTheDocument()
  })

  it('vazio mostra a mensagem no lugar do conteúdo', () => {
    render(
      <CartaoGrafico titulo="Sopros" consulta={ok} vazio="Nenhum sopro marcado.">
        <p>conteúdo</p>
      </CartaoGrafico>,
    )
    expect(screen.getByText('Nenhum sopro marcado.')).toBeInTheDocument()
    expect(screen.queryByText('conteúdo')).not.toBeInTheDocument()
  })

  it('erro mostra a mensagem da API e tenta de novo', async () => {
    const refetch = vi.fn()
    render(
      <CartaoGrafico
        titulo="Heatmap"
        consulta={{ isLoading: false, isError: true, error: new Error('Banco fora do ar'), refetch }}
      >
        <p>conteúdo</p>
      </CartaoGrafico>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Banco fora do ar')
    await userEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(refetch).toHaveBeenCalled()
  })

  it('falha ao atualizar com dados em cache mantém o conteúdo', () => {
    render(
      <CartaoGrafico titulo="Boxplot" consulta={{ ...ok, isError: true, error: new Error('x'), data: [1] }}>
        <p>conteúdo</p>
      </CartaoGrafico>,
    )
    expect(screen.getByText('conteúdo')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('com dados mostra título, descrição e conteúdo', () => {
    render(
      <CartaoGrafico titulo="Boxplot" descricao="Como cada sensor varia." consulta={ok}>
        <p>conteúdo</p>
      </CartaoGrafico>,
    )
    expect(screen.getByRole('heading', { name: 'Boxplot' })).toBeInTheDocument()
    expect(screen.getByText('Como cada sensor varia.')).toBeInTheDocument()
    expect(screen.getByText('conteúdo')).toBeInTheDocument()
  })
})
