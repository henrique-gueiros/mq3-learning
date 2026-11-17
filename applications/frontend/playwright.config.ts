import { defineConfig, devices } from '@playwright/test'

// Ponta a ponta da tela. O broker MQTT é simulado no teste (e2e/brokerFalso.ts).
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: { baseURL: 'http://localhost:5173', trace: 'off' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://localhost:5173', reuseExistingServer: true },
})
