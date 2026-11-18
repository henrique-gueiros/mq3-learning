import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { vi } from 'vitest'
import { TemaProvider } from '../../tema/TemaProvider'

/**
 * `fetch` falso: a resposta é escolhida pelo começo do caminho (`/api/heatmap`…).
 * Valor `Error` vira resposta 503 com a mensagem no `detail`.
 */
export function apiFalsa(rotas: Record<string, unknown>) {
  const fetchFalso = vi.fn(async (url: string) => {
    const caminho = new URL(url, 'http://local').pathname
    const chave = Object.keys(rotas)
      .sort((a, b) => b.length - a.length)
      .find((r) => caminho.startsWith(r))
    const corpo = chave === undefined ? new Error(`rota sem resposta no teste: ${caminho}`) : rotas[chave]
    if (corpo instanceof Error) return { ok: false, status: 503, json: async () => ({ detail: corpo.message }) }
    return { ok: true, status: 200, json: async () => corpo }
  })
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

/** Renderiza com o cache do TanStack Query (sem novas tentativas) e o tema. */
export function montar(ui: ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <TemaProvider>{ui}</TemaProvider>
    </QueryClientProvider>,
  )
}
