import mqtt from 'mqtt'
import { useEffect, useReducer, useState } from 'react'
import { estadoInicial, reduzir, type EstadoAoVivo } from './estado'
import { parsearMensagem, TOPICOS, type Mensagem } from './mensagens'

export type Conexao = 'conectando' | 'conectado' | 'sem-broker'

/** WebSocket do broker na mesma origem da página (o Vite ou o nginx encaminham /mqtt). */
export function urlDoBroker(): string {
  const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocolo}://${window.location.host}/mqtt`
}

function redutor(e: EstadoAoVivo, m: Mensagem) {
  return reduzir(e, m, Date.now())
}

/** Assina as leituras ao vivo no broker e reconecta sozinho quando ele cai. */
export function useAoVivo(url: string = urlDoBroker()): { estado: EstadoAoVivo; conexao: Conexao } {
  const [estado, despachar] = useReducer(redutor, undefined, estadoInicial)
  const [conexao, setConexao] = useState<Conexao>('conectando')

  useEffect(() => {
    const cliente = mqtt.connect(url, { reconnectPeriod: 2000, connectTimeout: 5000, clean: true })
    cliente.on('connect', () => {
      setConexao('conectado')
      cliente.subscribe(TOPICOS, { qos: 1 })
    })
    cliente.on('offline', () => setConexao('sem-broker'))
    cliente.on('error', () => setConexao('sem-broker'))
    cliente.on('message', (topico, corpo) => {
      const m = parsearMensagem(topico, corpo.toString())
      if (m) despachar(m)
    })
    return () => {
      cliente.end(true)
    }
  }, [url])

  return { estado, conexao }
}
