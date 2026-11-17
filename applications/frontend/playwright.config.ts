import { defineConfig, devices } from '@playwright/test'

// Ponta a ponta da tela. O broker MQTT é simulado no teste (e2e/brokerFalso.ts).
// PLAYWRIGHT_BASE_URL aponta para uma tela já no ar (ex.: o nginx do Compose); sem ela, sobe o Vite.
const urlExterna = process.env.PLAYWRIGHT_BASE_URL

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: { baseURL: urlExterna ?? 'http://localhost:5173', trace: 'off' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: urlExterna ? undefined : { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://localhost:5173', reuseExistingServer: true },
})
