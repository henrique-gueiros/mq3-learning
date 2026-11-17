"""Monta ``dashboards/coleta.json`` a partir das consultas daqui e do JavaScript de ``paineis/``.

Uso, da raiz do repositório::

    python applications/grafana/montar_dashboard.py

O JavaScript dos gráficos fica em arquivos ``.js`` (legíveis e verificáveis);
este script os cola dentro do JSON que o Grafana lê. Depois de mudar um painel,
rode-o e versione o ``coleta.json`` gerado. Não edite o JSON à mão.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

PASTA = Path(__file__).resolve().parent
PAINEIS = PASTA / "paineis"
SAIDA = PASTA / "dashboards" / "coleta.json"

PG = {"type": "grafana-postgresql-datasource", "uid": "${ds_pg}"}
MQTT = {"type": "grafana-mqtt-datasource", "uid": "${ds_mqtt}"}

SIMULADOR = "(coalesce(origem, '') <> 'simulador' or '$incluir_simulador' = 'sim')"
SO_RODADAS_ESCOLHIDAS = f"caso in ($caso) and participante in ($participante) and {SIMULADOR}"
LEITURAS_ESCOLHIDAS = f"('$janela' = 'arquivo' or em_sopro) and {SO_RODADAS_ESCOLHIDAS}"

# sensor (prefixo das colunas) -> coluna de v_leituras
SENSORES = (("mq3", "mq3_raw"), ("mq135", "mq135_raw"), ("umid", "humidity_pct"))


def _js(nome: str) -> str:
    return (PAINEIS / "comum.js").read_text(encoding="utf-8") + "\n" + (PAINEIS / nome).read_text(encoding="utf-8")


def _consulta(sql: str) -> Dict[str, Any]:
    return {"datasource": PG, "refId": "A", "rawQuery": True, "editorMode": "code", "format": "table", "rawSql": sql}


def _grafico(titulo: str, descricao: str, js: str, sql: str, x: int, y: int, w: int, h: int, fonte=PG, alvo=None) -> Dict[str, Any]:
    return {
        "title": titulo,
        "description": descricao,
        "type": "volkovlabs-echarts-panel",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": fonte,
        "targets": [alvo or _consulta(sql)],
        "options": {"renderer": "canvas", "editorMode": "code", "getOption": _js(js), "map": "none"},
    }


def _linha(titulo: str, y: int, filhos: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return {
        "title": titulo,
        "type": "row",
        "collapsed": bool(filhos),
        "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
        "panels": filhos or [],
    }


ESTADOS_DA_PLACA = [
    {"type": "value", "options": {"recebendo": {"text": "recebendo", "color": "green"}, "parada": {"text": "parada", "color": "red"}}}
]


def _indicador(titulo: str, sql: str, descricao: str, x: int, estados: bool = False) -> Dict[str, Any]:
    return {
        "title": titulo,
        "description": descricao,
        "type": "stat",
        "gridPos": {"x": x, "y": 0, "w": 8, "h": 3},
        "datasource": PG,
        "targets": [_consulta(sql)],
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "/.*/"},
            "colorMode": "background" if estados else "none",
            "textMode": "value",
            "graphMode": "none",
        },
        "fieldConfig": {
            "defaults": {"mappings": ESTADOS_DA_PLACA if estados else [], "color": {"mode": "fixed", "fixedColor": "text"}},
            "overrides": [],
        },
    }


def _sql_distribuicao() -> str:
    colunas = []
    for prefixo, campo in SENSORES:
        for rotulo, p in (("p5", 0.05), ("p25", 0.25), ("p50", 0.5), ("p75", 0.75), ("p95", 0.95)):
            colunas.append(f"percentile_cont({p}) within group (order by {campo}) as {prefixo}_{rotulo}")
        colunas.append(f"avg({campo}) as {prefixo}_media")
    lista = ",\n       ".join(colunas)
    return f"select caso, count(*) as n,\n       {lista}\nfrom v_leituras\nwhere {LEITURAS_ESCOLHIDAS}\ngroup by caso\norder by caso"


SQL_SEPARACAO = f"""select caso, mq3_raw, mq135_raw
from (select caso, mq3_raw, mq135_raw,
             row_number() over (partition by caso order by md5(rodada_id::text || amostra::text)) as n
      from v_leituras
      where {LEITURAS_ESCOLHIDAS} and mq3_raw is not null and mq135_raw is not null) t
where n <= 400"""

SQL_VARIACAO = f"""with medias as (
  select caso, avg(mq3_raw) as mq3, avg(mq135_raw) as mq135, avg(humidity_pct) as umid
  from v_leituras
  where ('$janela' = 'arquivo' or em_sopro) and participante in ($participante) and {SIMULADOR}
  group by caso)
select m.caso,
       (m.mq3 / b.mq3 - 1) * 100 as mq3,
       (m.mq135 / b.mq135 - 1) * 100 as mq135,
       (m.umid / b.umid - 1) * 100 as umid
from medias m
cross join (select * from medias where caso = 'clean') b
where m.caso <> 'clean' and m.caso in ($caso)
order by m.caso"""

SQL_RODADA = """select tempo_s, mq3_raw, mq135_raw, humidity_pct, em_sopro, caso
from v_leituras
where rodada_id::text = '$rodada'
order by tempo_s"""

SQL_SUBIDA = f"""select caso, subida_mq3_raw as subida_mq3, subida_mq135_raw as subida_mq135
from v_sopros
where {SO_RODADAS_ESCOLHIDAS} and subida_mq3_raw is not null and subida_mq135_raw is not null"""

SQL_PLACA = """select case when max(recebido_em) > now() - interval '10 seconds' then 'recebendo' else 'parada' end as situacao
from leituras"""


def _variaveis() -> List[Dict[str, Any]]:
    def consulta(nome: str, rotulo: str, sql: str, oculta: bool, multi: bool = True) -> Dict[str, Any]:
        return {
            "name": nome, "label": rotulo, "type": "query", "datasource": PG, "query": sql, "definition": sql,
            "refresh": 2, "multi": multi, "includeAll": multi, "hide": 2 if oculta else 0,
            "current": {"text": ["All"], "value": ["$__all"]} if multi else {},
        }

    def fixa(nome: str, rotulo: str, opcoes: str, padrao: str, oculta: bool) -> Dict[str, Any]:
        return {
            "name": nome, "label": rotulo, "type": "custom", "query": opcoes, "hide": 2 if oculta else 0,
            "current": {"text": padrao, "value": padrao},
            "options": [{"text": o, "value": o, "selected": o == padrao} for o in opcoes.split(",")],
        }

    return [
        {"name": "ds_pg", "label": "PostgreSQL", "type": "datasource", "query": PG["type"], "hide": 2},
        {"name": "ds_mqtt", "label": "MQTT", "type": "datasource", "query": MQTT["type"], "hide": 2},
        consulta("caso", "Caso", "select distinct caso from rodadas where caso is not null order by 1", False),
        consulta("participante", "Participante", "select distinct participante from rodadas where participante is not null order by 1", True),
        consulta(
            "rodada", "Rodada",
            "select id::text as __value,\n       caso || ' · ' || participante || ' · ' || to_char(inicio, 'DD/MM HH24:MI') as __text\n"
            "from rodadas\nwhere inicio is not null\norder by inicio desc",
            False, multi=False,
        ),
        fixa("janela", "Janela", "arquivo,sopro", "arquivo", False),
        fixa("incluir_simulador", "Incluir simulador", "nao,sim", "nao", True),
    ]


def montar() -> Dict[str, Any]:
    paineis: List[Dict[str, Any]] = [
        _indicador("Placa", SQL_PLACA, "Recebendo = chegou leitura no banco nos últimos 10 s.", 0, estados=True),
        _indicador(
            "Rodadas",
            f"select count(*) as rodadas from rodadas where {SO_RODADAS_ESCOLHIDAS}",
            "Rodadas dos casos escolhidos.", 8,
        ),
        _indicador(
            "Leituras",
            f"select count(*) as leituras from v_leituras where {LEITURAS_ESCOLHIDAS}",
            "Leituras dos casos escolhidos, dentro da janela escolhida.", 16,
        ),
        _linha("Comparação entre os casos", 3),
        _grafico(
            "Distribuição das leituras por caso",
            "Caixa: do 1º ao 3º quartil, com a mediana. Linhas: percentis 5 e 95. Losango: média. Todas as leituras das rodadas de cada caso.",
            "distribuicao.js", _sql_distribuicao(), 0, 4, 24, 10,
        ),
        _grafico(
            "Média em relação ao ar limpo",
            "Quanto a média de cada caso difere da média do ar limpo, por sensor. Precisa de rodadas de ar limpo.",
            "variacao.js", SQL_VARIACAO, 0, 14, 10, 9,
        ),
        _grafico(
            "MQ-3 × MQ-135 por leitura",
            "Até 400 leituras por caso, sorteadas sempre do mesmo jeito. Se os casos formam grupos separados, os dois sensores já os distinguem.",
            "separacao.js", SQL_SEPARACAO, 10, 14, 14, 9,
        ),
        _linha("Rodada selecionada", 23),
        _grafico(
            "Leituras da rodada ao longo do tempo",
            "Um gráfico por sensor. A faixa cinza é a janela de sopro (sopro + 30 s), quando há sopro marcado.",
            "rodada.js", SQL_RODADA, 0, 24, 24, 16,
        ),
        _linha(
            "Sopros marcados",
            40,
            [
                _grafico(
                    "Subida por sopro",
                    "Um ponto por sopro: pico (sopro + 30 s) menos a mediana dos 15 s antes. Aparece quando há sopros em attempts.csv ou marcados na ponte.",
                    "subida.js", SQL_SUBIDA, 0, 41, 12, 9,
                ),
                {
                    "title": "Rodadas sem sopro marcado",
                    "description": "Ficam fora do gráfico de subidas e da janela 'sopro'.",
                    "type": "table",
                    "gridPos": {"x": 12, "y": 41, "w": 12, "h": 9},
                    "datasource": PG,
                    "targets": [_consulta("select caso, participante, arquivo_sessao as arquivo, inicio\nfrom v_rodadas_sem_sopro\norder by inicio desc")],
                },
            ],
        ),
        _linha(
            "Ao vivo (placa)",
            41,
            [
                _grafico(
                    "Leituras que chegam da placa",
                    "Chega pelo MQTT, direto do broker. Fica vazio enquanto nenhuma placa publica.",
                    "aovivo.js", "", 0, 42, 24, 11, fonte=MQTT,
                    alvo={"datasource": MQTT, "refId": "A", "topic": "mq3/placa01/leituras"},
                ),
            ],
        ),
    ]
    proximo = 1
    for painel in paineis:
        painel["id"] = proximo
        proximo += 1
        for filho in painel.get("panels", []):
            filho["id"] = proximo
            proximo += 1
    return {
        "uid": "mq3-coleta",
        "title": "MQ-3 — Coleta",
        "tags": ["mq3", "coleta"],
        "timezone": "browser",
        "refresh": "",
        "time": {"from": "now-6h", "to": "now"},
        "schemaVersion": 39,
        "annotations": {"list": []},
        "templating": {"list": _variaveis()},
        "panels": paineis,
    }


def main() -> None:
    SAIDA.write_text(json.dumps(montar(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Gravado {SAIDA}")


if __name__ == "__main__":
    main()
