import { afterEach, describe, expect, it, vi } from 'vitest'
import { classificarSopro, ErroModelo } from './cliente'
import { SOPROS } from './sopros'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('classificarSopro', () => {
  it('envia o recorte para /modelo/classificar', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'classificado',
        prediction: 'sem_efeito',
        prob_sem_efeito: 1,
        prob_sob_efeito: 0,
        detalhe: '',
        sessao: 'leituras_perfume.csv',
        attempt_id: 'demo-perfume',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const resultado = await classificarSopro(SOPROS[0])

    expect(resultado.prediction).toBe('sem_efeito')
    expect(fetchMock).toHaveBeenCalledWith('/modelo/classificar', expect.objectContaining({ method: 'POST' }))
    const corpo = JSON.parse(fetchMock.mock.calls[0][1].body as string)
    expect(corpo.sessao).toBe('leituras_perfume.csv')
    expect(corpo.leituras.length).toBeGreaterThan(10)
    expect(corpo.leituras[0]).not.toHaveProperty('alcool')
  })

  it('explica quando o serviço está fora do ar', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed')))
    await expect(classificarSopro(SOPROS[1])).rejects.toBeInstanceOf(ErroModelo)
  })
})
