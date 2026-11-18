/**
 * Peças repetidas nos gráficos de análise: eixos, dica (tooltip), legenda e título de
 * grade no estilo do design system. Funções puras, sem tocar no DOM.
 */

import type { CoresGrafico } from './aoVivo'

export type Marca = Record<string, unknown>

/** Dados e contexto que toda função de opções da análise recebe. */
export interface EntradaGrafico<T> {
  dados: T
  cores: CoresGrafico
  tema: 'escuro' | 'claro'
  animar?: boolean
}

/** `#rrggbb` com transparência, para preenchimentos na cor do caso. */
export function comAlfa(hex: string, alfa: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alfa})`
}

const rotuloEixo = (cores: CoresGrafico) => ({
  color: cores.mudo,
  fontFamily: cores.fonteMono,
  fontSize: 11,
  formatter: (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 2 }),
})

/** Eixo numérico: sem linha nem marcas, grade em hairline, números em Geist Mono. */
export function eixoValor<E extends Marca>(cores: CoresGrafico, extra: E = {} as E): Marca & E & { type: 'value' } {
  return {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: rotuloEixo(cores),
    splitLine: { lineStyle: { color: cores.linha } },
    nameTextStyle: { color: cores.corpo, fontFamily: cores.fonte, fontSize: 12 },
    ...extra,
    type: 'value',
  }
}

/** Eixo de categorias (casos, sensores): todos os rótulos, mesmo em tela estreita. */
export function eixoCategoria(cores: CoresGrafico, data: string[], extra: Marca = {}): Marca & { type: 'category'; data: string[] } {
  return {
    axisLine: { lineStyle: { color: cores.linha } },
    axisTick: { show: false },
    axisLabel: { color: cores.corpo, fontFamily: cores.fonte, fontSize: 12, interval: 0 },
    ...extra,
    type: 'category',
    data,
  }
}

/** Aparência da dica (tooltip), igual à do gráfico ao vivo. */
export function dica(cores: CoresGrafico, extra: Marca = {}): Marca {
  return {
    backgroundColor: cores.cartao,
    borderColor: cores.linha,
    textStyle: { color: cores.tinta, fontSize: 12, fontFamily: cores.fonte },
    ...extra,
  }
}

/** Legenda por caso, no topo. */
export function legenda<E extends Marca>(cores: CoresGrafico, extra: E = {} as E): Marca & E {
  return {
    top: 0,
    left: 0,
    icon: 'circle',
    itemWidth: 9,
    itemHeight: 9,
    itemGap: 16,
    textStyle: { color: cores.corpo, fontFamily: cores.fonte, fontSize: 12 },
    ...extra,
  }
}

/** Título pequeno de uma grade (cada sensor num gráfico). */
export function tituloGrade(cores: CoresGrafico, texto: string, posicao: Marca): Marca {
  return { text: texto, ...posicao, textStyle: { color: cores.corpo, fontFamily: cores.fonte, fontSize: 12, fontWeight: 500 } }
}

/** Segundos como texto curto do eixo: `90` → `1:30`. */
export function rotuloSegundos(s: number): string {
  const total = Math.max(0, Math.round(s))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/**
 * Grades empilhadas com o mesmo eixo de tempo (uma medida por grade, cada uma com o
 * seu eixo y). Só a última mostra os rótulos do tempo. `topo` e `fundo` são em %.
 */
export function gradesEmpilhadas(
  cores: CoresGrafico,
  rotulos: string[],
  { topo = 6, fundo = 10 }: { topo?: number; fundo?: number } = {},
): { title: Marca[]; grid: Marca[]; xAxis: Marca[]; yAxis: Marca[] } {
  const passo = (100 - topo - fundo) / rotulos.length
  const ultima = rotulos.length - 1
  return {
    title: rotulos.map((r, i) => tituloGrade(cores, r, { left: 0, top: `${topo + i * passo}%` })),
    grid: rotulos.map((_, i) => ({ left: 0, right: 16, top: `${topo + i * passo + 4}%`, height: `${passo - 8}%`, containLabel: true })),
    xAxis: rotulos.map((_, i) => ({
      type: 'value',
      gridIndex: i,
      min: 0,
      axisLine: { lineStyle: { color: cores.linha } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: i === ultima, hideOverlap: true, color: cores.mudo, fontFamily: cores.fonteMono, fontSize: 11, formatter: rotuloSegundos },
    })),
    yAxis: rotulos.map((_, i) => eixoValor(cores, { gridIndex: i, scale: true, splitNumber: 3 })),
  }
}

/** Animação curta ao trocar filtro; desligada com `prefers-reduced-motion`. */
export function animacao(animar: boolean): Marca {
  return {
    animation: animar,
    animationDuration: animar ? 300 : 0,
    animationDurationUpdate: animar ? 250 : 0,
    animationEasingUpdate: 'cubicOut',
  }
}