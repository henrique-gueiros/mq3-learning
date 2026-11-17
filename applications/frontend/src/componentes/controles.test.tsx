import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Chip, Interruptor, Segmentado } from './controles'

describe('Segmentado', () => {
  it('marca a opção atual e avisa a escolhida', async () => {
    const aoMudar = vi.fn()
    render(
      <Segmentado
        rotulo="Janela"
        valor="arquivo"
        aoMudar={aoMudar}
        opcoes={[{ valor: 'arquivo', rotulo: 'Arquivo' }, { valor: 'sopro', rotulo: 'Sopro' }]}
      />,
    )
    expect(screen.getByRole('radio', { name: 'Arquivo' })).toHaveAttribute('aria-checked', 'true')
    await userEvent.click(screen.getByRole('radio', { name: 'Sopro' }))
    expect(aoMudar).toHaveBeenCalledWith('sopro')
  })
})

describe('Chip', () => {
  it('é um botão que alterna', async () => {
    const aoAlternar = vi.fn()
    render(<Chip rotulo="bebida" ativo={false} aoAlternar={aoAlternar} />)
    const chip = screen.getByRole('button', { name: 'bebida' })
    expect(chip).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(chip)
    expect(aoAlternar).toHaveBeenCalled()
  })
})

describe('Interruptor', () => {
  it('liga e desliga', async () => {
    const aoMudar = vi.fn()
    render(<Interruptor rotulo="Incluir simulador" ligado={false} aoMudar={aoMudar} />)
    const chave = screen.getByRole('switch', { name: 'Incluir simulador' })
    expect(chave).toHaveAttribute('aria-checked', 'false')
    await userEvent.click(chave)
    expect(aoMudar).toHaveBeenCalledWith(true)
  })
})
