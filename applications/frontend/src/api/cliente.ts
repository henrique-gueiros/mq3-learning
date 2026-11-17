/** Filtros que a API entende (query string). Nenhum caso = todos. */
export interface FiltrosApi {
  casos: string[]
  janela: 'arquivo' | 'sopro'
  simulador: boolean
}

/** Monta `?caso=a&caso=b&janela=..&simulador=true`; sem filtros devolve texto vazio. */
export function montarQuery(filtros?: FiltrosApi): string {
  if (!filtros) return ''
  const p = new URLSearchParams()
  filtros.casos.forEach((c) => p.append('caso', c))
  p.set('janela', filtros.janela)
  if (filtros.simulador) p.set('simulador', 'true')
  const texto = p.toString()
  return texto ? `?${texto}` : ''
}

/** GET em `/api<rota>`; erro da API vira exceção com a mensagem dela (`detail`). */
export async function buscar<T>(rota: string, filtros?: FiltrosApi): Promise<T> {
  const resposta = await fetch(`/api${rota}${montarQuery(filtros)}`)
  if (!resposta.ok) {
    let mensagem = `Erro ${resposta.status} ao consultar a API.`
    try {
      const corpo = await resposta.json()
      if (typeof corpo?.detail === 'string') mensagem = corpo.detail
    } catch {
      // corpo sem JSON: fica a mensagem com o status
    }
    throw new Error(mensagem)
  }
  return (await resposta.json()) as T
}
