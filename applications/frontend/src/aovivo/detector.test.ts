import { describe, expect, it } from 'vitest'
import { detectar, LIMIARES, type Amostra } from './detector'

// Séries montadas à mão, uma leitura por segundo; não representam o sensor real.
const serie = (n: number, f: (i: number) => Partial<Amostra>, inicio = 0): Amostra[] =>
  Array.from({ length: n }, (_, i) => ({ t_ms: (inicio + i) * 1000, umid: 45, mq135: 250, mq3: 650, ppm: 0.4, ...f(i) }))

const ruido = (i: number) => ((i * 7919) % 5) - 2 // -2..2, repetível

const estados = (amostras: Amostra[]) => detectar(amostras).map((d) => d.estado)

describe('detector de sopro', () => {
  it('ambiente estável vira "ambiente" depois de calibrar e nunca dispara', () => {
    const r = detectar(serie(120, (i) => ({ mq135: 250 + ruido(i), umid: 45 + ruido(i) / 10 })))
    expect(r[0].estado).toBe('calibrando')
    expect(r.at(-1)!.estado).toBe('ambiente')
    expect(r.some((d) => d.estado === 'sopro')).toBe(false)
    expect(r.at(-1)!.base).toMatchObject({ umid: expect.closeTo(45, 0), mq135: expect.closeTo(250, -1) })
  })

  it('deriva lenta do carro não dispara', () => {
    const r = estados(serie(300, (i) => ({ mq135: 250 + i, umid: 45 + i * 0.02, mq3: 650 + i * 2 })))
    expect(r).not.toContain('sopro')
  })

  it('só gás subindo, sem umidade (perfume, álcool no ar), não é sopro', () => {
    const amostras = [...serie(30, () => ({})), ...serie(40, () => ({ mq135: 1100, mq3: 2400 }), 30)]
    expect(estados(amostras)).not.toContain('sopro')
  })

  it('umidade e gás subindo juntos é sopro em poucos segundos', () => {
    const amostras = [...serie(30, () => ({})), ...serie(10, () => ({ umid: 72, mq135: 560, mq3: 1500 }), 30)]
    const r = estados(amostras)
    const primeiro = r.indexOf('sopro')
    expect(primeiro).toBeGreaterThanOrEqual(30)
    expect(primeiro).toBeLessThanOrEqual(33)
  })

  it('umidade sobe e o gás vem um pouco depois: ainda é sopro', () => {
    const amostras = [
      ...serie(30, () => ({})),
      ...serie(3, () => ({ umid: 70 }), 30),
      ...serie(5, () => ({ umid: 74, mq135: 520 }), 33),
    ]
    expect(estados(amostras)).toContain('sopro')
  })

  it('depois do sopro passa por "recuperando" e volta a "ambiente"', () => {
    const amostras = [
      ...serie(30, () => ({})),
      ...serie(10, () => ({ umid: 72, mq135: 560, mq3: 1500 }), 30),
      ...serie(15, (i) => ({ umid: 60 - i, mq135: 400 - i * 10, mq3: 900 }), 40),
      ...serie(30, () => ({}), 55),
    ]
    const r = estados(amostras)
    const sopro = r.indexOf('sopro')
    const recuperando = r.indexOf('recuperando')
    expect(recuperando).toBeGreaterThan(sopro)
    expect(r.at(-1)).toBe('ambiente')
  })

  it('a base não aprende o sopro', () => {
    const amostras = [...serie(30, () => ({})), ...serie(60, () => ({ umid: 72, mq135: 560, mq3: 1500 }), 30)]
    const r = detectar(amostras)
    expect(r.at(-1)!.estado).toBe('sopro')
    expect(r.at(-1)!.base!.umid).toBeCloseTo(45)
  })

  it('sessão que já começa no meio de um sopro usa a referência do ambiente', () => {
    const r = detectar(serie(8, () => ({ umid: 76, mq135: 640, mq3: 2000 })))
    expect(r.at(-1)!.estado).toBe('sopro')
    expect(r.at(-1)!.baseProvisoria).toBe(true)
  })

  it('sessão que começa com perfume no ar e ar úmido (58%) não é sopro', () => {
    expect(estados(serie(60, () => ({ umid: 58, mq135: 1200, mq3: 2400 })))).not.toContain('sopro')
  })

  it('se o sensor não volta à base, recalibra depois do tempo máximo de recuperação', () => {
    const passo = LIMIARES.recuperacaoMaxMs / 1000
    const amostras = [
      ...serie(30, () => ({})),
      ...serie(10, () => ({ umid: 72, mq135: 560, mq3: 1500 }), 30),
      ...serie(passo + 40, () => ({ umid: 50, mq135: 330, mq3: 900 }), 40),
    ]
    const r = detectar(amostras)
    expect(r.map((d) => d.estado)).toContain('calibrando')
    expect(r.at(-1)!.estado).toBe('ambiente')
    expect(r.at(-1)!.base!.mq135).toBeCloseTo(330)
  })

  it('carro úmido desde o começo: sai do "sopro" provisório, recalibra e não volta a disparar', () => {
    const r = detectar(serie(400, () => ({ umid: 70, mq135: 550, mq3: 1300 })))
    const est = r.map((d) => d.estado)
    expect(est[5]).toBe('sopro')
    expect(est.at(-1)).toBe('ambiente')
    expect(est.slice(est.indexOf('calibrando', 5))).not.toContain('sopro')
  })

  it('uma leitura isolada abaixo do limiar não interrompe o sopro', () => {
    const amostras = [
      ...serie(30, () => ({})),
      ...serie(20, (i) => (i % 7 === 6 ? { umid: 47, mq135: 260, mq3: 660 } : { umid: 72, mq135: 560, mq3: 1500 }), 30),
    ]
    // a janela de 5 s ainda vê a subida; a troca exige leituras seguidas
    const r = estados(amostras).slice(31)
    expect(r.every((e) => e === 'sopro')).toBe(true)
  })

  it('o ppm do firmware não decide nada', () => {
    const amostras = [...serie(30, () => ({})), ...serie(10, () => ({ umid: 72, ppm: 5 }), 30)]
    expect(estados(amostras)).not.toContain('sopro')
  })

  it('umidade vazia (DHT11 no começo) não quebra nem dispara', () => {
    const r = estados(serie(40, (i) => ({ umid: null, mq135: i > 20 ? 700 : 250 })))
    expect(r).not.toContain('sopro')
  })

  it('guarda há quanto tempo está no estado atual', () => {
    const r = detectar([...serie(30, () => ({})), ...serie(10, () => ({ umid: 72, mq135: 560, mq3: 1500 }), 30)])
    const ultimo = r.at(-1)!
    expect(ultimo.estado).toBe('sopro')
    expect(ultimo.desdeMs).toBeGreaterThanOrEqual(30000)
    expect(ultimo.desdeMs).toBeLessThanOrEqual(33000)
  })
})
