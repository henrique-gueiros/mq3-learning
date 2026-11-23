/** Identificador dos três exemplos da aba. */
export type IdSopro = 'perfume' | 'bebida' | 'ambiente'

/** Uma linha do CSV da coleta, só com o que o modelo lê e o que a tela mostra. */
export interface LeituraDemo {
  t_ms: number
  mq3_raw: number
  mq135_raw: number
  temperature_c: number
  humidity_pct: number
  ppm: number
}

/** Um sopro de exemplo pronto para enviar ao modelo. */
export interface SoproDemo {
  id: IdSopro
  caso: string
  rotulo: string
  detalhe: string
  origem: string
  blow_start_s: number
  blow_end_s: number
  leituras: LeituraDemo[]
}

/** Resposta de `POST /modelo/classificar`, o mesmo corpo do MQTT de resultado. */
export interface ResultadoModelo {
  sessao: string
  attempt_id: string | null
  status: string
  prediction: string | null
  prob_sem_efeito: number | null
  prob_sob_efeito: number | null
  detalhe: string
}
