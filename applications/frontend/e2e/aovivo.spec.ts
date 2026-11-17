import { expect, test } from '@playwright/test'
import { BrokerFalso } from './brokerFalso'

// Rodada montada à mão (não é dado do sensor): 30 s de ambiente e depois
// umidade e gás subindo juntos, publicada por um broker falso.

const placa = 'placa-e2e'
const rodada_id = 'e2e-0001'

function leitura(amostra: number, umid: number, mq135: number, mq3: number, ppm: number) {
  return {
    rodada_id, amostra, t_ms: amostra * 1000, mq3_raw: mq3, ppm, mq135_raw: mq135, mq135_mv: 0,
    temperature_c: 28, humidity_pct: umid, alcool: 0,
  }
}

test('a tela mostra as leituras chegando e detecta o sopro', async ({ page }) => {
  const broker = new BrokerFalso()
  await broker.instalar(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Aguardando a placa.' })).toBeVisible()
  await broker.assinou()

  broker.publicar(`mq3/${placa}/rodada`, {
    rodada_id, placa, caso: 'drink', participante: 'e2e', inicio: null, arquivo_sessao: 'e2e.csv', origem: 'simulador',
  })
  for (let i = 0; i < 30; i++) broker.publicar(`mq3/${placa}/leituras`, leitura(i, 45, 250, 650, 0.4))
  await expect(page.getByRole('heading', { name: 'Ambiente.' })).toBeVisible()
  await expect(page.getByRole('status').filter({ hasText: 'Recebendo' })).toBeVisible()
  await expect(page.getByRole('definition').filter({ hasText: 'bebida' })).toBeVisible()

  for (let i = 30; i < 36; i++) broker.publicar(`mq3/${placa}/leituras`, leitura(i, 72, 560, 1500, 0.9))
  await expect(page.getByRole('heading', { name: 'Sopro detectado.' })).toBeVisible()
  await expect(page.getByText('+124,0%')).toBeVisible()
  await expect(page.getByText('Sopro detectado', { exact: true })).toBeVisible() // o aviso
  await expect(page.locator('.grafico-aovivo canvas')).toHaveCount(1)
})

test('perfume no ar sem umidade não vira sopro', async ({ page }) => {
  const broker = new BrokerFalso()
  await broker.instalar(page)
  await page.goto('/')
  await broker.assinou()
  for (let i = 0; i < 30; i++) broker.publicar(`mq3/${placa}/leituras`, leitura(i, 45, 250, 650, 0.4))
  for (let i = 30; i < 50; i++) broker.publicar(`mq3/${placa}/leituras`, leitura(i, 45, 1100, 2400, 1.2))
  await expect(page.getByText('1.100')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Ambiente.' })).toBeVisible()
})
