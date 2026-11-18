import { expect, test, type Page } from '@playwright/test'
import { BrokerFalso } from './brokerFalso'

// Respostas da API montadas à mão (não são dados do sensor): só conferem que as
// quatro seções da análise pedem, recebem e desenham, e que os filtros vão para a URL.

const p = (base: number) => ({ p5: base, p25: base + 50, p50: base + 100, p75: base + 150, p95: base + 200, media: base + 110 })
const inicio = '2026-11-12T23:05:00Z'

const RESPOSTAS: Record<string, unknown> = {
  '/api/filtros': {
    casos: ['clean', 'drink'],
    participantes: ['e2e'],
    rodadas: [
      { id: 'r-drink', caso: 'drink', participante: 'e2e', origem: 'ponte', inicio },
      { id: 'r-clean', caso: 'clean', participante: 'e2e', origem: 'ponte', inicio: '2026-11-12T22:00:00Z' },
    ],
  },
  '/api/resumo': { placa: 'parada', rodadas: 2, leituras: 120 },
  '/api/distribuicao': [
    { caso: 'clean', n: 60, mq3: p(700), mq135: p(250), umid: p(45) },
    { caso: 'drink', n: 60, mq3: p(1500), mq135: p(600), umid: p(75) },
  ],
  '/api/heatmap': [{ caso: 'drink', mq3: 110, mq135: 140, umid: 66 }],
  '/api/dispersao': [
    { caso: 'clean', mq3_raw: 700, mq135_raw: 250 },
    { caso: 'drink', mq3_raw: 1500, mq135_raw: 600 },
  ],
  '/api/sobrepostas': [
    { rodada: 'r-drink', caso: 'drink', pontos: [[0, 50, 300, 0.4], [10, 80, 600, 1.2]] },
    { rodada: 'r-clean', caso: 'clean', pontos: [[0, 45, 250, 0.3], [10, 46, 260, 0.3]] },
  ],
  '/api/rodadas/r-drink/leituras': {
    rodada: 'r-drink',
    caso: 'drink',
    pontos: [
      { tempo_s: 0, t_ms: 0, mq3_raw: 700, mq135_raw: 250, humidity_pct: 50, ppm: 0.4, em_sopro: false },
      { tempo_s: 5, t_ms: 5000, mq3_raw: 1500, mq135_raw: 600, humidity_pct: 80, ppm: 1.2, em_sopro: true },
    ],
  },
  '/api/sopros': [{ caso: 'drink', subida_mq3: 800, subida_mq135: 350 }],
  '/api/rodadas-sem-sopro': [
    { rodada_id: 'r-clean', caso: 'clean', participante: 'e2e', arquivo: '2026-11-12_e2e_clean_1.csv', inicio },
  ],
}

/** Responde `/api/*` com `RESPOSTAS` e guarda as URLs pedidas. */
async function apiFalsa(page: Page): Promise<string[]> {
  const pedidas: string[] = []
  // só o caminho que começa com /api/: no Vite, os módulos de src/api/ também têm "/api/" na URL
  await page.route((url) => url.pathname.startsWith('/api/'), (rota) => {
    const url = new URL(rota.request().url())
    pedidas.push(url.pathname + url.search)
    const corpo = RESPOSTAS[url.pathname]
    return corpo === undefined
      ? rota.fulfill({ status: 404, json: { detail: 'sem resposta no e2e' } })
      : rota.fulfill({ json: corpo })
  })
  return pedidas
}

test('as quatro seções da análise desenham com a resposta da API', async ({ page }) => {
  await new BrokerFalso().instalar(page)
  await apiFalsa(page)
  await page.goto('/')

  for (const [secao, grafico] of [
    ['Comparação entre os casos.', 'Boxplot da distribuição'],
    ['Todas as rodadas juntas.', '2 rodadas sobrepostas'],
    ['Rodada selecionada.', 'Leituras de MQ-3, MQ-135 e umidade da rodada bebida · e2e'],
    ['Sopros marcados.', 'Dispersão da subida por sopro'],
  ]) {
    const regiao = page.getByRole('region', { name: secao })
    await regiao.scrollIntoViewIfNeeded()
    const figura = regiao.getByRole('img', { name: grafico }).first()
    await expect(figura).toBeVisible()
    await expect(figura.locator('canvas').first()).toBeVisible()
  }

  await expect(page.getByRole('combobox', { name: 'Rodada' })).toHaveValue('r-drink')
  const tabela = page.getByRole('table', { name: 'Rodadas sem sopro marcado' })
  await expect(tabela.getByText('2026-11-12_e2e_clean_1.csv')).toBeVisible()
})

test('filtros vão para a URL e para a API', async ({ page }) => {
  await new BrokerFalso().instalar(page)
  const pedidas = await apiFalsa(page)
  await page.goto('/')
  await expect(page.getByRole('region', { name: 'Comparação entre os casos.' }).getByRole('img').first()).toBeVisible()

  await page.getByRole('button', { name: 'bebida' }).click()
  await expect(page).toHaveURL(/caso=/)
  await expect.poll(() => pedidas.some((u) => u.startsWith('/api/distribuicao') && u.includes('caso='))).toBe(true)

  await page.getByRole('radio', { name: 'Só o sopro' }).click()
  await expect(page).toHaveURL(/janela=sopro/)
  await expect.poll(() => pedidas.some((u) => u.startsWith('/api/distribuicao') && u.includes('janela=sopro'))).toBe(true)

  await page.getByRole('combobox', { name: 'Rodada' }).selectOption('r-clean')
  await expect(page).toHaveURL(/rodada=r-clean/)
})
