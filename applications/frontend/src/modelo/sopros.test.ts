import { describe, expect, it } from 'vitest'
import { corpoDoSopro, resumoDoSopro, SOPROS } from './sopros'
import { formatarProbabilidade, textoDaClassificacao } from './textos'

describe('sopros de exemplo', () => {
  it('traz perfume, bebida e ambiente, cada um com antes e durante o sopro', () => {
    expect(SOPROS.map((s) => s.id)).toEqual(['perfume', 'bebida', 'ambiente'])
    for (const sopro of SOPROS) {
      const inicio = sopro.blow_start_s * 1000
      const fim = sopro.blow_end_s * 1000
      expect(sopro.leituras.some((l) => l.t_ms < inicio)).toBe(true)
      expect(sopro.leituras.some((l) => l.t_ms >= inicio && l.t_ms <= fim)).toBe(true)
      expect(sopro.origem.endsWith('.csv')).toBe(true)
    }
  })

  it('resume o pico do trecho que o modelo olha e monta o corpo do pedido', () => {
    const perfume = SOPROS[0]
    const resumo = resumoDoSopro(perfume)
    const desde = perfume.blow_start_s * 1000
    const durante = perfume.leituras.filter((l) => l.t_ms >= desde)
    expect(resumo.ppm).toBe(Math.max(...durante.map((l) => l.ppm)))
    expect(resumo.mq135).toBe(Math.max(...durante.map((l) => l.mq135_raw)))
    expect(resumo.umidade).toBe(Math.max(...durante.map((l) => l.humidity_pct)))

    const corpo = corpoDoSopro(perfume)
    expect(corpo.sessao).toBe('leituras_perfume.csv')
    expect(corpo.attempt_id).toBe('demo-perfume')
    expect(corpo.blow_end_s).toBeGreaterThan(corpo.blow_start_s)
    expect(corpo.leituras).toHaveLength(perfume.leituras.length)
  })
})

describe('texto da classificação', () => {
  it('nomeia as duas classes e o caso sem arquivo de modelo', () => {
    expect(textoDaClassificacao({ status: 'classificado', prediction: 'sob_efeito', detalhe: '' }).titulo).toBe('Sob efeito.')
    expect(textoDaClassificacao({ status: 'classificado', prediction: 'sem_efeito', detalhe: '' }).titulo).toBe('Sem efeito.')
    expect(textoDaClassificacao({ status: 'sem_modelo', prediction: null, detalhe: 'falta o arquivo' }).detalhe).toBe('falta o arquivo')
    expect(formatarProbabilidade(0.6635)).toBe('66,4%')
    expect(formatarProbabilidade(null)).toBe('—')
  })
})
