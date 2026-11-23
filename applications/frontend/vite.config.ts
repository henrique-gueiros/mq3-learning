/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em desenvolvimento, /api vai para a API (Compose, 127.0.0.1:8000), /modelo/ para o
// classificador (127.0.0.1:8010) e /mqtt para o WebSocket do Mosquitto (127.0.0.1:9001).
// A página /modelo fica no Vite; só o que tem barra depois (/modelo/classificar) sai daqui.
// Em produção, o nginx faz o mesmo papel.
export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: {
      output: {
        // bibliotecas em arquivos próprios: mudam pouco, então o navegador as guarda entre versões da tela.
        // O ECharts fica de fora de propósito: agrupado, levaria para a 1ª carga os gráficos que só a análise usa.
        codeSplitting: {
          groups: [
            { name: 'mqtt', test: /node_modules[\\/]mqtt[^\\/]*[\\/]/ }, // mqtt e mqtt-packet
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
          ],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/modelo/': 'http://127.0.0.1:8010',
      '/mqtt': { target: 'ws://127.0.0.1:9001', ws: true },
    },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    setupFiles: ['./src/testes/preparar.ts'],
  },
})
