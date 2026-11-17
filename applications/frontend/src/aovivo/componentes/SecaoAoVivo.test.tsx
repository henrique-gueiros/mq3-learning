import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { TemaProvider } from '../../tema/TemaProvider'
import { estadoInicial, reduzir, type EstadoAoVivo } from '../estado'
import type { Mensagem } from '../mensagens'
import { CartaoEstado } from './CartaoEstado'
import { PainelAoVivo } from './PainelAoVivo'

// o ECharts precisa de canvas, que o jsdom não tem; o gráfico é testado pelas opções
vi.mock('./GraficoAoVivo', () => ({ GraficoAoVivo: () => null }))

const leitura = (amostra: number, extra: Record<string, number> = {}): Mensagem => ({
  placa: 'placa01',
  tipo: 'leituras',
  dados: { rodada_id: 'r1', amostra, t_ms: amostra * 1000, mq3_raw: 800, ppm: 0.4, mq135_raw: 250, temperature_c: 28, humidity_pct: 45, ...extra },
})

const montar = (msgs: Mensagem[]): EstadoAoVivo => msgs.reduce((e, m) => reduzir(e, m, 1000), estadoInicial())

describe('CartaoEstado', () => {
  it.each([
    ['calibrando', 'Calibrando.'],
    ['ambiente', 'Ambiente.'],
    ['sopro', 'Sopro detectado.'],
    ['recuperando', 'Recuperando.'],
  ] as const)('estado %s', (estado, titulo) => {
    render(<CartaoEstado estado={estado} segundosNoEstado={12} temDados />)
    expect(screen.getByRole('heading', { name: titulo })).toBeInTheDocument()
    expect(screen.getByText(/estimativa da tela/i)).toBeInTheDocument()
  })

  it('sem dados pede a placa', () => {
    render(<CartaoEstado estado="calibrando" segundosNoEstado={0} temDados={false} />)
    expect(screen.getByRole('heading', { name: 'Aguardando a placa.' })).toBeInTheDocument()
  })
})

describe('PainelAoVivo', () => {
  it('sem leituras mostra como pôr dados na tela', () => {
    render(<TemaProvider><PainelAoVivo estado={estadoInicial()} /></TemaProvider>)
    expect(screen.getByRole('heading', { name: 'Aguardando a placa.' })).toBeInTheDocument()
    expect(screen.getByText(/coleta.simulador/)).toBeInTheDocument()
  })

  it('mostra os três números com a variação em relação à base', () => {
    const e = montar([
      { placa: 'placa01', tipo: 'rodada', dados: { rodada_id: 'r1', placa: 'placa01', caso: 'drink', participante: 'p01', inicio: null, arquivo_sessao: null, origem: 'ponte' } },
      ...Array.from({ length: 30 }, (_, i) => leitura(i)),
      leitura(30, { humidity_pct: 72, mq135_raw: 560, mq3_raw: 1500, ppm: 0.9 }),
      leitura(31, { humidity_pct: 72, mq135_raw: 560, mq3_raw: 1500, ppm: 0.9 }),
    ])
    render(<TemaProvider><PainelAoVivo estado={e} /></TemaProvider>)
    expect(screen.getByRole('heading', { name: 'Sopro detectado.' })).toBeInTheDocument()
    expect(screen.getByText('560')).toBeInTheDocument()
    expect(screen.getByText('+124,0%')).toBeInTheDocument()
    expect(screen.getByText('bebida')).toBeInTheDocument()
  })
})
