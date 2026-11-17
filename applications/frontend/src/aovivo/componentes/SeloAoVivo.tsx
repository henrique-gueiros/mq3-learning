import { useEffect, useState } from 'react'
import { SeloPlaca } from '../../componentes/exibicao'
import { situacaoPlaca, type EstadoAoVivo } from '../estado'
import type { Conexao } from '../useAoVivo'

/**
 * Selo da placa no cabeçalho. Tem o próprio relógio de 1 s, para "recebendo" virar
 * "sem leituras" sem mensagem nova, sem renderizar a tela inteira a cada segundo.
 */
export function SeloAoVivo({ estado, conexao }: { estado: EstadoAoVivo; conexao: Conexao }) {
  const [agora, setAgora] = useState(() => Date.now())
  useEffect(() => {
    const relogio = window.setInterval(() => setAgora(Date.now()), 1000)
    return () => window.clearInterval(relogio)
  }, [])
  return <SeloPlaca estado={conexao === 'sem-broker' ? 'sem-broker' : situacaoPlaca(estado, agora)} />
}
