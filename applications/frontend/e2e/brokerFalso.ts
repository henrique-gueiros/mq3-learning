import type { Page, WebSocketRoute } from '@playwright/test'
import mqttPacket from 'mqtt-packet'

/**
 * Broker MQTT falso dentro do Playwright: intercepta o WebSocket /mqtt da página e
 * responde ao protocolo (CONNECT → CONNACK, SUBSCRIBE → SUBACK). Assim o teste não
 * depende do Mosquitto e não grava nada no banco da coleta.
 */
export class BrokerFalso {
  private conexoes: WebSocketRoute[] = []
  private prontas: Promise<void>
  private avisarPronta!: () => void

  constructor() {
    this.prontas = new Promise((resolver) => (this.avisarPronta = resolver))
  }

  async instalar(page: Page) {
    await page.routeWebSocket(/\/mqtt$/, (ws) => {
      this.conexoes.push(ws)
      const leitor = mqttPacket.parser({ protocolVersion: 4 })
      leitor.on('packet', (pacote) => {
        if (pacote.cmd === 'connect') this.enviar(ws, { cmd: 'connack', returnCode: 0, sessionPresent: false })
        if (pacote.cmd === 'subscribe') {
          this.enviar(ws, { cmd: 'suback', messageId: pacote.messageId, granted: pacote.subscriptions.map(() => 1) })
          this.avisarPronta()
        }
        if (pacote.cmd === 'pingreq') this.enviar(ws, { cmd: 'pingresp' })
      })
      ws.onMessage((dados) => leitor.parse(Buffer.isBuffer(dados) ? dados : Buffer.from(dados)))
    })
  }

  /** Espera a página assinar os tópicos. */
  assinou() {
    return this.prontas
  }

  publicar(topico: string, corpo: object) {
    const pacote = { cmd: 'publish' as const, topic: topico, payload: JSON.stringify(corpo), qos: 0 as const, dup: false, retain: false }
    for (const ws of this.conexoes) this.enviar(ws, pacote)
  }

  private enviar(ws: WebSocketRoute, pacote: mqttPacket.Packet) {
    ws.send(mqttPacket.generate(pacote))
  }
}
