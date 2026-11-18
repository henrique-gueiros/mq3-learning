import { useCallback } from 'react'
import { useRodadasSemSopro, useSopros } from '../api/consultas'
import { corDoCaso, nomeDoCaso } from '../dominio/casos'
import { formatarDataHora } from '../dominio/formato'
import type { CoresGrafico } from '../graficos/aoVivo'
import { GraficoECharts } from '../graficos/GraficoECharts'
import { opcoesSubida } from '../graficos/subida'
import { Secao } from '../layout/Secao'
import { useTema } from '../tema/TemaProvider'
import { CartaoGrafico } from './CartaoGrafico'
import type { PropsSecao } from './tipos'

const ALTURA = 320

/** Frente 2D: subida por sopro e rodadas sem sopro (plano, 4.6). */
export function SecaoSopros({ filtros }: PropsSecao) {
  const { tema } = useTema()
  const sopros = useSopros(filtros)
  const semSopro = useRodadasSemSopro()
  const fSubida = useCallback(
    (cores: CoresGrafico, animar: boolean) => opcoesSubida({ dados: sopros.data ?? [], cores, tema, animar }),
    [sopros.data, tema],
  )
  const titulo = 'Rodadas sem sopro marcado'
  return (
    <Secao id="sopros" titulo="Sopros marcados." descricao="Quanto cada sopro fez os sensores subirem.">
      <div className="grade-analise">
        <CartaoGrafico
          className="grade-larga"
          titulo="Subida por sopro"
          descricao="Um ponto por sopro: pico (sopro + 30 s) menos a mediana dos 15 s antes."
          consulta={sopros}
          vazio={sopros.data?.length === 0 ? 'Nenhum sopro marcado. Marque com Enter na ponte ou em attempts.csv.' : undefined}
          altura={ALTURA}
        >
          <GraficoECharts opcoes={fSubida} rotulo="Dispersão da subida por sopro: MQ-3 × MQ-135, colorida pelo caso" altura={ALTURA} />
        </CartaoGrafico>
        <CartaoGrafico
          className="grade-estreita"
          titulo={titulo}
          descricao="Ficam fora do gráfico de subidas e da janela 'só o sopro'."
          consulta={semSopro}
          vazio={semSopro.data?.length === 0 ? 'Todas as rodadas têm sopro marcado.' : undefined}
        >
          <div className="tabela-rolagem">
            <table className="tabela" aria-label={titulo}>
              <thead>
                <tr>
                  <th scope="col">Rodada</th>
                  <th scope="col">Início</th>
                </tr>
              </thead>
              <tbody>
                {semSopro.data?.map((r) => (
                  <tr key={r.rodada_id}>
                    <td className="tabela-rodada">
                      <span className="tabela-caso">
                        <span className="chip-cor tabela-cor" style={{ background: corDoCaso(r.caso, tema) }} aria-hidden />
                        <span>{`${nomeDoCaso(r.caso)} · ${r.participante}`}</span>
                      </span>
                      <span className="tabela-arquivo" title={r.arquivo}>
                        {r.arquivo}
                      </span>
                    </td>
                    <td className="mono">{formatarDataHora(r.inicio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CartaoGrafico>
      </div>
    </Secao>
  )
}
