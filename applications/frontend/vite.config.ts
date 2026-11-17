/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em desenvolvimento, /api vai para a API (Compose, 127.0.0.1:8000) e /mqtt para o
// WebSocket do Mosquitto (127.0.0.1:9001). Em produção, o nginx faz o mesmo papel.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/mqtt': { target: 'ws://127.0.0.1:9001', ws: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/testes/preparar.ts'],
  },
})
