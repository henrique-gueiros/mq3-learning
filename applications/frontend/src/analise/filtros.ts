import { useCallback, useEffect, useState } from 'react'
import type { FiltrosApi } from '../api/cliente'

/** Filtros da tela de análise. Vivem na URL (`?caso=..&janela=..&simulador=1&rodada=..`). */
export interface Filtros extends FiltrosApi {
  /** Rodada escolhida na seção "Rodada selecionada"; `null` = a mais recente. */
  rodada: string | null
}

export const FILTROS_PADRAO: Filtros = { casos: [], janela: 'arquivo', simulador: false, rodada: null }

/** Lê os filtros de `location.search`; valor inválido cai no padrão. */
export function lerFiltros(search: string): Filtros {
  const p = new URLSearchParams(search)
  const casos = [...new Set(p.getAll('caso').filter(Boolean))]
  return {
    casos,
    janela: p.get('janela') === 'sopro' ? 'sopro' : 'arquivo',
    simulador: p.get('simulador') === '1' || p.get('simulador') === 'true',
    rodada: p.get('rodada') || null,
  }
}

/** Texto para `location.search`; só o que difere do padrão (padrão = URL limpa). */
export function escreverFiltros(f: Filtros): string {
  const p = new URLSearchParams()
  f.casos.forEach((c) => p.append('caso', c))
  if (f.janela !== FILTROS_PADRAO.janela) p.set('janela', f.janela)
  if (f.simulador) p.set('simulador', '1')
  if (f.rodada) p.set('rodada', f.rodada)
  const texto = p.toString()
  return texto ? `?${texto}` : ''
}

/** Filtros guardados na URL (`history.replaceState`, sem empilhar histórico). */
export function useFiltrosDaUrl(): [Filtros, (mudanca: Partial<Filtros>) => void] {
  const [filtros, setFiltros] = useState<Filtros>(() => lerFiltros(window.location.search))
  useEffect(() => {
    window.history.replaceState(null, '', `${window.location.pathname}${escreverFiltros(filtros)}${window.location.hash}`)
  }, [filtros])
  const mudar = useCallback((mudanca: Partial<Filtros>) => setFiltros((atual) => ({ ...atual, ...mudanca })), [])
  return [filtros, mudar]
}
