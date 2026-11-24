/**
 * Mensagens MQTT da coleta, como o navegador as recebe. O formato é o de
 * applications/coleta/mensagens.py: tópico mq3/<placa>/<tipo> e corpo em JSON.
 *
 * O `alcool` (e o mq135_mv) do firmware não entram: a tela não usa a regra do firmware.
 */

export interface Rodada {
  rodada_id: string
  placa: string
  caso: string | null
  participante: string | null
  inicio: string | null
  arquivo_sessao: string | null
  origem: string | null
}

export interface Leitura {
  rodada_id: string
  amostra: number
  t_ms: number
  mq3_raw: number
  ppm: number | null
  mq135_raw: number | null
  temperature_c: number | null
  humidity_pct: number | null
}

export type TipoEvento = 'sopro_inicio' | 'sopro_fim' | 'rodada_fim'

export interface Evento {
  rodada_id: string
  tipo: TipoEvento
  t_ms: number
}

export interface Status {
  estado: 'online' | 'offline'
}

/** Resposta do servidor do modelo para um sopro_fim (services/mq3mqtt/ao_vivo.py). */
export interface Resultado {
  rodada_id: string
  /** t_ms do sopro_fim que o servidor classificou. */
  t_ms: number
  sessao: string
  attempt_id: string | null
  status: string
  prediction: 'sob_efeito' | 'sem_efeito' | null
  prob_sem_efeito: number | null
  prob_sob_efeito: number | null
  detalhe: string
}

export type Mensagem =
  | { placa: string; tipo: 'rodada'; dados: Rodada }
  | { placa: string; tipo: 'leituras'; dados: Leitura }
  | { placa: string; tipo: 'eventos'; dados: Evento }
  | { placa: string; tipo: 'status'; dados: Status }
  | { placa: string; tipo: 'resultado'; dados: Resultado }

export const TOPICOS = ['mq3/+/rodada', 'mq3/+/leituras', 'mq3/+/eventos', 'mq3/+/status', 'mq3/+/resultado']

type Objeto = Record<string, unknown>

const numero = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)
const texto = (v: unknown): string | null => (typeof v === 'string' ? v : null)

function lerLeitura(o: Objeto): Leitura | null {
  const rodada_id = texto(o.rodada_id)
  const amostra = numero(o.amostra)
  const t_ms = numero(o.t_ms)
  const mq3_raw = numero(o.mq3_raw)
  if (rodada_id === null || amostra === null || t_ms === null || mq3_raw === null) return null
  return {
    rodada_id,
    amostra,
    t_ms,
    mq3_raw,
    ppm: numero(o.ppm),
    mq135_raw: numero(o.mq135_raw),
    temperature_c: numero(o.temperature_c),
    humidity_pct: numero(o.humidity_pct),
  }
}

function lerEvento(o: Objeto): Evento | null {
  const rodada_id = texto(o.rodada_id)
  const t_ms = numero(o.t_ms)
  const tipo = o.tipo
  if (rodada_id === null || t_ms === null) return null
  if (tipo !== 'sopro_inicio' && tipo !== 'sopro_fim' && tipo !== 'rodada_fim') return null
  return { rodada_id, tipo, t_ms }
}

function lerRodada(o: Objeto, placa: string): Rodada | null {
  const rodada_id = texto(o.rodada_id)
  if (rodada_id === null) return null
  return {
    rodada_id,
    placa: texto(o.placa) ?? placa,
    caso: texto(o.caso),
    participante: texto(o.participante),
    inicio: texto(o.inicio),
    arquivo_sessao: texto(o.arquivo_sessao),
    origem: texto(o.origem),
  }
}

function lerResultado(o: Objeto): Resultado | null {
  const rodada_id = texto(o.rodada_id)
  const t_ms = numero(o.t_ms)
  const status = texto(o.status)
  const p = o.prediction
  if (rodada_id === null || t_ms === null || status === null) return null
  if (p !== null && p !== 'sob_efeito' && p !== 'sem_efeito') return null
  return {
    rodada_id,
    t_ms,
    sessao: texto(o.sessao) ?? '',
    attempt_id: texto(o.attempt_id),
    status,
    prediction: p,
    prob_sem_efeito: numero(o.prob_sem_efeito),
    prob_sob_efeito: numero(o.prob_sob_efeito),
    detalhe: texto(o.detalhe) ?? '',
  }
}

/** Converte uma mensagem do broker; devolve `null` para o que a tela não usa ou não entende. */
export function parsearMensagem(topico: string, corpo: string): Mensagem | null {
  const partes = topico.split('/')
  if (partes.length !== 3 || partes[0] !== 'mq3') return null
  const [, placa, tipo] = partes
  let o: unknown
  try {
    o = JSON.parse(corpo)
  } catch {
    return null
  }
  if (typeof o !== 'object' || o === null) return null
  const objeto = o as Objeto
  switch (tipo) {
    case 'leituras': {
      const dados = lerLeitura(objeto)
      return dados && { placa, tipo, dados }
    }
    case 'eventos': {
      const dados = lerEvento(objeto)
      return dados && { placa, tipo, dados }
    }
    case 'rodada': {
      const dados = lerRodada(objeto, placa)
      return dados && { placa, tipo, dados }
    }
    case 'resultado': {
      const dados = lerResultado(objeto)
      return dados && { placa, tipo, dados }
    }
    case 'status':
      return objeto.estado === 'online' || objeto.estado === 'offline'
        ? { placa, tipo, dados: { estado: objeto.estado } }
        : null
    default:
      return null
  }
}
