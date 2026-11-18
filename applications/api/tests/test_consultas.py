import pytest

from api import consultas
from api.consultas import Filtros
from api.tests.dados import constante, leituras, rodada, sopro

pytestmark = pytest.mark.integracao


def test_filtros_lista_casos_participantes_e_rodadas(pg):
    antiga = rodada(pg, "clean", "p02", inicio="2026-11-05T10:00:00+00:00")
    nova = rodada(pg, "drink", "p01", inicio="2026-11-06T09:30:00+00:00")
    resposta = consultas.filtros(pg)
    assert resposta["casos"] == ["clean", "drink"]
    assert resposta["participantes"] == ["p01", "p02"]
    assert [r["id"] for r in resposta["rodadas"]] == [nova, antiga]
    assert resposta["rodadas"][0]["caso"] == "drink"
    assert resposta["rodadas"][0]["participante"] == "p01"
    assert resposta["rodadas"][0]["inicio"].isoformat() == "2026-11-06T09:30:00+00:00"


def test_filtros_diz_a_origem_de_cada_rodada(pg):
    rodada(pg, "clean", origem="simulador", inicio="2026-11-06T09:30:00+00:00")
    rodada(pg, "drink", origem="ponte", inicio="2026-11-05T09:30:00+00:00")
    assert [r["origem"] for r in consultas.filtros(pg)["rodadas"]] == ["simulador", "ponte"]


def test_resumo_conta_rodadas_e_leituras_sem_o_simulador(pg):
    clean = rodada(pg, "clean")
    leituras(pg, clean, constante(3, 100, 400, 50.0))
    simulada = rodada(pg, "clean", origem="simulador")
    leituras(pg, simulada, constante(5, 100, 400, 50.0))
    assert consultas.resumo(pg, Filtros()) == {"placa": "recebendo", "rodadas": 1, "leituras": 3}
    assert consultas.resumo(pg, Filtros(simulador=True))["leituras"] == 8


def test_resumo_sem_leituras_diz_que_a_placa_esta_parada(pg):
    assert consultas.resumo(pg, Filtros()) == {"placa": "parada", "rodadas": 0, "leituras": 0}


def test_filtro_por_caso_e_participante(pg):
    leituras(pg, rodada(pg, "clean", "p01"), constante(2, 100, 400, 50.0))
    leituras(pg, rodada(pg, "drink", "p01"), constante(3, 100, 400, 50.0))
    leituras(pg, rodada(pg, "drink", "p02"), constante(4, 100, 400, 50.0))
    assert consultas.resumo(pg, Filtros(casos=("drink",)))["leituras"] == 7
    assert consultas.resumo(pg, Filtros(casos=("drink",), participantes=("p02",)))["leituras"] == 4


def test_distribuicao_tem_percentis_e_media_por_sensor(pg):
    r = rodada(pg, "perfume")
    leituras(pg, r, [(i * 1000, v, 2 * v, float(v)) for i, v in enumerate([10, 20, 30, 40, 50])])
    [linha] = consultas.distribuicao(pg, Filtros())
    assert linha["caso"] == "perfume" and linha["n"] == 5
    assert linha["mq3"] == {"p5": 12, "p25": 20, "p50": 30, "p75": 40, "p95": 48, "media": 30}
    assert linha["mq135"]["p50"] == 60
    assert linha["umid"]["media"] == 30


def test_janela_sopro_so_usa_leituras_do_sopro(pg):
    r = rodada(pg, "drink")
    leituras(pg, r, [(0, 100, 400, 50.0), (20000, 900, 400, 50.0), (100000, 100, 400, 50.0)])
    sopro(pg, r, 20000)
    [linha] = consultas.distribuicao(pg, Filtros(janela="sopro"))
    assert linha["n"] == 1 and linha["mq3"]["media"] == 900


def test_heatmap_compara_cada_caso_com_o_ambiente(pg):
    leituras(pg, rodada(pg, "clean"), constante(2, 100, 400, 50.0))
    leituras(pg, rodada(pg, "drink"), constante(2, 150, 300, 55.0))
    assert consultas.heatmap(pg, Filtros()) == [{"caso": "drink", "mq3": 50, "mq135": -25, "umid": pytest.approx(10)}]


def test_heatmap_usa_o_ambiente_mesmo_quando_ele_nao_esta_no_filtro(pg):
    leituras(pg, rodada(pg, "clean"), constante(2, 100, 400, 50.0))
    leituras(pg, rodada(pg, "drink"), constante(2, 200, 400, 50.0))
    assert consultas.heatmap(pg, Filtros(casos=("drink",)))[0]["mq3"] == 100


def test_heatmap_sem_ambiente_fica_vazio(pg):
    leituras(pg, rodada(pg, "drink"), constante(2, 150, 300, 55.0))
    assert consultas.heatmap(pg, Filtros()) == []


def test_dispersao_limita_pontos_por_caso_sempre_igual(pg):
    leituras(pg, rodada(pg, "clean"), [(i * 1000, i, i, 50.0) for i in range(10)])
    leituras(pg, rodada(pg, "drink"), [(i * 1000, i, i, 50.0) for i in range(3)])
    primeira = consultas.dispersao(pg, Filtros(), limite=5)
    assert sum(p["caso"] == "clean" for p in primeira) == 5
    assert sum(p["caso"] == "drink" for p in primeira) == 3
    assert consultas.dispersao(pg, Filtros(), limite=5) == primeira


def test_sobrepostas_agrupa_os_pontos_por_rodada(pg):
    r = rodada(pg, "clean")
    leituras(pg, r, [(1000, 100, 400, 50.0, 0.3), (3000, 110, 410, 51.0, 0.4)])
    assert consultas.sobrepostas(pg, Filtros()) == [
        {"rodada": r, "caso": "clean", "pontos": [[0, 50.0, 400, pytest.approx(0.3)], [2, 51.0, 410, pytest.approx(0.4)]]}
    ]


def test_leituras_da_rodada_marcam_o_sopro(pg):
    r = rodada(pg, "drink")
    leituras(pg, r, [(0, 100, 400, 50.0), (20000, 900, 450, 60.0, 0.9), (100000, 100, 400, 50.0)])
    sopro(pg, r, 20000)
    resposta = consultas.leituras_rodada(pg, r)
    assert resposta["caso"] == "drink"
    assert [p["em_sopro"] for p in resposta["pontos"]] == [False, True, False]
    assert resposta["pontos"][1] == {
        "tempo_s": 20, "t_ms": 20000, "mq3_raw": 900, "mq135_raw": 450, "humidity_pct": 60.0,
        "ppm": pytest.approx(0.9), "em_sopro": True,
    }


def test_leituras_de_rodada_desconhecida(pg):
    assert consultas.leituras_rodada(pg, "00000000-0000-4000-8000-000000000000") is None


def test_sopros_trazem_as_subidas(pg):
    r = rodada(pg, "drink")
    leituras(pg, r, [(10000, 100, 400, 50.0), (21000, 600, 700, 60.0)])
    sopro(pg, r, 20000)
    assert consultas.sopros(pg, Filtros()) == [{"caso": "drink", "subida_mq3": 500, "subida_mq135": 300}]


def test_rodadas_sem_sopro(pg):
    sem = rodada(pg, "perfume", "p03")
    com = rodada(pg, "drink")
    sopro(pg, com, 1000)
    [linha] = consultas.rodadas_sem_sopro(pg)
    assert linha["rodada_id"] == sem and linha["caso"] == "perfume" and linha["participante"] == "p03"
    assert linha["arquivo"] == "perfume.csv"
