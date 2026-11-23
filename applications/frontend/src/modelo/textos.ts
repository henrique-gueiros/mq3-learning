import { formatarNumero } from '../dominio/formato'
import type { ResultadoModelo } from './tipos'

export interface TextoClassificacao {
  titulo: string
  detalhe: string
  classe: 'sob_efeito' | 'sem_efeito' | 'atencao'
}

/** Frase da classe que o modelo devolveu. Sem modelo e sem janela ficam em atenção. */
export function textoDaClassificacao(resultado: Pick<ResultadoModelo, 'status' | 'prediction' | 'detalhe'>): TextoClassificacao {
  if (resultado.status === 'classificado' && resultado.prediction === 'sob_efeito') {
    return {
      titulo: 'Sob efeito.',
      detalhe: 'O modelo classificou este sopro como bebida nas condições do experimento.',
      classe: 'sob_efeito',
    }
  }
  if (resultado.status === 'classificado' && resultado.prediction === 'sem_efeito') {
    return {
      titulo: 'Sem efeito.',
      detalhe: 'O modelo classificou este sopro junto de ar limpo, perfume, álcool em gel e enxaguante.',
      classe: 'sem_efeito',
    }
  }
  if (resultado.status === 'sem_modelo') {
    return {
      titulo: 'Sem modelo.',
      detalhe: resultado.detalhe || 'Ainda não há um arquivo de modelo para classificar este sopro.',
      classe: 'atencao',
    }
  }
  return {
    titulo: 'Sem classificação.',
    detalhe: resultado.detalhe || 'O modelo não devolveu uma classe para este sopro.',
    classe: 'atencao',
  }
}

/** Probabilidade em porcentagem, no formato da tela. Vazio vira traço. */
export function formatarProbabilidade(valor: number | null | undefined): string {
  if (valor == null || Number.isNaN(valor)) return '—'
  return `${formatarNumero(valor * 100, 1)}%`
}
