import type { Tema } from '../dominio/casos'

export type { Tema }

const CHAVE = 'mq3-tema'

interface Armazenamento {
  getItem(chave: string): string | null
  setItem(chave: string, valor: string): void
}

/** Tema salvo pelo visitante; escuro quando não há nada salvo ou o navegador bloqueia o armazenamento. */
export function lerTema(armazenamento: Armazenamento): Tema {
  try {
    const salvo = armazenamento.getItem(CHAVE)
    return salvo === 'claro' || salvo === 'escuro' ? salvo : 'escuro'
  } catch {
    return 'escuro'
  }
}

/** Guarda a escolha; se o navegador não deixar, a troca vale só nesta visita. */
export function salvarTema(armazenamento: Armazenamento, tema: Tema): void {
  try {
    armazenamento.setItem(CHAVE, tema)
  } catch {
    // modo privado ou armazenamento bloqueado
  }
}
