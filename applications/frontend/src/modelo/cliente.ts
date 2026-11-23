import { corpoDoSopro } from './sopros'
import type { ResultadoModelo, SoproDemo } from './tipos'

/** Falha de rede ou resposta de erro do serviço do modelo. */
export class ErroModelo extends Error {}

const FORA_DO_AR = 'O serviço do modelo não está no ar. Suba o container do modelo e tente de novo.'

/**
 * Envia o recorte ao modelo em `POST /modelo/classificar`.
 * O serviço devolve a classe; esta função não interpreta o sopro.
 */
export async function classificarSopro(sopro: SoproDemo): Promise<ResultadoModelo> {
  let resposta: Response
  try {
    resposta = await fetch('/modelo/classificar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpoDoSopro(sopro)),
    })
  } catch {
    throw new ErroModelo(FORA_DO_AR)
  }
  if (!resposta.ok) {
    if (resposta.status === 502 || resposta.status === 503) throw new ErroModelo(FORA_DO_AR)
    let detalhe = `Erro ${resposta.status} ao classificar.`
    try {
      const corpo = await resposta.json()
      if (typeof corpo?.detail === 'string') detalhe = corpo.detail
    } catch {
      // corpo sem JSON: fica a mensagem com o status
    }
    throw new ErroModelo(detalhe)
  }
  return (await resposta.json()) as ResultadoModelo
}
