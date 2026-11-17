import pytest
from fastapi.testclient import TestClient

from api.app import app, conexao
from api.tests.dados import constante, leituras, rodada, sopro


@pytest.fixture
def cliente(pg):
    app.dependency_overrides[conexao] = lambda: pg
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def cliente_sem_banco():
    app.dependency_overrides[conexao] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_janela_invalida_e_recusada(cliente_sem_banco):
    assert cliente_sem_banco.get("/api/resumo", params={"janela": "tudo"}).status_code == 422


def test_saude_nao_precisa_de_banco(cliente_sem_banco):
    assert cliente_sem_banco.get("/api/saude").json() == {"ok": True}


@pytest.mark.integracao
def test_filtros_vem_da_query_string(cliente, pg):
    leituras(pg, rodada(pg, "clean"), constante(2, 100, 400, 50.0))
    leituras(pg, rodada(pg, "drink"), constante(3, 100, 400, 50.0))
    leituras(pg, rodada(pg, "perfume"), constante(4, 100, 400, 50.0))
    resposta = cliente.get("/api/resumo", params=[("caso", "drink"), ("caso", "perfume")])
    assert resposta.json()["leituras"] == 7


@pytest.mark.integracao
def test_simulador_so_entra_quando_pedido(cliente, pg):
    leituras(pg, rodada(pg, "clean", origem="simulador"), constante(2, 100, 400, 50.0))
    assert cliente.get("/api/resumo").json()["leituras"] == 0
    assert cliente.get("/api/resumo", params={"simulador": "true"}).json()["leituras"] == 2


@pytest.mark.integracao
def test_rotas_dos_graficos_respondem(cliente, pg):
    leituras(pg, rodada(pg, "clean"), constante(3, 100, 400, 50.0))
    r = rodada(pg, "drink")
    leituras(pg, r, [(10000, 100, 400, 50.0), (21000, 600, 700, 60.0)])
    sopro(pg, r, 20000)
    for rota in ("filtros", "distribuicao", "heatmap", "dispersao", "sobrepostas", "sopros", "rodadas-sem-sopro"):
        resposta = cliente.get(f"/api/{rota}")
        assert resposta.status_code == 200, rota
    assert cliente.get(f"/api/rodadas/{r}/leituras").json()["caso"] == "drink"


@pytest.mark.integracao
def test_rodada_desconhecida_da_404(cliente):
    assert cliente.get("/api/rodadas/00000000-0000-4000-8000-000000000000/leituras").status_code == 404
