import type { RodadaOpcao } from '../api/consultas'
import { nomeDoCaso } from '../dominio/casos'
import { formatarDataHora } from '../dominio/formato'

/** Rodadas do seletor: as do simulador só com o interruptor "incluir simulador" ligado. */
export function rodadasVisiveis(rodadas: RodadaOpcao[], simulador: boolean): RodadaOpcao[] {
  return simulador ? rodadas : rodadas.filter((r) => r.origem !== 'simulador')
}

/** `bebida · p01 · 06/11/2026 14:00`, no fuso do navegador; as do simulador vêm marcadas. */
export function rotuloRodada(r: RodadaOpcao): string {
  const partes = [nomeDoCaso(r.caso), r.participante, formatarDataHora(r.inicio), r.arquivo ?? '']
  if (r.origem === 'simulador') partes.push('simulador')
  return partes.filter(Boolean).join(' · ')
}

/** A rodada escolhida, se ainda está na lista; senão a mais recente (a primeira). */
export function escolherRodada(escolhida: string | null, visiveis: RodadaOpcao[]): string | null {
  if (escolhida && visiveis.some((r) => r.id === escolhida)) return escolhida
  return visiveis[0]?.id ?? null
}
