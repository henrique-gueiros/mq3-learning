import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LimiteDeErro } from './LimiteDeErro'

afterEach(() => vi.restoreAllMocks())

function Quebra(): never {
  throw new Error('chunk não carregou')
}

describe('LimiteDeErro', () => {
  it('sem erro mostra o conteúdo', () => {
    render(
      <LimiteDeErro mensagem="Análise indisponível.">
        <p>análise</p>
      </LimiteDeErro>,
    )
    expect(screen.getByText('análise')).toBeInTheDocument()
  })

  it('com erro mostra a mensagem e o botão de recarregar, e o resto da tela continua', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <>
        <p>ao vivo</p>
        <LimiteDeErro mensagem="Análise indisponível.">
          <Quebra />
        </LimiteDeErro>
      </>,
    )
    expect(screen.getByText('ao vivo')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Análise indisponível.')
    expect(screen.getByRole('button', { name: 'Recarregar a página' })).toBeInTheDocument()
  })
})
