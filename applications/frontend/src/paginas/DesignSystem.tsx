import { useState } from 'react'
import { Chip, Interruptor, Segmentado } from '../componentes/controles'
import { Cartao, SeloPlaca, Stat } from '../componentes/exibicao'
import { corDoCaso, nomeDoCaso, ordenarCasos } from '../dominio/casos'
import { Secao } from '../layout/Secao'
import { useTema } from '../tema/TemaProvider'
import './design-system.css'

const GRUPOS_DE_COR = [
  { nome: 'Superfícies', tokens: ['pagina', 'cartao', 'insercao', 'linha', 'linha-forte'] },
  { nome: 'Texto', tokens: ['tinta', 'corpo', 'mudo', 'primaria'] },
  { nome: 'Estados', tokens: ['azul', 'verde', 'ambar', 'vermelho'] },
]

const ESCALA = [
  { classe: 'display-xl', uso: 'Número principal ao vivo', amostra: 'Ambiente.' },
  { classe: 'display-lg', uso: 'Título de seção', amostra: 'Comparação entre os casos.' },
  { classe: 'display-md', uso: 'Título de cartão', amostra: 'Distribuição por caso' },
  { classe: 'display-sm', uso: 'Subtítulo', amostra: 'MQ-135' },
  { classe: 'corpo-lg', uso: 'Descrição de seção', amostra: 'Leituras chegando da placa agora.' },
  { classe: 'corpo-sm', uso: 'Texto de apoio', amostra: 'Recebendo = chegou leitura nos últimos 10 s.' },
  { classe: 'legenda mono', uso: 'Unidades e valores técnicos', amostra: 'mq135_raw 1063 · 92,4 %' },
]

const CASOS = ordenarCasos(['clean', 'drink', 'perfume', 'alcohol70_spray', 'alcohol70_hands', 'mouthwash', 'outro'])

/** Referência viva do design system: tokens, tipos, cores dos casos e componentes base. */
export function DesignSystem() {
  const { tema } = useTema()
  const [janela, setJanela] = useState<'arquivo' | 'sopro'>('arquivo')
  const [ativos, setAtivos] = useState<string[]>(['clean', 'drink'])
  const [simulador, setSimulador] = useState(false)

  return (
    <main>
      <Secao
        id="ds-cores"
        titulo="Design system."
        descricao="Tokens e componentes da tela, a partir do DESIGN.md da Vercel (Geist). Troque o tema no canto para ver as duas versões."
      >
        <div className="ds-grade">
          {GRUPOS_DE_COR.map((g) => (
            <Cartao key={g.nome}>
              <h3 className="display-sm">{g.nome}</h3>
              <ul className="ds-amostras">
                {g.tokens.map((t) => (
                  <li key={t}>
                    <span className="ds-amostra" style={{ background: `var(--${t})` }} />
                    <code className="mono legenda">--{t}</code>
                  </li>
                ))}
              </ul>
            </Cartao>
          ))}
          <Cartao>
            <h3 className="display-sm">Casos</h3>
            <ul className="ds-amostras">
              {CASOS.map((c) => (
                <li key={c}>
                  <span className="ds-amostra" style={{ background: corDoCaso(c, tema) }} />
                  <span className="corpo-sm">{c === 'outro' ? 'outro caso' : nomeDoCaso(c)}</span>
                </li>
              ))}
            </ul>
          </Cartao>
        </div>
        <div className="ds-gradiente" aria-hidden />
      </Secao>

      <Secao id="ds-tipos" titulo="Tipografia." descricao="Geist para tudo; Geist Mono para números e unidades, com algarismos de largura fixa.">
        <Cartao className="ds-tipos">
          {ESCALA.map((t) => (
            <div key={t.classe} className="ds-tipo">
              <code className="mono legenda">.{t.classe.split(' ')[0]}</code>
              <span className="legenda">{t.uso}</span>
              <span className={t.classe}>{t.amostra}</span>
            </div>
          ))}
        </Cartao>
      </Secao>

      <Secao id="ds-componentes" titulo="Componentes." descricao="Os blocos que a tela usa. Todos funcionam pelo teclado.">
        <div className="ds-grade">
          <Cartao>
            <h3 className="display-sm">Filtros</h3>
            <div className="ds-pilha">
              <Segmentado
                rotulo="Janela"
                valor={janela}
                aoMudar={setJanela}
                opcoes={[
                  { valor: 'arquivo', rotulo: 'Arquivo inteiro' },
                  { valor: 'sopro', rotulo: 'Só o sopro' },
                ]}
              />
              <div className="ds-linha">
                {CASOS.slice(0, 4).map((c) => (
                  <Chip
                    key={c}
                    rotulo={nomeDoCaso(c)}
                    cor={corDoCaso(c, tema)}
                    ativo={ativos.includes(c)}
                    aoAlternar={() => setAtivos((a) => (a.includes(c) ? a.filter((x) => x !== c) : [...a, c]))}
                  />
                ))}
              </div>
              <Interruptor rotulo="Incluir simulador" ligado={simulador} aoMudar={setSimulador} />
            </div>
          </Cartao>
          <Cartao>
            <h3 className="display-sm">Situação da placa</h3>
            <div className="ds-pilha">
              <SeloPlaca estado="recebendo" />
              <SeloPlaca estado="parada" />
              <SeloPlaca estado="offline" />
            </div>
          </Cartao>
          <Cartao className="ds-largo">
            <h3 className="display-sm">Números</h3>
            <div className="ds-stats">
              <Stat rotulo="PPM" valor={0.87} casas={2} variacao={117.5} destaque />
              <Stat rotulo="MQ-135" valor={1063} variacao={66.1} />
              <Stat rotulo="Umidade" valor={89.5} casas={1} unidade="%" variacao={18.1} />
              <Stat rotulo="Temperatura" valor={null} unidade="°C" />
            </div>
          </Cartao>
        </div>
      </Secao>
    </main>
  )
}
