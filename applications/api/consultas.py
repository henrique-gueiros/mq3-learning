"""Consultas da tela de análise: as mesmas do dashboard do Grafana, com parâmetros.

O SQL de referência está em ``grafana/montar_dashboard.py``. Lá os filtros eram
variáveis do Grafana coladas no texto; aqui viram parâmetros do psycopg, então
nenhum valor vindo do navegador entra no SQL como texto.

Cada função recebe uma conexão aberta e devolve dados prontos para virar JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence

import psycopg
from psycopg.rows import dict_row

Janela = Literal["arquivo", "sopro"]

# sensor (prefixo na resposta) -> coluna de v_leituras
SENSORES = (("mq3", "mq3_raw"), ("mq135", "mq135_raw"), ("umid", "humidity_pct"))
PERCENTIS = (("p5", 0.05), ("p25", 0.25), ("p50", 0.5), ("p75", 0.75), ("p95", 0.95))


@dataclass(frozen=True)
class Filtros:
    """Filtros da barra da tela. ``None`` em casos ou participantes significa todos."""

    casos: Optional[Sequence[str]] = None
    participantes: Optional[Sequence[str]] = None
    janela: Janela = "arquivo"
    simulador: bool = False

    def parametros(self) -> Dict[str, Any]:
        return {
            "casos": None if self.casos is None else list(self.casos),
            "participantes": None if self.participantes is None else list(self.participantes),
            "janela": self.janela,
            "simulador": self.simulador,
        }


# Rodadas sem caso ou participante (leituras que chegaram antes da mensagem
# ``rodada``) ficam de fora, como no "All" do Grafana.
SIMULADOR = "(coalesce(origem, '') <> 'simulador' or %(simulador)s)"
PARTICIPANTES = (
    "participante is not null and (%(participantes)s::text[] is null or participante = any(%(participantes)s))"
)
CASOS = "caso is not null and (%(casos)s::text[] is null or caso = any(%(casos)s))"
SO_RODADAS_ESCOLHIDAS = f"{CASOS} and {PARTICIPANTES} and {SIMULADOR}"
LEITURAS_ESCOLHIDAS = f"(%(janela)s = 'arquivo' or em_sopro) and {SO_RODADAS_ESCOLHIDAS}"


def _linhas(con: psycopg.Connection, sql: str, parametros: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    with con.cursor(row_factory=dict_row) as cursor:
        return cursor.execute(sql, parametros or {}).fetchall()


def filtros(con: psycopg.Connection) -> Dict[str, Any]:
    """Opções da barra de filtros: casos, participantes e rodadas (mais nova primeiro)."""
    casos = _linhas(con, "select distinct caso from rodadas where caso is not null order by 1")
    participantes = _linhas(
        con, "select distinct participante from rodadas where participante is not null order by 1"
    )
    rodadas = _linhas(
        con,
        """select id::text as id, caso,
                  caso || ' · ' || participante || ' · ' || to_char(inicio, 'DD/MM HH24:MI') as rotulo
           from rodadas
           where inicio is not null and caso is not null
           order by inicio desc""",
    )
    return {
        "casos": [l["caso"] for l in casos],
        "participantes": [l["participante"] for l in participantes],
        "rodadas": rodadas,
    }


def resumo(con: psycopg.Connection, f: Filtros) -> Dict[str, Any]:
    """Situação da placa (chegou leitura nos últimos 10 s?) e totais dos filtros."""
    p = f.parametros()
    [placa] = _linhas(
        con,
        """select case when max(recebido_em) > now() - interval '10 seconds'
                       then 'recebendo' else 'parada' end as situacao
           from leituras""",
    )
    [rodadas] = _linhas(con, f"select count(*) as n from rodadas where {SO_RODADAS_ESCOLHIDAS}", p)
    [leituras] = _linhas(con, f"select count(*) as n from v_leituras where {LEITURAS_ESCOLHIDAS}", p)
    return {"placa": placa["situacao"], "rodadas": rodadas["n"], "leituras": leituras["n"]}


def distribuicao(con: psycopg.Connection, f: Filtros) -> List[Dict[str, Any]]:
    """Percentis 5, 25, 50, 75 e 95 e a média de cada sensor, por caso (boxplot)."""
    colunas = []
    for prefixo, campo in SENSORES:
        for rotulo, q in PERCENTIS:
            colunas.append(f"percentile_cont({q}) within group (order by {campo}) as {prefixo}_{rotulo}")
        colunas.append(f"avg({campo})::float8 as {prefixo}_media")
    sql = (
        f"select caso, count(*) as n, {', '.join(colunas)} "
        f"from v_leituras where {LEITURAS_ESCOLHIDAS} group by caso order by caso"
    )
    resposta = []
    for linha in _linhas(con, sql, f.parametros()):
        item: Dict[str, Any] = {"caso": linha["caso"], "n": linha["n"]}
        for prefixo, _ in SENSORES:
            chaves = [r for r, _ in PERCENTIS] + ["media"]
            item[prefixo] = {c: linha[f"{prefixo}_{c}"] for c in chaves}
        resposta.append(item)
    return resposta


def heatmap(con: psycopg.Connection, f: Filtros) -> List[Dict[str, Any]]:
    """Diferença (%) da média de cada caso em relação à do ambiente (``clean``).

    O ambiente entra no cálculo mesmo fora do filtro de casos: ele é a referência.
    """
    sql = f"""
        with medias as (
          select caso, avg(mq3_raw) as mq3, avg(mq135_raw) as mq135, avg(humidity_pct) as umid
          from v_leituras
          where (%(janela)s = 'arquivo' or em_sopro) and caso is not null and {PARTICIPANTES} and {SIMULADOR}
          group by caso)
        select m.caso,
               ((m.mq3 / nullif(b.mq3, 0) - 1) * 100)::float8 as mq3,
               ((m.mq135 / nullif(b.mq135, 0) - 1) * 100)::float8 as mq135,
               ((m.umid / nullif(b.umid, 0) - 1) * 100)::float8 as umid
        from medias m
        cross join (select * from medias where caso = 'clean') b
        where m.caso <> 'clean' and (%(casos)s::text[] is null or m.caso = any(%(casos)s))
        order by m.caso"""
    return _linhas(con, sql, f.parametros())


def dispersao(con: psycopg.Connection, f: Filtros, limite: int = 400) -> List[Dict[str, Any]]:
    """Até ``limite`` leituras por caso (MQ-3 × MQ-135), sorteadas sempre do mesmo jeito."""
    sql = f"""
        select caso, mq3_raw, mq135_raw
        from (select caso, mq3_raw, mq135_raw,
                     row_number() over (partition by caso order by md5(rodada_id::text || amostra::text)) as n
              from v_leituras
              where {LEITURAS_ESCOLHIDAS} and mq3_raw is not null and mq135_raw is not null) t
        where n <= %(limite)s
        order by caso, n"""
    return _linhas(con, sql, {**f.parametros(), "limite": limite})


def sobrepostas(con: psycopg.Connection, f: Filtros) -> List[Dict[str, Any]]:
    """Uma série por rodada: pontos ``[tempo_s, umidade, mq135, ppm]``.

    Os pontos vão em listas, não em objetos, porque são milhares e o JSON fica menor.
    """
    sql = f"""
        select rodada_id::text as rodada, caso, tempo_s, humidity_pct, mq135_raw, ppm
        from v_leituras
        where {LEITURAS_ESCOLHIDAS}
        order by rodada_id, tempo_s"""
    series: List[Dict[str, Any]] = []
    for linha in _linhas(con, sql, f.parametros()):
        if not series or series[-1]["rodada"] != linha["rodada"]:
            series.append({"rodada": linha["rodada"], "caso": linha["caso"], "pontos": []})
        series[-1]["pontos"].append([linha["tempo_s"], linha["humidity_pct"], linha["mq135_raw"], linha["ppm"]])
    return series


def leituras_rodada(con: psycopg.Connection, rodada_id: str) -> Optional[Dict[str, Any]]:
    """Leituras de uma rodada ao longo do tempo, com a marcação da janela de sopro."""
    [rodada] = _linhas(
        con, "select count(*) as n, max(caso) as caso from rodadas where id::text = %(id)s", {"id": rodada_id}
    )
    if rodada["n"] == 0:
        return None
    pontos = _linhas(
        con,
        """select tempo_s, t_ms, mq3_raw, mq135_raw, humidity_pct, ppm, em_sopro
           from v_leituras where rodada_id::text = %(id)s order by tempo_s""",
        {"id": rodada_id},
    )
    return {"rodada": rodada_id, "caso": rodada["caso"], "pontos": pontos}


def sopros(con: psycopg.Connection, f: Filtros) -> List[Dict[str, Any]]:
    """Subida do MQ-3 e do MQ-135 em cada sopro marcado (pico menos a linha de base)."""
    sql = f"""
        select caso, subida_mq3_raw as subida_mq3, subida_mq135_raw as subida_mq135
        from v_sopros
        where {SO_RODADAS_ESCOLHIDAS} and subida_mq3_raw is not null and subida_mq135_raw is not null
        order by caso, rodada_id, n"""
    return _linhas(con, sql, f.parametros())


def rodadas_sem_sopro(con: psycopg.Connection) -> List[Dict[str, Any]]:
    """Rodadas sem nenhum sopro marcado: ficam fora das subidas e da janela 'sopro'."""
    linhas = _linhas(
        con,
        """select rodada_id::text as rodada_id, caso, participante, arquivo_sessao as arquivo, inicio
           from v_rodadas_sem_sopro order by inicio desc nulls last""",
    )
    return [{**l, "inicio": l["inicio"].isoformat() if l["inicio"] else None} for l in linhas]
