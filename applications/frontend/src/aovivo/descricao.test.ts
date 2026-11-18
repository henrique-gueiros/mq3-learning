import { describe, expect, it } from 'vitest'
import { descricaoAoVivo } from './descricao'

describe('descricaoAoVivo', () => {
  it('sem leitura não promete que algo está chegando', () => {
    expect(descricaoAoVivo('online', false)).toMatch(/Nenhuma leitura chegou ainda/)
  })

  it('com leitura diz o que a placa está mandando', () => {
    expect(descricaoAoVivo('online', true)).toMatch(/Leituras chegando da placa agora/)
  })

  it('sem broker explica a reconexão', () => {
    expect(descricaoAoVivo('sem-broker', false)).toMatch(/Sem conexão com o broker/)
  })
})