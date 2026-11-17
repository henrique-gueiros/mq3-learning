"""O dashboard versionado tem que ser o que ``montar_dashboard.py`` gera, e cada gráfico tem que montar."""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

GRAFANA = Path(__file__).resolve().parents[2] / "grafana"
_spec = importlib.util.spec_from_file_location("montar_dashboard", GRAFANA / "montar_dashboard.py")
montar_dashboard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(montar_dashboard)

NODE = shutil.which("node")
EXECUTAR = """
const entrada = JSON.parse(require('fs').readFileSync(0, 'utf8'));
globalThis.document = { body: {} };
globalThis.getComputedStyle = () => ({ backgroundColor: 'rgb(255, 255, 255)' });
const opcao = new Function('context', entrada.codigo)({ panel: { data: { series: entrada.series } }, grafana: {} });
console.log(JSON.stringify(opcao, (k, v) => (typeof v === 'function' ? 'FN' : v)));
"""


def _paineis(dashboard):
    for painel in dashboard["panels"]:
        yield painel
        yield from painel.get("panels", [])


def _painel(titulo):
    return next(p for p in _paineis(montar_dashboard.montar()) if p["title"] == titulo)


def _quadro(**colunas):
    return {"fields": [{"name": nome, "values": valores, "type": "time" if nome == "tempo" else "other"} for nome, valores in colunas.items()]}


def _opcao(titulo, series):
    codigo = _painel(titulo)["options"]["getOption"]
    saida = subprocess.run(
        [NODE, "-e", EXECUTAR], input=json.dumps({"codigo": codigo, "series": series}), capture_output=True, text=True, check=True
    )
    return json.loads(saida.stdout)


def test_dashboard_versionado_e_o_gerado():
    versionado = json.loads((GRAFANA / "dashboards" / "coleta.json").read_text(encoding="utf-8"))
    assert versionado == montar_dashboard.montar(), "rode: python applications/grafana/montar_dashboard.py"


def test_todo_grafico_usa_business_charts():
    tipos = {p["type"] for p in _paineis(montar_dashboard.montar())}
    assert tipos <= {"volkovlabs-echarts-panel", "stat", "table", "row"}
    graficos = [p for p in _paineis(montar_dashboard.montar()) if p["type"] not in ("row", "stat", "table")]
    assert graficos and all(p["type"] == "volkovlabs-echarts-panel" for p in graficos)


def test_ids_dos_paineis_sao_unicos():
    ids = [p["id"] for p in _paineis(montar_dashboard.montar())]
    assert len(ids) == len(set(ids))


def test_so_o_que_o_usuario_escolhe_fica_visivel():
    visiveis = [v["name"] for v in montar_dashboard.montar()["templating"]["list"] if v["hide"] == 0]
    assert visiveis == ["caso", "rodada", "janela"]


GRAFICOS_COM_DADOS = {
    "Distribuição das leituras por caso": lambda: [
        _quadro(
            caso=["clean", "drink"], n=[10, 5],
            **{f"{s}_{k}": [1.0, 2.0] for s in ("mq3", "mq135", "umid") for k in ("p5", "p25", "p50", "p75", "p95", "media")},
        )
    ],
    "Média em relação ao ar limpo": lambda: [_quadro(caso=["drink"], mq3=[120.0], mq135=[180.0], umid=[92.0])],
    "MQ-3 × MQ-135 por leitura": lambda: [_quadro(caso=["clean", "drink"], mq3_raw=[800, 1900], mq135_raw=[250, 700])],
    "Leituras da rodada ao longo do tempo": lambda: [
        _quadro(tempo_s=[0, 1, 2, 3], mq3_raw=[1, 2, 3, 4], mq135_raw=[1, 2, 3, 4], humidity_pct=[5, 6, 7, 8],
                em_sopro=[False, True, True, False], caso=["drink"] * 4)
    ],
    "Subida por sopro": lambda: [_quadro(caso=["drink", "perfume"], subida_mq3=[900, 100], subida_mq135=[300, 700])],
    "Leituras que chegam da placa": lambda: [_quadro(tempo=[1, 2], mq3_raw=[1, 2], mq135_raw=[3, 4], humidity_pct=[5, 6])],
}


@pytest.mark.skipif(NODE is None, reason="node não instalado")
@pytest.mark.parametrize("titulo", GRAFICOS_COM_DADOS)
def test_grafico_monta_com_dados(titulo):
    opcao = _opcao(titulo, GRAFICOS_COM_DADOS[titulo]())
    assert opcao["series"], titulo
    assert "title" not in opcao or isinstance(opcao["title"], list)


@pytest.mark.skipif(NODE is None, reason="node não instalado")
@pytest.mark.parametrize("titulo", GRAFICOS_COM_DADOS)
def test_grafico_sem_dados_avisa_em_vez_de_quebrar(titulo):
    opcao = _opcao(titulo, [])
    assert opcao["title"]["text"] and "series" not in opcao


@pytest.mark.skipif(NODE is None, reason="node não instalado")
def test_boxplot_tem_caixa_e_media_por_sensor():
    opcao = _opcao("Distribuição das leituras por caso", GRAFICOS_COM_DADOS["Distribuição das leituras por caso"]())
    assert [s["type"] for s in opcao["series"]] == ["boxplot", "scatter"] * 3


@pytest.mark.skipif(NODE is None, reason="node não instalado")
def test_rodada_marca_a_janela_de_sopro():
    opcao = _opcao("Leituras da rodada ao longo do tempo", GRAFICOS_COM_DADOS["Leituras da rodada ao longo do tempo"]())
    assert opcao["series"][0]["markArea"]["data"] == [[{"xAxis": 1}, {"xAxis": 2}]]


@pytest.mark.skipif(NODE is None, reason="node não instalado")
def test_cada_caso_mantem_sua_cor_nos_graficos():
    dispersao = _opcao("MQ-3 × MQ-135 por leitura", GRAFICOS_COM_DADOS["MQ-3 × MQ-135 por leitura"]())
    subida = _opcao("Subida por sopro", [_quadro(caso=["drink"], subida_mq3=[1], subida_mq135=[2])])
    cor_dispersao = next(s for s in dispersao["series"] if s["name"] == "bebida")["itemStyle"]["color"]
    assert cor_dispersao.startswith("rgba(235, 104, 52")
    assert subida["series"][0]["itemStyle"]["color"] == "#eb6834"
