import { describe, expect, it } from 'vitest'
import { comAlfa, eixoCategoria, eixoValor, gradesEmpilhadas, rotuloSegundos } from './comum'
import { CORES_TESTE as cores } from './testes/cores'

type ComFormatador = { axisLabel: { formatter: (v: number) => string } }

describe('comum', () => {
  it('números do eixo no formato brasileiro', () => {
    const formatar = (eixoValor(cores) as unknown as ComFormatador).axisLabel.formatter
    expect(formatar(3000)).toBe('3.000')
    expect(formatar(0.25)).toBe('0,25')
  })

  it('eixo de categorias mostra todos os rótulos (o ECharts esconde alguns em tela estreita)', () => {
    expect((eixoCategoria(cores, ['MQ-3', 'MQ-135']).axisLabel as { interval: number }).interval).toBe(0)
  })

  it('cor com transparência', () => {
    expect(comAlfa('#ff8000', 0.5)).toBe('rgba(255, 128, 0, 0.5)')
  })

  it('segundos como m:ss', () => {
    expect(rotuloSegundos(90)).toBe('1:30')
    expect(rotuloSegundos(5)).toBe('0:05')
  })

  it('grades empilhadas: um eixo y em formato brasileiro e só a última mostra o tempo', () => {
    const g = gradesEmpilhadas(cores, ['A', 'B', 'C'])
    expect(g.grid).toHaveLength(3)
    expect(g.xAxis.map((x) => (x.axisLabel as { show: boolean }).show)).toEqual([false, false, true])
    expect((g.yAxis[0] as unknown as ComFormatador).axisLabel.formatter(1200)).toBe('1.200')
  })
})
