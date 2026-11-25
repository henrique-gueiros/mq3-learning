"""Alerta por Telegram quando o modelo classifica um sopro como sob_efeito."""

import json

from mq3mqtt.alerta import Alertador, texto_do_alerta

RESULTADO = {
    "rodada_id": "r1",
    "t_ms": 45000,
    "sessao": "leituras_3.csv",
    "attempt_id": "leituras_3@40s",
    "status": "classificado",
    "prediction": "sob_efeito",
    "prob_sem_efeito": 0.2,
    "prob_sob_efeito": 0.8,
    "detalhe": "",
}


def _corpo(**extra) -> bytes:
    return json.dumps({**RESULTADO, **extra}).encode("utf-8")


def test_texto_nao_afirma_embriaguez():
    texto = texto_do_alerta("placa01", RESULTADO)
    assert "placa01" in texto
    assert "80,0%" in texto
    assert "condições do experimento" in texto
    assert "embriag" not in texto.lower()


def test_envia_so_para_sob_efeito():
    enviados = []
    alertador = Alertador(token="t", chat_id="c", enviar=lambda url, dados: enviados.append((url, dados)))

    alertador.ao_receber("mq3/placa01/resultado", _corpo())
    alertador.ao_receber("mq3/placa01/resultado", _corpo(prediction="sem_efeito", t_ms=90000))
    alertador.ao_receber("mq3/placa01/resultado", _corpo(prediction=None, status="sem_modelo", t_ms=91000))
    alertador.ao_receber("mq3/placa01/resultado", _corpo(t_ms=92000, origem="continuo", alerta=False))

    assert len(enviados) == 1
    url, dados = enviados[0]
    assert url == "https://api.telegram.org/bott/sendMessage"
    assert dados["chat_id"] == "c"


def test_resultado_repetido_alerta_uma_vez():
    enviados = []
    alertador = Alertador(token="t", chat_id="c", enviar=lambda url, dados: enviados.append(dados))
    alertador.ao_receber("mq3/placa01/resultado", _corpo())
    alertador.ao_receber("mq3/placa01/resultado", _corpo())
    assert len(enviados) == 1


def test_sem_token_nao_envia_nada():
    enviados = []
    alertador = Alertador(token="", chat_id="", enviar=lambda url, dados: enviados.append(dados))
    alertador.ao_receber("mq3/placa01/resultado", _corpo())
    assert enviados == []


def test_ignora_outros_topicos_e_lixo():
    enviados = []
    alertador = Alertador(token="t", chat_id="c", enviar=lambda url, dados: enviados.append(dados))
    alertador.ao_receber("mq3/placa01/eventos", _corpo())
    alertador.ao_receber("mq3/placa01/resultado", b"nao e json")
    assert enviados == []


def test_falha_no_envio_nao_derruba():
    def falha(url, dados):
        raise OSError("sem rede")

    alertador = Alertador(token="t", chat_id="c", enviar=falha)
    alertador.ao_receber("mq3/placa01/resultado", _corpo())  # só registra no log


def test_depois_de_uma_falha_o_reenvio_alerta():
    enviados = []
    tentativas = []

    def enviar(url, dados):
        tentativas.append(dados)
        if len(tentativas) == 1:
            raise OSError("sem rede")
        enviados.append(dados)

    alertador = Alertador(token="t", chat_id="c", enviar=enviar)
    alertador.ao_receber("mq3/placa01/resultado", _corpo())
    alertador.ao_receber("mq3/placa01/resultado", _corpo())
    assert len(enviados) == 1
