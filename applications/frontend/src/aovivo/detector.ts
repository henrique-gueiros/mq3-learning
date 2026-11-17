/**
 * Detector ambiente × sopro, para a tela ao vivo. É uma heurística, não o modelo:
 * não diz se a pessoa bebeu, só se parece haver alguém soprando no sensor.
 *
 * Ideia: o ar expirado sobe a umidade; álcool ou outros vapores sobem o gás
 * (MQ-135 ou MQ-3 cru). Sopro é os dois subirem juntos em relação à linha de base do
 * ambiente. Perfume ou álcool no ar sobem o gás sem subir a umidade, então não
 * contam. A base é a mediana dos últimos 60 s de ambiente e não aprende o sopro,
 * para o carro poder mudar devagar (deriva) sem disparar.
 *
 * O `ppm` do firmware não entra na decisão (AGENTS.md: é a regra do firmware);
 * a base guarda o ppm só para a tela mostrar a variação.
 *
 * Os limiares são HIPÓTESE: vêm da comparação entre as rodadas de ambiente e as
 * de bebida coletadas até 17/11 e devem ser revistos na análise exploratória.
 */

export interface Amostra {
  t_ms: number
  umid: number | null
  mq135: number | null
  mq3: number | null
  /** Só para exibir; não entra na decisão. */
  ppm: number | null
}

export interface Base {
  umid: number | null
  mq135: number | null
  mq3: number | null
  ppm: number | null
}

export type EstadoSopro = 'calibrando' | 'ambiente' | 'sopro' | 'recuperando'

export interface Limiares {
  /** Subida mínima sobre a base para contar como sopro. */
  subida: { umid: number; mq135: number; mq3: number }
  /** Distância máxima da base para contar como de volta ao ambiente. */
  tolerancia: { umid: number; mq135: number; mq3: number }
  /** Base usada enquanto calibra (sessão que começa no meio de um sopro). */
  referencia: Base
  /** Janela em que umidade e gás precisam ter subido. */
  janelaSubidaMs: number
  /** Janela da mediana do ambiente. */
  janelaBaseMs: number
  /** Leituras de ambiente para a base ficar pronta. */
  minAmostrasBase: number
  /** Leituras seguidas para confirmar uma troca de estado. */
  confirmar: number
  /** Se o sensor não volta à base nesse tempo, recalibra. */
  recuperacaoMaxMs: number
  /** Sopro mais longo que isso é ar do ambiente que mudou: recalibra. */
  soproMaxMs: number
}

export const LIMIARES: Limiares = {
  subida: { umid: 8, mq135: 120, mq3: 300 },
  tolerancia: { umid: 3, mq135: 60, mq3: 150 },
  referencia: { umid: 55, mq135: 400, mq3: 900, ppm: 0.45 },
  janelaSubidaMs: 5000,
  janelaBaseMs: 60000,
  minAmostrasBase: 10,
  confirmar: 2,
  recuperacaoMaxMs: 120000,
  soproMaxMs: 300000,
}

export interface Detector {
  estado: EstadoSopro
  /** t_ms em que entrou no estado atual. */
  desdeMs: number
  base: Base | null
  /** true quando a base é a referência fixa, não a medida. */
  baseProvisoria: boolean
  /**
   * A referência fixa só vale na primeira calibração da sessão (sessão que já
   * começa num sopro). Depois de recalibrar, o ar atual é o ambiente, mesmo úmido.
   */
  usarReferencia: boolean
  ambiente: Amostra[]
  recentes: Amostra[]
  /** Leituras seguidas a favor da próxima troca de estado. */
  confirmacoes: number
  /** Em "recuperando": leituras seguidas com sopro de novo. */
  retornos: number
}

/** Detector no começo de uma sessão: calibrando, sem base. */
export function novoDetector(): Detector {
  return {
    estado: 'calibrando', desdeMs: 0, base: null, baseProvisoria: false, usarReferencia: true,
    ambiente: [], recentes: [], confirmacoes: 0, retornos: 0,
  }
}

function mediana(valores: (number | null)[]): number | null {
  const v = valores.filter((x): x is number => x !== null).sort((a, b) => a - b)
  if (v.length === 0) return null
  const meio = Math.floor(v.length / 2)
  return v.length % 2 ? v[meio] : (v[meio - 1] + v[meio]) / 2
}

function maximo(valores: (number | null)[]): number | null {
  const v = valores.filter((x): x is number => x !== null)
  return v.length ? Math.max(...v) : null
}

function baseDe(amostras: Amostra[]): Base {
  return {
    umid: mediana(amostras.map((a) => a.umid)),
    mq135: mediana(amostras.map((a) => a.mq135)),
    mq3: mediana(amostras.map((a) => a.mq3)),
    ppm: mediana(amostras.map((a) => a.ppm)),
  }
}

const acima = (valor: number | null, base: number | null, limite: number) =>
  valor !== null && base !== null && valor - base >= limite

/** Umidade e gás (MQ-135 ou MQ-3) subiram em algum ponto da janela recente. */
export function subiu(recentes: Amostra[], base: Base, l: Limiares): boolean {
  const umid = acima(maximo(recentes.map((a) => a.umid)), base.umid, l.subida.umid)
  const mq135 = acima(maximo(recentes.map((a) => a.mq135)), base.mq135, l.subida.mq135)
  const mq3 = acima(maximo(recentes.map((a) => a.mq3)), base.mq3, l.subida.mq3)
  return umid && (mq135 || mq3)
}

const perto = (valor: number | null, base: number | null, tolerancia: number) =>
  valor === null || base === null || valor - base <= tolerancia

function voltou(a: Amostra, base: Base, l: Limiares): boolean {
  return (
    perto(a.umid, base.umid, l.tolerancia.umid) &&
    perto(a.mq135, base.mq135, l.tolerancia.mq135) &&
    perto(a.mq3, base.mq3, l.tolerancia.mq3)
  )
}

const trocar = (d: Detector, estado: EstadoSopro, t_ms: number, extra: Partial<Detector> = {}): Detector => ({
  ...d,
  ...extra,
  estado,
  desdeMs: t_ms,
  confirmacoes: 0,
  retornos: 0,
})

const recalibrar = (d: Detector, t_ms: number): Detector =>
  trocar(d, 'calibrando', t_ms, { ambiente: [], base: null, baseProvisoria: false, usarReferencia: false })

/** Avança o detector com uma leitura nova. Não altera o detector recebido. */
export function passo(anterior: Detector, a: Amostra, l: Limiares = LIMIARES): Detector {
  const recentes = [...anterior.recentes, a].filter((r) => r.t_ms > a.t_ms - l.janelaSubidaMs)
  const d: Detector = { ...anterior, recentes, desdeMs: anterior.recentes.length ? anterior.desdeMs : a.t_ms }

  switch (d.estado) {
    case 'calibrando': {
      if (d.usarReferencia && subiu(recentes, l.referencia, l)) {
        const confirmacoes = d.confirmacoes + 1
        return confirmacoes >= l.confirmar
          ? trocar(d, 'sopro', a.t_ms, { base: l.referencia, baseProvisoria: true })
          : { ...d, confirmacoes }
      }
      const ambiente = [...d.ambiente, a]
      if (ambiente.length >= l.minAmostrasBase) {
        return trocar(d, 'ambiente', a.t_ms, { ambiente, base: baseDe(ambiente), baseProvisoria: false })
      }
      return { ...d, ambiente, confirmacoes: 0 }
    }

    case 'ambiente': {
      const base = d.base ?? l.referencia
      if (subiu(recentes, base, l)) {
        const confirmacoes = d.confirmacoes + 1
        return confirmacoes >= l.confirmar ? trocar(d, 'sopro', a.t_ms) : { ...d, confirmacoes }
      }
      const ambiente = [...d.ambiente, a].filter((r) => r.t_ms > a.t_ms - l.janelaBaseMs)
      return { ...d, ambiente, base: baseDe(ambiente), confirmacoes: 0 }
    }

    case 'sopro': {
      const base = d.base ?? l.referencia
      const duracao = a.t_ms - d.desdeMs
      // base provisória errada (carro úmido) ou ar que mudou de vez: o sopro não acaba sozinho
      if ((d.baseProvisoria && duracao >= l.recuperacaoMaxMs) || duracao >= l.soproMaxMs) {
        return recalibrar(d, a.t_ms)
      }
      if (subiu(recentes, base, l)) return { ...d, confirmacoes: 0 }
      const confirmacoes = d.confirmacoes + 1
      return confirmacoes >= l.confirmar ? trocar(d, 'recuperando', a.t_ms) : { ...d, confirmacoes }
    }

    case 'recuperando': {
      const base = d.base ?? l.referencia
      if (subiu(recentes, base, l)) {
        const retornos = d.retornos + 1
        return retornos >= l.confirmar ? trocar(d, 'sopro', a.t_ms) : { ...d, retornos, confirmacoes: 0 }
      }
      if (voltou(a, base, l)) {
        const confirmacoes = d.confirmacoes + 1
        if (confirmacoes < l.confirmar) return { ...d, confirmacoes, retornos: 0 }
        // com base provisória, o ambiente de verdade só agora pode ser medido
        return d.baseProvisoria ? recalibrar(d, a.t_ms) : trocar(d, 'ambiente', a.t_ms)
      }
      if (a.t_ms - d.desdeMs >= l.recuperacaoMaxMs) {
        return recalibrar(d, a.t_ms)
      }
      return { ...d, confirmacoes: 0, retornos: 0 }
    }
  }
}

/** Roda o detector sobre uma série inteira; devolve o detector depois de cada leitura. */
export function detectar(amostras: Amostra[], l: Limiares = LIMIARES): Detector[] {
  const saida: Detector[] = []
  let d = novoDetector()
  for (const a of amostras) {
    d = passo(d, a, l)
    saida.push(d)
  }
  return saida
}
