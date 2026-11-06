import pytest

from coleta import banco
from coleta.tests.dados_banco import gravar_serie, nova_rodada, payload, sopro

pytestmark = pytest.mark.integracao


def _um(con, sql, *params):
    return con.execute(sql, params).fetchone()


def test_leitura_repetida_nao_duplica(pg):
    rodada = nova_rodada(pg)
    assert banco.gravar_leitura(pg, payload(rodada, 1, 1000, 1200)) is True
    assert banco.gravar_leitura(pg, payload(rodada, 1, 1000, 1200)) is False
    assert _um(pg, "select count(*) from leituras")[0] == 1


def test_leitura_antes_da_rodada(pg):
    rodada = "7f1c0a52-0000-4000-8000-000000000001"
    banco.garantir_rodada(pg, rodada, "placa01")
    banco.gravar_leitura(pg, payload(rodada, 1, 1000, 1200))
    banco.gravar_rodada(pg, {
        "rodada_id": rodada, "placa": "placa01", "caso": "clean", "participante": "p02",
        "inicio": "2026-11-05T14:00:00+00:00", "arquivo_sessao": "b.csv", "origem": "ponte",
    })
    assert _um(pg, "select caso, participante from v_leituras") == ("clean", "p02")


def test_evento_repetido_nao_duplica(pg):
    rodada = nova_rodada(pg)
    sopro(pg, rodada, 20000)
    sopro(pg, rodada, 20000)
    assert _um(pg, "select count(*) from v_sopros")[0] == 1


def test_sopro_sem_fim_usa_5s(pg):
    rodada = nova_rodada(pg)
    gravar_serie(pg, rodada, [(19000, 100), (21000, 300)])
    sopro(pg, rodada, 20000)
    assert _um(pg, "select inicio_ms, fim_ms from v_sopros") == (20000, 25000)


def test_sopro_com_fim(pg):
    rodada = nova_rodada(pg)
    sopro(pg, rodada, 20000, 23000)
    sopro(pg, rodada, 80000)
    assert pg.execute("select n, fim_ms from v_sopros order by n").fetchall() == [(1, 23000), (2, 85000)]


def test_base_e_mediana_e_subida(pg):
    rodada = nova_rodada(pg)
    gravar_serie(pg, rodada, [
        (4000, 999),                      # mais de 15 s antes: fora da base
        (10000, 100), (12000, 100), (14000, 900),   # base: mediana 100
        (21000, 600, 700),                # pico dentro de [20000, 55000]
        (56000, 700),                     # depois da janela: fora do pico
    ])
    sopro(pg, rodada, 20000)
    assert _um(pg, "select base_mq3_raw, pico_mq3_raw, subida_mq3_raw from v_sopros") == (100, 600, 500)


def test_media_arquivo_e_sopro(pg):
    rodada = nova_rodada(pg)
    gravar_serie(pg, rodada, [(1000, 100), (21000, 400), (30000, 600), (90000, 100)])
    sopro(pg, rodada, 20000)
    medias = dict(pg.execute("select janela, media_mq3_raw from v_media_rodada").fetchall())
    assert medias == {"arquivo": 300, "sopro": 500}


def test_rodada_sem_sopro(pg):
    rodada = nova_rodada(pg)
    gravar_serie(pg, rodada, [(1000, 100)])
    assert _um(pg, "select count(*) from v_rodadas_sem_sopro")[0] == 1
    assert _um(pg, "select n_leituras, media_mq3_raw from v_media_rodada where janela = 'sopro'") == (0, None)


def test_simulador_fora_da_lista_sem_sopro(pg):
    nova_rodada(pg, origem="simulador")
    assert _um(pg, "select count(*) from v_rodadas_sem_sopro")[0] == 0


def test_dht_vazio_nao_quebra_media(pg):
    rodada = nova_rodada(pg)
    banco.gravar_leitura(pg, payload(rodada, 1, 1000, 100, umidade=None))
    banco.gravar_leitura(pg, payload(rodada, 2, 2000, 100, umidade=60.0))
    assert _um(pg, "select media_humidity_pct from v_media_rodada where janela = 'arquivo'")[0] == 60


def test_rodada_fim_grava_sha_e_fim(pg):
    rodada = nova_rodada(pg)
    banco.gravar_evento(pg, {"rodada_id": rodada, "tipo": "rodada_fim", "t_ms": 9, "sha256": "ab" * 32})
    assert banco.rodada_por_sha(pg, "ab" * 32) == rodada
    assert _um(pg, "select fim is not null from rodadas")[0] is True


def test_views_sem_ppm_nem_alcool(pg):
    for view in ("v_leituras", "v_media_rodada", "v_sopros"):
        colunas = {d.name for d in pg.execute(f"select * from {view} limit 0").description}
        assert not colunas & {"ppm", "alcool"}, view


def test_tempo_desde_o_inicio(pg):
    rodada = nova_rodada(pg)
    gravar_serie(pg, rodada, [(5000, 100), (7500, 100)])
    assert [r[0] for r in pg.execute("select tempo_s from v_leituras order by amostra")] == [0, 2.5]
