import { describe, expect, it } from 'vitest'
import { estadoInicial, reduzir, situacaoPlaca, JANELA_MS, SILENCIO_MS, type EstadoAoVivo } from './estado'
import type { Mensagem } from './mensagens'

const leitura = (amostra: number, extra: Record<string, number | null> = {}, rodada_id = 'r1', placa = 'placa01'): Mensagem => ({
  placa,
  tipo: 'leituras',
  dados: {
    rodada_id, amostra, t_ms: amostra * 1000, mq3_raw: 800, ppm: 0.4, mq135_raw: 250,
    temperature_c: 28, humidity_pct: 45, ...extra,
  },
})

const aplicar = (msgs: Mensagem[], inicio: EstadoAoVivo = estadoInicial(), agora = 1_000) =>
  msgs.reduce((e, m) => reduzir(e, m, agora), inicio)

describe('estado ao vivo', () => {
  it('guarda as leituras e passa cada uma pelo detector', () => {
    const e = aplicar(Array.from({ length: 12 }, (_, i) => leitura(i)))
    expect(e.leituras).toHaveLength(12)
    expect(e.placa).toBe('placa01')
    expect(e.detector.estado).toBe('ambiente')
    expect(e.ultimaLeituraEm).toBe(1_000)
  })

  it('ignora leitura repetida (o MQTT pode reenviar)', () => {
    const e = aplicar([leitura(1), leitura(2), leitura(2)])
    expect(e.leituras.map((l) => l.amostra)).toEqual([1, 2])
  })

  it('mantém só os últimos minutos', () => {
    const passos = JANELA_MS / 1000 + 30
    const e = aplicar(Array.from({ length: passos }, (_, i) => leitura(i)))
    expect(e.leituras[0].t_ms).toBeGreaterThanOrEqual(e.leituras.at(-1)!.t_ms - JANELA_MS)
  })

  it('rodada nova recomeça leituras, eventos e detector', () => {
    const antes = aplicar([...Array.from({ length: 12 }, (_, i) => leitura(i)), { placa: 'placa01', tipo: 'eventos', dados: { rodada_id: 'r1', tipo: 'sopro_inicio', t_ms: 5000 } }])
    const e = aplicar(
      [{ placa: 'placa01', tipo: 'rodada', dados: { rodada_id: 'r2', placa: 'placa01', caso: 'drink', participante: 'p01', inicio: null, arquivo_sessao: null, origem: 'ponte' } }, leitura(1, {}, 'r2')],
      antes,
    )
    expect(e.rodada?.caso).toBe('drink')
    expect(e.leituras).toHaveLength(1)
    expect(e.eventos).toHaveLength(0)
    expect(e.detector.estado).toBe('calibrando')
  })

  it('a mensagem retida da rodada atual não apaga as leituras', () => {
    const rodada: Mensagem = { placa: 'placa01', tipo: 'rodada', dados: { rodada_id: 'r1', placa: 'placa01', caso: 'clean', participante: 'p02', inicio: null, arquivo_sessao: null, origem: 'ponte' } }
    const e = aplicar([leitura(1), leitura(2), rodada])
    expect(e.leituras).toHaveLength(2)
    expect(e.rodada?.caso).toBe('clean')
  })

  it('registra os trechos de cada estado do detector', () => {
    const msgs = [
      ...Array.from({ length: 30 }, (_, i) => leitura(i)),
      ...Array.from({ length: 6 }, (_, i) => leitura(30 + i, { humidity_pct: 72, mq135_raw: 560, mq3_raw: 1500 })),
    ]
    const e = aplicar(msgs)
    expect(e.trechos.map((t) => t.estado)).toEqual(['calibrando', 'ambiente', 'sopro'])
    expect(e.trechos.at(-1)!.fim_ms).toBe(35_000)
  })

  it('avisa sopro detectado, sopro marcado e fim de rodada', () => {
    let e = aplicar(Array.from({ length: 30 }, (_, i) => leitura(i)))
    e = aplicar([leitura(30, { humidity_pct: 72, mq135_raw: 560 }), leitura(31, { humidity_pct: 72, mq135_raw: 560 })], e)
    expect(e.aviso?.texto).toBe('Sopro detectado')
    e = aplicar([{ placa: 'placa01', tipo: 'eventos', dados: { rodada_id: 'r1', tipo: 'sopro_inicio', t_ms: 31000 } }], e)
    expect(e.aviso?.texto).toBe('Sopro marcado na ponte')
    e = aplicar([{ placa: 'placa01', tipo: 'eventos', dados: { rodada_id: 'r1', tipo: 'rodada_fim', t_ms: 40000 } }], e)
    expect(e.aviso?.texto).toBe('Rodada encerrada')
    expect(e.eventos).toHaveLength(2)
  })

  it('segue uma placa só: outra placa não reinicia a tela enquanto a atual envia', () => {
    const rodadaSim: Mensagem = { placa: 'sim', tipo: 'rodada', dados: { rodada_id: 'rs', placa: 'sim', caso: 'perfume', participante: 'p00', inicio: null, arquivo_sessao: null, origem: 'simulador' } }
    const e = aplicar([leitura(1), leitura(2), rodadaSim, leitura(5, {}, 'rs', 'sim'), leitura(3)])
    expect(e.placa).toBe('placa01')
    expect(e.leituras.map((l) => l.amostra)).toEqual([1, 2, 3])
  })

  it('a rodada retida de cada placa é lembrada até a leitura chegar', () => {
    const rodada: Mensagem = { placa: 'placa01', tipo: 'rodada', dados: { rodada_id: 'r1', placa: 'placa01', caso: 'drink', participante: 'p01', inicio: null, arquivo_sessao: null, origem: 'ponte' } }
    const outra: Mensagem = { placa: 'sim', tipo: 'rodada', dados: { rodada_id: 'rs', placa: 'sim', caso: 'perfume', participante: 'p00', inicio: null, arquivo_sessao: null, origem: 'simulador' } }
    const e = aplicar([rodada, outra, leitura(1)])
    expect(e.rodada?.caso).toBe('drink')
  })

  it('troca de placa quando a atual fica em silêncio', () => {
    const inicio = aplicar([leitura(1)], estadoInicial(), 1_000)
    const e = aplicar([leitura(1, {}, 'rs', 'sim')], inicio, 1_000 + SILENCIO_MS + 1)
    expect(e.placa).toBe('sim')
    expect(e.rodada?.rodada_id).toBe('rs')
  })

  it('status de outra placa não muda a situação da placa atual', () => {
    const e = aplicar([leitura(1), { placa: 'sim', tipo: 'status', dados: { estado: 'offline' } }], estadoInicial(), 50_000)
    expect(situacaoPlaca(e, 51_000)).toBe('recebendo')
  })

  it('evento que chega antes da primeira leitura da rodada não se perde', () => {
    const e = aplicar([
      { placa: 'placa01', tipo: 'eventos', dados: { rodada_id: 'r1', tipo: 'sopro_inicio', t_ms: 5000 } },
      leitura(6),
    ])
    expect(e.eventos).toHaveLength(1)
  })

  it('leitura fora de ordem entra no lugar certo e não passa pelo detector', () => {
    const e = aplicar([leitura(1), leitura(3), leitura(2)])
    expect(e.leituras.map((l) => l.amostra)).toEqual([1, 2, 3])
    expect(e.detector.recentes.map((a) => a.t_ms)).toEqual([1000, 3000])
  })

  it('evento de outra placa fica guardado para quando ela assumir', () => {
    let e = aplicar([leitura(1)], estadoInicial(), 1_000)
    e = aplicar([{ placa: 'sim', tipo: 'eventos', dados: { rodada_id: 'rs', tipo: 'sopro_inicio', t_ms: 500 } }], e, 1_000)
    e = aplicar([leitura(2, {}, 'rs', 'sim')], e, 1_000 + SILENCIO_MS + 1)
    expect(e.eventos).toEqual([{ rodada_id: 'rs', tipo: 'sopro_inicio', t_ms: 500 }])
  })

  it('leitura atrasada da rodada anterior não reinicia a rodada nova', () => {
    const nova: Mensagem = { placa: 'placa01', tipo: 'rodada', dados: { rodada_id: 'r2', placa: 'placa01', caso: 'drink', participante: 'p01', inicio: null, arquivo_sessao: null, origem: 'ponte' } }
    const e = aplicar([leitura(1), nova, leitura(1, {}, 'r2'), leitura(9, {}, 'r1'), leitura(2, {}, 'r2')])
    expect(e.rodada?.caso).toBe('drink')
    expect(e.leituras.map((l) => l.amostra)).toEqual([1, 2])
  })

  it('leituras da rodada nova que chegam antes do anúncio dela não se perdem', () => {
    const anuncio = (id: string, caso: string): Mensagem => ({ placa: 'placa01', tipo: 'rodada', dados: { rodada_id: id, placa: 'placa01', caso, participante: 'p01', inicio: null, arquivo_sessao: null, origem: 'ponte' } })
    const e = aplicar([anuncio('r1', 'clean'), leitura(1), leitura(1, {}, 'r2'), leitura(2, {}, 'r2'), anuncio('r2', 'drink'), leitura(3, {}, 'r2'), leitura(9, {}, 'r1')])
    expect(e.rodada?.rodada_id).toBe('r2')
    expect(e.rodada?.caso).toBe('drink')
    expect(e.leituras.map((l) => l.amostra)).toEqual([1, 2, 3])
  })

  it('um aviso por sopro, mesmo que ele passe por "recuperando" e volte', () => {
    const alto = { humidity_pct: 72, mq135_raw: 560, mq3_raw: 1500 }
    const e = aplicar([
      ...Array.from({ length: 30 }, (_, i) => leitura(i)),
      ...Array.from({ length: 5 }, (_, i) => leitura(30 + i, alto)),
      ...Array.from({ length: 6 }, (_, i) => leitura(35 + i)),
      ...Array.from({ length: 4 }, (_, i) => leitura(41 + i, alto)),
    ])
    expect(e.trechos.map((t) => t.estado)).toEqual(['calibrando', 'ambiente', 'sopro', 'recuperando', 'sopro'])
    expect(e.aviso?.id).toBe(1)
  })

  it('situação da placa: recebendo até 10 s sem leitura; offline pelo status', () => {
    const e = aplicar([leitura(1)], estadoInicial(), 50_000)
    expect(situacaoPlaca(e, 55_000)).toBe('recebendo')
    expect(situacaoPlaca(e, 61_000)).toBe('parada')
    expect(situacaoPlaca(estadoInicial(), 0)).toBe('aguardando')
    const off = aplicar([{ placa: 'placa01', tipo: 'status', dados: { estado: 'offline' } }], e, 56_000)
    expect(situacaoPlaca(off, 56_000)).toBe('offline')
  })
})
