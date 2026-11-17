"""API somente leitura da tela de análise.

Cada rota corresponde a um gráfico da tela. Os filtros vêm na query string, por
exemplo ``/api/resumo?caso=drink&caso=perfume&janela=sopro&simulador=true``.

Uso, de ``applications/``::

    uvicorn api.app:app --reload

O banco vem de ``API_PG_DSN`` (no Compose, o usuário só leitura) ou, sem ela, da
mesma configuração das ferramentas da coleta (``coleta/config.py``).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterator, List, Optional

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query

from api import consultas
from api.consultas import Filtros, Janela
from coleta.config import Config

app = FastAPI(title="MQ-3 — API da tela", docs_url="/api/docs", openapi_url="/api/openapi.json")


def conexao() -> Iterator[psycopg.Connection]:
    """Uma conexão por requisição; a API só lê, então não há transação para confirmar."""
    dsn = os.environ.get("API_PG_DSN") or Config.do_ambiente().pg_dsn
    with psycopg.connect(dsn, autocommit=True) as con:
        yield con


def filtros(
    caso: Optional[List[str]] = Query(None, description="Casos; sem nenhum, todos."),
    participante: Optional[List[str]] = Query(None, description="Participantes; sem nenhum, todos."),
    janela: Janela = Query("arquivo", description="'arquivo' (tudo) ou 'sopro' (só a janela de sopro)."),
    simulador: bool = Query(False, description="Incluir as rodadas do simulador."),
) -> Filtros:
    return Filtros(casos=caso, participantes=participante, janela=janela, simulador=simulador)


@app.get("/api/saude")
def saude() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/api/filtros")
def rota_filtros(con=Depends(conexao)) -> Dict[str, Any]:
    return consultas.filtros(con)


@app.get("/api/resumo")
def rota_resumo(f: Filtros = Depends(filtros), con=Depends(conexao)) -> Dict[str, Any]:
    return consultas.resumo(con, f)


@app.get("/api/distribuicao")
def rota_distribuicao(f: Filtros = Depends(filtros), con=Depends(conexao)) -> List[Dict[str, Any]]:
    return consultas.distribuicao(con, f)


@app.get("/api/heatmap")
def rota_heatmap(f: Filtros = Depends(filtros), con=Depends(conexao)) -> List[Dict[str, Any]]:
    return consultas.heatmap(con, f)


@app.get("/api/dispersao")
def rota_dispersao(f: Filtros = Depends(filtros), con=Depends(conexao)) -> List[Dict[str, Any]]:
    return consultas.dispersao(con, f)


@app.get("/api/sobrepostas")
def rota_sobrepostas(f: Filtros = Depends(filtros), con=Depends(conexao)) -> List[Dict[str, Any]]:
    return consultas.sobrepostas(con, f)


@app.get("/api/rodadas/{rodada_id}/leituras")
def rota_leituras_rodada(rodada_id: str, con=Depends(conexao)) -> Dict[str, Any]:
    resposta = consultas.leituras_rodada(con, rodada_id)
    if resposta is None:
        raise HTTPException(status_code=404, detail="rodada não encontrada")
    return resposta


@app.get("/api/sopros")
def rota_sopros(f: Filtros = Depends(filtros), con=Depends(conexao)) -> List[Dict[str, Any]]:
    return consultas.sopros(con, f)


@app.get("/api/rodadas-sem-sopro")
def rota_rodadas_sem_sopro(con=Depends(conexao)) -> List[Dict[str, Any]]:
    return consultas.rodadas_sem_sopro(con)
