import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { BotaoTema } from './BotaoTema'
import { TemaProvider } from './TemaProvider'

describe('troca de tema', () => {
  beforeEach(() => {
    localStorage.clear()
    delete document.documentElement.dataset.theme
  })

  it('começa escuro e alterna para o claro, guardando a escolha', async () => {
    render(<TemaProvider><BotaoTema /></TemaProvider>)
    expect(document.documentElement.dataset.theme).toBe('escuro')
    await userEvent.click(screen.getByRole('button', { name: 'Usar tema claro' }))
    expect(document.documentElement.dataset.theme).toBe('claro')
    expect(localStorage.getItem('mq3-tema')).toBe('claro')
    expect(screen.getByRole('button', { name: 'Usar tema escuro' })).toBeInTheDocument()
  })
})
