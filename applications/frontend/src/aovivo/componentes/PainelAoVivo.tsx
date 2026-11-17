import { useMemo } from 'react'
import { Stat } from '../../componentes/exibicao'
import { corDoCaso, nomeDoCaso } from '../../dominio/casos'
import { variacao } from '../../dominio/variacao'
import { rotuloTempo } from '../../graficos/aoVivo'
import { useTema } from '../../tema/TemaProvider'
import type { EstadoAoVivo } from '../estado'
import { janelasMarcadas } from '../janelas'
import { CartaoEstado } from './CartaoEstado'
import { GraficoAoVivo } from './GraficoAoVivo'
import './aovivo.css'

/** Conteúdo da seção "Ao vivo": estado do detector, três números e o gráfico. */
export function PainelAoVivo({ estado }: { estado: EstadoAoVivo }) {
  const { tema } = useTema()
  const marcadas = useMemo(() => janelasMarcadas(estado.eventos), [estado.eventos])
  const ultima = estado.leituras.at(-1)
  const { detector, rodada } = estado

  if (!ultima) {
    return (
      <div className="aovivo-grade">
        <CartaoEstado estado="calibrando" segundosNoEstado={0} temDados={false} />
        <div className="aovivo-vazio">
          <p className="corpo-sm">
            As leituras aparecem aqui assim que a placa (ou a ponte serial) publicar no broker. Para testar sem a placa, de{' '}
            <code className="mono">applications/</code>:
          </p>
          <pre className="mono codigo">
            python -m coleta.simulador ../esp32-esp8266/leituras.csv --caso clean --participante p00 --sopros 20
          </pre>
        </div>
      </div>
    )
  }

  const base = detector.base
  const segundosNoEstado = Math.max(0, (ultima.t_ms - detector.desdeMs) / 1000)
  const corRodada = rodada?.caso ? corDoCaso(rodada.caso, tema) : undefined

  return (
    <div className="aovivo-grade">
      <CartaoEstado estado={detector.estado} segundosNoEstado={segundosNoEstado} temDados />
      <div className="aovivo-numeros">
        <Stat rotulo="PPM" valor={ultima.ppm} casas={2} variacao={base ? variacao(ultima.ppm, base.ppm) : undefined} />
        <Stat rotulo="MQ-135" valor={ultima.mq135_raw} variacao={base ? variacao(ultima.mq135_raw, base.mq135) : undefined} />
        <Stat
          rotulo="Umidade"
          valor={ultima.humidity_pct}
          casas={1}
          unidade="%"
          variacao={base ? variacao(ultima.humidity_pct, base.umid) : undefined}
        />
      </div>
      <dl className="aovivo-rodada">
        <div>
          <dt className="legenda">Caso</dt>
          <dd className="corpo-sm">
            {corRodada && <span className="aovivo-cor" style={{ background: corRodada }} aria-hidden />}
            {rodada?.caso ? nomeDoCaso(rodada.caso) : 'não informado'}
          </dd>
        </div>
        <div>
          <dt className="legenda">Participante</dt>
          <dd className="corpo-sm">{rodada?.participante ?? '—'}</dd>
        </div>
        <div>
          <dt className="legenda">Placa</dt>
          <dd className="corpo-sm mono">{estado.placa}</dd>
        </div>
        <div>
          <dt className="legenda">Tempo de sessão</dt>
          <dd className="corpo-sm mono">{rotuloTempo(ultima.t_ms / 1000)}</dd>
        </div>
        {rodada?.origem === 'simulador' && (
          <div>
            <dt className="legenda">Fonte</dt>
            <dd className="corpo-sm">simulador</dd>
          </div>
        )}
      </dl>
      <div className="aovivo-grafico">
        <GraficoAoVivo
          leituras={estado.leituras}
          base={base}
          trechos={estado.trechos}
          marcadas={marcadas}
          corDaRodada={corRodada}
        />
        <ul className="aovivo-legenda legenda">
          <li><span className="aovivo-amostra linha" style={{ background: corRodada ?? 'var(--tinta)' }} />leitura</li>
          <li><span className="aovivo-amostra tracejada" />linha de base do ambiente</li>
          <li><span className="aovivo-amostra faixa-sopro" />sopro detectado</li>
          <li><span className="aovivo-amostra faixa-recuperando" />recuperando</li>
          <li><span className="aovivo-amostra contorno" />sopro marcado na ponte</li>
        </ul>
      </div>
    </div>
  )
}
