/**
 * Estado da seção "Ao vivo", montado mensagem a mensagem. É uma função pura
 * (reduzir) para poder ser testada sem broker; o hook useAoVivo só a alimenta.
 *
 * A tela acompanha uma placa por vez: a primeira que mandar leituras. Outra placa
 * só assume quando a atual fica em silêncio. Rodada e status de cada placa ficam
 * guardados (as mensagens são retidas e chegam todas ao conectar).
 */

import { novoDetector, passo, type Detector, type EstadoSopro } from './detector'
import type { Evento, Leitura, Mensagem, Resultado, Rodada } from './mensagens'

/** Quanto do passado a tela guarda: o gráfico mostra menos que isso. */
export const JANELA_MS = 5 * 60 * 1000
/** Sem leitura há mais que isso, a placa é dada como parada (e outra pode assumir). */
export const SILENCIO_MS = 10_000

export interface Trecho {
  estado: EstadoSopro
  inicio_ms: number
  fim_ms: number
}

export interface Aviso {
  id: number
  texto: string
  tipo: 'sopro' | 'marcacao' | 'rodada' | 'resultado' | 'alerta'
}

export interface EstadoAoVivo {
  placa: string | null
  rodada: Rodada | null
  leituras: Leitura[]
  /** Eventos da rodada atual. */
  eventos: Evento[]
  detector: Detector
  trechos: Trecho[]
  ultimaLeituraEm: number | null
  aviso: Aviso | null
  /** Última rodada anunciada por placa (mensagem retida). */
  rodadasPorPlaca: Record<string, Rodada>
  statusPorPlaca: Record<string, 'online' | 'offline'>
  /** Eventos de rodadas que ainda não são a atual, por rodada_id. */
  pendentes: Record<string, Evento[]>
  /** Classificações do servidor do modelo, por rodada_id, na ordem em que chegaram. */
  resultadosPorRodada: Record<string, Resultado[]>
}

/** Estado vazio, antes da primeira mensagem do broker. */
export function estadoInicial(): EstadoAoVivo {
  return {
    placa: null, rodada: null, leituras: [], eventos: [], detector: novoDetector(), trechos: [],
    ultimaLeituraEm: null, aviso: null, rodadasPorPlaca: {}, statusPorPlaca: {}, pendentes: {}, resultadosPorRodada: {},
  }
}

const rodadaVazia = (rodada_id: string, placa: string): Rodada => ({
  rodada_id, placa, caso: null, participante: null, inicio: null, arquivo_sessao: null, origem: null,
})

/** Começa outra rodada (ou placa), guardando o que vale para todas. */
function recomecar(e: EstadoAoVivo, placa: string, rodada: Rodada): EstadoAoVivo {
  const { [rodada.rodada_id]: eventos = [], ...outros } = e.pendentes
  // os eventos da rodada que sai voltam para os pendentes, caso ela volte
  const pendentes = e.rodada && e.eventos.length ? { ...outros, [e.rodada.rodada_id]: e.eventos } : outros
  return {
    ...estadoInicial(),
    placa,
    rodada,
    eventos,
    pendentes,
    ultimaLeituraEm: e.ultimaLeituraEm,
    aviso: e.aviso,
    rodadasPorPlaca: e.rodadasPorPlaca,
    statusPorPlaca: e.statusPorPlaca,
    resultadosPorRodada: e.resultadosPorRodada,
  }
}

function avisar(e: EstadoAoVivo, texto: string, tipo: Aviso['tipo']): Aviso {
  return { id: (e.aviso?.id ?? 0) + 1, texto, tipo }
}

const emSilencio = (e: EstadoAoVivo, agora: number) => e.ultimaLeituraEm === null || agora - e.ultimaLeituraEm > SILENCIO_MS

function comLeitura(atual: EstadoAoVivo, l: Leitura, placa: string, agora: number): EstadoAoVivo {
  if (atual.placa !== null && atual.placa !== placa && !emSilencio(atual, agora)) return atual

  // leitura atrasada da rodada anterior desta placa: a rodada nova já foi anunciada
  const anunciadaAgora = atual.rodadasPorPlaca[placa]?.rodada_id
  if (atual.placa === placa && atual.rodada?.rodada_id === anunciadaAgora && l.rodada_id !== anunciadaAgora) return atual

  let e = atual
  if (e.placa !== placa || e.rodada?.rodada_id !== l.rodada_id) {
    const anunciada = e.rodadasPorPlaca[placa]
    e = recomecar(e, placa, anunciada?.rodada_id === l.rodada_id ? anunciada : rodadaVazia(l.rodada_id, placa))
  }
  if (e.leituras.some((x) => x.amostra === l.amostra)) return e

  const statusPorPlaca = { ...e.statusPorPlaca, [placa]: 'online' as const }
  const ultima = e.leituras.at(-1)

  // fora de ordem (reenvio): entra no gráfico no lugar certo, mas o detector já passou desse ponto
  if (ultima && l.t_ms < ultima.t_ms) {
    const leituras = [...e.leituras, l].sort((a, b) => a.t_ms - b.t_ms)
    return { ...e, leituras, ultimaLeituraEm: agora, statusPorPlaca }
  }

  const detector = passo(e.detector, { t_ms: l.t_ms, umid: l.humidity_pct, mq135: l.mq135_raw, mq3: l.mq3_raw, ppm: l.ppm })
  const corte = l.t_ms - JANELA_MS
  const leituras = [...e.leituras, l].filter((x) => x.t_ms >= corte)

  const ultimo = e.trechos.at(-1)
  const trechos =
    ultimo && ultimo.estado === detector.estado
      ? [...e.trechos.slice(0, -1), { ...ultimo, fim_ms: l.t_ms }]
      : [...e.trechos, { estado: detector.estado, inicio_ms: l.t_ms, fim_ms: l.t_ms }]

  // o aviso é para um sopro novo, não para a volta de "recuperando"
  const comecouSopro = detector.estado === 'sopro' && (e.detector.estado === 'ambiente' || e.detector.estado === 'calibrando')
  return {
    ...e,
    leituras,
    detector,
    trechos: trechos.filter((t) => t.fim_ms >= corte),
    ultimaLeituraEm: agora,
    statusPorPlaca,
    aviso: comecouSopro ? avisar(e, 'Sopro detectado', 'sopro') : e.aviso,
  }
}

function comEvento(e: EstadoAoVivo, ev: Evento): EstadoAoVivo {
  if (e.rodada?.rodada_id !== ev.rodada_id) {
    const lista = e.pendentes[ev.rodada_id] ?? []
    if (lista.some((x) => x.tipo === ev.tipo && x.t_ms === ev.t_ms)) return e
    return { ...e, pendentes: { ...e.pendentes, [ev.rodada_id]: [...lista, ev] } }
  }
  if (e.eventos.some((x) => x.tipo === ev.tipo && x.t_ms === ev.t_ms)) return e
  const eventos = [...e.eventos, ev]
  if (ev.tipo === 'sopro_inicio') return { ...e, eventos, aviso: avisar(e, 'Sopro marcado na ponte', 'marcacao') }
  if (ev.tipo === 'rodada_fim') return { ...e, eventos, aviso: avisar(e, 'Rodada encerrada', 'rodada') }
  return { ...e, eventos }
}

function comResultado(e: EstadoAoVivo, r: Resultado): EstadoAoVivo {
  const lista = e.resultadosPorRodada[r.rodada_id] ?? []
  if (lista.some((x) => x.t_ms === r.t_ms)) return e
  const resultadosPorRodada = { ...e.resultadosPorRodada, [r.rodada_id]: [...lista, r] }
  if (e.rodada?.rodada_id !== r.rodada_id) return { ...e, resultadosPorRodada }
  const aviso =
    r.prediction === 'sob_efeito'
      ? avisar(e, 'Alerta: o modelo classificou o sopro como sob efeito', 'alerta')
      : avisar(e, r.prediction === 'sem_efeito' ? 'Modelo: sem efeito' : 'Modelo: sem classificação', 'resultado')
  return { ...e, resultadosPorRodada, aviso }
}

/** Aplica uma mensagem do broker. `agora` é o relógio do navegador (ms). */
export function reduzir(e: EstadoAoVivo, m: Mensagem, agora: number): EstadoAoVivo {
  switch (m.tipo) {
    case 'leituras':
      return comLeitura(e, m.dados, m.placa, agora)

    case 'rodada': {
      const anotado = { ...e, rodadasPorPlaca: { ...e.rodadasPorPlaca, [m.placa]: m.dados } }
      if (e.placa !== m.placa) return anotado
      // a mensagem é retida: chega de novo a cada reconexão sem ser rodada nova
      return e.rodada?.rodada_id === m.dados.rodada_id ? { ...anotado, rodada: m.dados } : recomecar(anotado, m.placa, m.dados)
    }

    case 'eventos':
      // de outra placa: fica guardado, caso a tela passe a seguir essa placa
      return comEvento(e, m.dados)

    case 'resultado':
      return comResultado(e, m.dados)

    case 'status':
      return { ...e, statusPorPlaca: { ...e.statusPorPlaca, [m.placa]: m.dados.estado } }
  }
}

export type SituacaoPlaca = 'recebendo' | 'parada' | 'offline' | 'aguardando'

/** Situação da placa seguida: offline pelo status, recebendo até 10 s sem leitura, ou parada. */
export function situacaoPlaca(e: EstadoAoVivo, agora: number): SituacaoPlaca {
  if (e.placa === null) return 'aguardando'
  if (e.statusPorPlaca[e.placa] === 'offline') return 'offline'
  if (!emSilencio(e, agora)) return 'recebendo'
  return 'parada'
}
