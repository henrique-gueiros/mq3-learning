import { describe, expect, it } from 'vitest'
import { parsearMensagem } from './mensagens'

const json = (o: unknown) => JSON.stringify(o)

describe('parsearMensagem', () => {
  it('lê uma leitura com os campos do CSV do firmware', () => {
    const m = parsearMensagem(
      'mq3/placa01/leituras',
      json({ rodada_id: 'r1', amostra: 3, t_ms: 3000, mq3_raw: 812, ppm: 0.41, mq135_raw: 230, mq135_mv: 300, temperature_c: null, humidity_pct: 47.2, alcool: 0 }),
    )
    expect(m).toEqual({
      placa: 'placa01',
      tipo: 'leituras',
      dados: { rodada_id: 'r1', amostra: 3, t_ms: 3000, mq3_raw: 812, ppm: 0.41, mq135_raw: 230, temperature_c: null, humidity_pct: 47.2 },
    })
  })

  it('não guarda o alcool calculado pelo firmware', () => {
    const m = parsearMensagem('mq3/p/leituras', json({ rodada_id: 'r', amostra: 1, t_ms: 0, mq3_raw: 1, alcool: 1 }))
    expect(m && 'alcool' in m.dados).toBe(false)
  })

  it('lê rodada, evento e status', () => {
    expect(parsearMensagem('mq3/p/rodada', json({ rodada_id: 'r', placa: 'p', caso: 'drink', participante: 'p01', inicio: '2026-11-17T10:00:00', arquivo_sessao: 'a.csv', origem: 'ponte' }))?.tipo).toBe('rodada')
    expect(parsearMensagem('mq3/p/eventos', json({ rodada_id: 'r', tipo: 'sopro_inicio', t_ms: 20000 }))?.dados).toEqual({ rodada_id: 'r', tipo: 'sopro_inicio', t_ms: 20000 })
    expect(parsearMensagem('mq3/p/status', json({ estado: 'offline' }))?.dados).toEqual({ estado: 'offline' })
  })

  it('ignora tópico desconhecido, JSON quebrado e campos obrigatórios faltando', () => {
    expect(parsearMensagem('mq3/p/resultado', json({}))).toBeNull()
    expect(parsearMensagem('mq3/p/desconhecido', json({ rodada_id: 'r' }))).toBeNull()
    expect(parsearMensagem('outro/p/leituras', json({}))).toBeNull()
    expect(parsearMensagem('mq3/p/leituras', '{quebrado')).toBeNull()
    expect(parsearMensagem('mq3/p/leituras', json({ rodada_id: 'r', amostra: 1 }))).toBeNull()
    expect(parsearMensagem('mq3/p/eventos', json({ rodada_id: 'r', tipo: 'outro', t_ms: 1 }))).toBeNull()
  })

  it('lê o resultado do servidor do modelo', () => {
    const corpo = {
      rodada_id: 'r', t_ms: 45000, sessao: 'a.csv', attempt_id: 'a@40s', status: 'classificado',
      prediction: 'sob_efeito', prob_sem_efeito: 0.2, prob_sob_efeito: 0.8, detalhe: '',
    }
    expect(parsearMensagem('mq3/p/resultado', json(corpo))).toEqual({ placa: 'p', tipo: 'resultado', dados: corpo })
    expect(parsearMensagem('mq3/p/resultado', json({ ...corpo, prediction: null, status: 'sem_modelo', prob_sob_efeito: null, prob_sem_efeito: null }))?.dados)
      .toMatchObject({ prediction: null, status: 'sem_modelo' })
    expect(parsearMensagem('mq3/p/resultado', json({ ...corpo, prediction: 'outra' }))).toBeNull()
  })
})
