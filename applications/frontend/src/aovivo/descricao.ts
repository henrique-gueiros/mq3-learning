/** Frase da seção "Ao vivo": não diz que as leituras estão chegando se nenhuma chegou. */
export function descricaoAoVivo(conexao: string, temLeitura: boolean): string {
  if (conexao === 'sem-broker') {
    return 'Sem conexão com o broker MQTT. Confira se o Compose está de pé; a tela reconecta sozinha.'
  }
  if (!temLeitura) return 'Nenhuma leitura chegou ainda. PPM, MQ-135 e umidade aparecem quando a placa publicar.'
  return 'Leituras chegando da placa agora: PPM, MQ-135 e umidade.'
}
