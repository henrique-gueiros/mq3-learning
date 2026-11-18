import { useQuery } from '@tanstack/react-query'
import { buscar, type FiltrosApi } from './cliente'

/** Tipos espelhando as respostas de `applications/api/app.py`. */

export interface OpcoesFiltros {
  casos: string[]
  participantes: string[]
  rodadas: RodadaOpcao[]
}

export interface RodadaOpcao {
  id: string
  caso: string
  participante: string
  /** `'simulador'`, `'ponte'`, `'importador'`… (vazio se desconhecida). */
  origem: string
  /** ISO 8601, em UTC. */
  inicio: string
}

export interface ResumoApi {
  placa: 'recebendo' | 'parada'
  rodadas: number
  leituras: number
}

export interface Percentis {
  p5: number | null
  p25: number | null
  p50: number | null
  p75: number | null
  p95: number | null
  media: number | null
}

export interface DistribuicaoCaso {
  caso: string
  n: number
  mq3: Percentis
  mq135: Percentis
  umid: Percentis
}

/** Diferença (%) da média do caso em relação ao ambiente (`clean`). */
export interface CelulaHeatmap {
  caso: string
  mq3: number | null
  mq135: number | null
  umid: number | null
}

export interface PontoDispersao {
  caso: string
  mq3_raw: number
  mq135_raw: number
}

/** Pontos `[tempo_s, umidade, mq135, ppm]`. */
export type PontoSobreposto = [number, number | null, number | null, number | null]

export interface SerieSobreposta {
  rodada: string
  caso: string
  pontos: PontoSobreposto[]
}

export interface PontoRodada {
  tempo_s: number
  t_ms: number
  mq3_raw: number | null
  mq135_raw: number | null
  humidity_pct: number | null
  ppm: number | null
  em_sopro: boolean
}

export interface LeiturasRodada {
  rodada: string
  caso: string
  pontos: PontoRodada[]
}

export interface Sopro {
  caso: string
  subida_mq3: number
  subida_mq135: number
}

export interface RodadaSemSopro {
  rodada_id: string
  caso: string
  participante: string
  arquivo: string
  inicio: string | null
}

/** A chave de cache leva só o que a API recebe (a rodada escolhida não refaz as consultas). */
const soApi = ({ casos, janela, simulador }: FiltrosApi): FiltrosApi => ({ casos, janela, simulador })

/** Opções da barra de filtros: casos, participantes e rodadas (a mais nova primeiro). */
export const useFiltros = () => useQuery({ queryKey: ['filtros'], queryFn: () => buscar<OpcoesFiltros>('/filtros') })

export const useResumo = (f: FiltrosApi) =>
  useQuery({ queryKey: ['resumo', soApi(f)], queryFn: () => buscar<ResumoApi>('/resumo', soApi(f)) })

export const useDistribuicao = (f: FiltrosApi) =>
  useQuery({ queryKey: ['distribuicao', soApi(f)], queryFn: () => buscar<DistribuicaoCaso[]>('/distribuicao', soApi(f)) })

export const useHeatmap = (f: FiltrosApi) =>
  useQuery({ queryKey: ['heatmap', soApi(f)], queryFn: () => buscar<CelulaHeatmap[]>('/heatmap', soApi(f)) })

export const useDispersao = (f: FiltrosApi) =>
  useQuery({ queryKey: ['dispersao', soApi(f)], queryFn: () => buscar<PontoDispersao[]>('/dispersao', soApi(f)) })

export const useSobrepostas = (f: FiltrosApi) =>
  useQuery({ queryKey: ['sobrepostas', soApi(f)], queryFn: () => buscar<SerieSobreposta[]>('/sobrepostas', soApi(f)) })

/** Leituras de uma rodada; sem `id` a consulta fica parada. Não depende dos filtros. */
export const useLeiturasRodada = (id: string | null | undefined) =>
  useQuery({
    queryKey: ['rodada', id],
    queryFn: () => buscar<LeiturasRodada>(`/rodadas/${encodeURIComponent(id ?? '')}/leituras`),
    enabled: !!id,
  })

export const useSopros = (f: FiltrosApi) =>
  useQuery({ queryKey: ['sopros', soApi(f)], queryFn: () => buscar<Sopro[]>('/sopros', soApi(f)) })

export const useRodadasSemSopro = () =>
  useQuery({ queryKey: ['rodadas-sem-sopro'], queryFn: () => buscar<RodadaSemSopro[]>('/rodadas-sem-sopro') })
