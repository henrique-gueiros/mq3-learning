import { describe, expect, it } from 'vitest'
import { opcoesDispersao } from './dispersao'
import { opcoesDistribuicao } from './distribuicao'
import { opcoesHeatmap } from './heatmap'
import { opcoesRodada } from './rodada'
import { opcoesSobrepostas } from './sobrepostas'
import { opcoesSubida } from './subida'
import { CORES_TESTE as cores } from './testes/cores'

const p = { p5: 1, p25: 2, p50: 3, p75: 4, p95: 5, media: 3 }
const base = { cores, tema: 'escuro' as const }

// O GraficoECharts troca as séries por `id` (replaceMerge): a que continua anima, a que saiu some.
const GRAFICOS = {
  distribuicao: opcoesDistribuicao({ ...base, dados: [{ caso: 'clean', n: 1, mq3: p, mq135: p, umid: p }, { caso: 'drink', n: 1, mq3: p, mq135: p, umid: p }] }),
  heatmap: opcoesHeatmap({ ...base, dados: [{ caso: 'drink', mq3: 10, mq135: 20, umid: 30 }] }),
  dispersao: opcoesDispersao({ ...base, dados: [{ caso: 'clean', mq3_raw: 1, mq135_raw: 2 }, { caso: 'drink', mq3_raw: 3, mq135_raw: 4 }] }),
  sobrepostas: opcoesSobrepostas({ ...base, dados: [{ rodada: 'r1', caso: 'drink', pontos: [[0, 1, 2, 3]] }] }),
  rodada: opcoesRodada({ ...base, dados: { rodada: 'r1', caso: 'drink', pontos: [{ tempo_s: 0, t_ms: 0, mq3_raw: 1, mq135_raw: 2, humidity_pct: 3, ppm: 0, em_sopro: false }] } }),
  subida: opcoesSubida({ ...base, dados: [{ caso: 'drink', subida_mq3: 1, subida_mq135: 2 }] }),
}

describe('séries com id', () => {
  for (const [nome, opcoes] of Object.entries(GRAFICOS)) {
    it(`${nome}: toda série tem id, sem repetir`, () => {
      const ids = (opcoes.series as { id?: string }[]).map((s) => s.id)
      expect(ids.every((id) => typeof id === 'string' && id.length > 0)).toBe(true)
      expect(new Set(ids).size).toBe(ids.length)
    })
  }
})
