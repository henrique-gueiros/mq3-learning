import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { TemaProvider } from '../tema/TemaProvider'
import { Cabecalho } from './Cabecalho'

const NOME_PAINEL = 'Seções (menu)'

function montar() {
  render(
    <TemaProvider>
      <Cabecalho />
      <p>fora do cabeçalho</p>
    </TemaProvider>,
  )
  return screen.getByRole('button', { name: 'Abrir menu das seções' })
}

describe('menu das seções no celular', () => {
  it('começa fechado e o botão abre e fecha o painel', async () => {
    const botao = montar()
    expect(botao).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('navigation', { name: NOME_PAINEL })).not.toBeInTheDocument()

    await userEvent.click(botao)
    expect(botao).toHaveAttribute('aria-expanded', 'true')
    expect(botao).toHaveAccessibleName('Fechar menu das seções')
    const painel = screen.getByRole('navigation', { name: NOME_PAINEL })
    expect(botao.getAttribute('aria-controls')).toBe(painel.id)
    expect(painel.querySelectorAll('a')).toHaveLength(4)

    await userEvent.click(botao)
    expect(botao).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('navigation', { name: NOME_PAINEL })).not.toBeInTheDocument()
  })

  it('Esc fecha e devolve o foco ao botão', async () => {
    const botao = montar()
    await userEvent.click(botao)
    await userEvent.tab()
    await userEvent.keyboard('{Escape}')
    expect(botao).toHaveAttribute('aria-expanded', 'false')
    expect(botao).toHaveFocus()
  })

  it('escolher um link fecha o painel', async () => {
    const botao = montar()
    await userEvent.click(botao)
    const painel = screen.getByRole('navigation', { name: NOME_PAINEL })
    await userEvent.click(painel.querySelector('a[href="/#rodadas"]') as HTMLElement)
    expect(botao).toHaveAttribute('aria-expanded', 'false')
  })

  it('clicar fora fecha, mas clicar dentro do painel não', async () => {
    const botao = montar()
    await userEvent.click(botao)
    await userEvent.click(screen.getByRole('navigation', { name: NOME_PAINEL }))
    expect(botao).toHaveAttribute('aria-expanded', 'true')
    await userEvent.click(screen.getByText('fora do cabeçalho'))
    expect(botao).toHaveAttribute('aria-expanded', 'false')
  })

  it('Tab não escapa do painel aberto', async () => {
    const botao = montar()
    await userEvent.click(botao)
    const links = screen.getByRole('navigation', { name: NOME_PAINEL }).querySelectorAll('a')
    links[links.length - 1].focus()
    await userEvent.tab()
    expect(links[0]).toHaveFocus()
    await userEvent.tab({ shift: true })
    expect(links[links.length - 1]).toHaveFocus()
  })
})
