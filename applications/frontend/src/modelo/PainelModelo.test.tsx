import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TemaProvider } from '../tema/TemaProvider'
import { classificarSopro } from './cliente'
import { PainelModelo } from './PainelModelo'
import type { ResultadoModelo } from './tipos'

vi.mock('./cliente', () => ({ classificarSopro: vi.fn() }))

function resultado(parcial: Partial<ResultadoModelo>): ResultadoModelo {
  return {
    sessao: 'leituras_bebida1.csv',
    attempt_id: 'demo-bebida',
    status: 'classificado',
    prediction: 'sob_efeito',
    prob_sem_efeito: 0.3365,
    prob_sob_efeito: 0.6635,
    detalhe: '',
    ...parcial,
  }
}

describe('PainelModelo', () => {
  beforeEach(() => {
    vi.mocked(classificarSopro).mockReset()
  })

  it('mostra os três sopros e a classe assim que o modelo responde', async () => {
    vi.mocked(classificarSopro).mockResolvedValue(resultado({}))
    render(
      <TemaProvider>
        <PainelModelo />
      </TemaProvider>,
    )

    expect(screen.getByRole('heading', { name: 'Aguardando um sopro.' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Perfume' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Bebida' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sem bebida' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Classificar o sopro de Bebida' }))

    expect(await screen.findByRole('heading', { name: 'Sob efeito.' })).toBeInTheDocument()
    expect(screen.getByText('Alerta de detecção.')).toBeInTheDocument()
    expect(screen.getByText('66,4%')).toBeInTheDocument()
    expect(screen.getByText(/leituras_bebida1.csv/)).toBeInTheDocument()
    expect(vi.mocked(classificarSopro).mock.calls[0][0].id).toBe('bebida')
  })

  it('mostra sem efeito para o perfume e explica quando o serviço cai', async () => {
    vi.mocked(classificarSopro).mockResolvedValueOnce(
      resultado({
        sessao: 'leituras_perfume.csv',
        attempt_id: 'demo-perfume',
        prediction: 'sem_efeito',
        prob_sem_efeito: 1,
        prob_sob_efeito: 0,
      }),
    )
    render(
      <TemaProvider>
        <PainelModelo />
      </TemaProvider>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Classificar o sopro de Perfume' }))
    expect(await screen.findByRole('heading', { name: 'Sem efeito.' })).toBeInTheDocument()
    expect(screen.queryByText('Alerta de detecção.')).not.toBeInTheDocument()

    vi.mocked(classificarSopro).mockRejectedValueOnce(new Error('O serviço do modelo não está no ar.'))
    await userEvent.click(screen.getByRole('button', { name: 'Classificar o sopro de Sem bebida' }))
    expect(await screen.findByRole('heading', { name: 'O modelo não respondeu.' })).toBeInTheDocument()
    expect(screen.getByText('O serviço do modelo não está no ar.')).toBeInTheDocument()
  })
})
