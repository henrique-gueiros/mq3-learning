import { useFiltros } from '../api/consultas'
import { Chip, Interruptor, Segmentado } from '../componentes/controles'
import { corDoCaso, nomeDoCaso, ordenarCasos } from '../dominio/casos'
import { useTema } from '../tema/TemaProvider'
import type { Filtros } from './filtros'
import './analise.css'

/**
 * Filtros da análise, fixos logo abaixo do cabeçalho. Nenhum caso marcado = todos
 * (os chips aparecem todos ativos). Participante não aparece, como no Grafana.
 */
export function BarraFiltros({ filtros, aoMudar }: { filtros: Filtros; aoMudar: (mudanca: Partial<Filtros>) => void }) {
  const { tema } = useTema()
  const { data } = useFiltros()
  const casos = ordenarCasos(data?.casos ?? [])
  const ativo = (c: string) => filtros.casos.length === 0 || filtros.casos.includes(c)

  // Do estado "todos" o primeiro clique isola o caso; depois cada clique liga/desliga.
  const alternar = (caso: string) => {
    if (filtros.casos.length === 0) return aoMudar({ casos: [caso] })
    const novos = filtros.casos.includes(caso) ? filtros.casos.filter((c) => c !== caso) : [...filtros.casos, caso]
    aoMudar({ casos: novos.length === casos.length ? [] : novos })
  }

  return (
    <div className="barra-filtros">
      <div className="recipiente barra-filtros-linha">
        <div className="barra-filtros-casos" role="group" aria-label="Casos">
          {casos.map((c) => (
            <Chip key={c} rotulo={nomeDoCaso(c)} cor={corDoCaso(c, tema)} ativo={ativo(c)} aoAlternar={() => alternar(c)} />
          ))}
        </div>
        <Segmentado
          rotulo="Janela"
          valor={filtros.janela}
          aoMudar={(janela) => aoMudar({ janela })}
          opcoes={[
            { valor: 'arquivo', rotulo: 'Arquivo inteiro' },
            { valor: 'sopro', rotulo: 'Só o sopro' },
          ]}
        />
        <Interruptor rotulo="Incluir simulador" ligado={filtros.simulador} aoMudar={(simulador) => aoMudar({ simulador })} />
      </div>
    </div>
  )
}
