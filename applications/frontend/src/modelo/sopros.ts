/**
 * Três sopros de exemplo para a aba Modelo.
 *
 * Os números vêm dos CSVs da equipe em `esp32-esp8266/` (perfume, bebida e
 * ambiente). Cada recorte cobre os 15 s antes do sopro, o sopro e os 30 s
 * seguintes: a mesma janela de features do treino. Não entra em treino nem em teste.
 */
import bruto from './sopros.json'
import type { IdSopro, LeituraDemo, SoproDemo } from './tipos'

const TEXTOS: Record<IdSopro, { rotulo: string; detalhe: string }> = {
  perfume: {
    rotulo: 'Perfume',
    detalhe: 'Vapor de perfume no sensor, sem bebida.',
  },
  bebida: {
    rotulo: 'Bebida',
    detalhe: 'Sopro de quem bebeu, nas condições do experimento.',
  },
  ambiente: {
    rotulo: 'Sem bebida',
    detalhe: 'Ar do ambiente, sem sopro de bebida.',
  },
}

function montar(item: (typeof bruto)[number]): SoproDemo {
  const id = item.id as IdSopro
  const texto = TEXTOS[id]
  return {
    id,
    caso: item.caso,
    rotulo: texto.rotulo,
    detalhe: texto.detalhe,
    origem: item.origem,
    blow_start_s: item.blow_start_s,
    blow_end_s: item.blow_end_s,
    leituras: item.leituras as LeituraDemo[],
  }
}

/** Os três exemplos, na ordem em que a aba mostra. */
export const SOPROS: SoproDemo[] = bruto.map(montar)

/** Pico de PPM, MQ-135 e umidade no sopro e nos 30 s seguintes. */
export function resumoDoSopro(sopro: SoproDemo): { ppm: number; mq135: number; umidade: number } {
  const desde = sopro.blow_start_s * 1000
  const durante = sopro.leituras.filter((l) => l.t_ms >= desde)
  const base = durante.length > 0 ? durante : sopro.leituras
  return {
    ppm: Math.max(...base.map((l) => l.ppm)),
    mq135: Math.max(...base.map((l) => l.mq135_raw)),
    umidade: Math.max(...base.map((l) => l.humidity_pct)),
  }
}

/** Corpo do POST: o recorte inteiro, com o instante do sopro. */
export function corpoDoSopro(sopro: SoproDemo) {
  return {
    sessao: sopro.origem,
    attempt_id: `demo-${sopro.id}`,
    blow_start_s: sopro.blow_start_s,
    blow_end_s: sopro.blow_end_s,
    leituras: sopro.leituras,
  }
}
