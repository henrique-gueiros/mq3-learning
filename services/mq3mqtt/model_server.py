"""Servidor do modelo.

Fica no mesmo Docker Compose do broker, no computador da bancada. A ESP32 não
abre conexão com ele. Ele assina ``sopro_pronto``, lê a sessão no Postgres e
publica a classe em ``mq3/<placa>/resultado``.

Enquanto ``ml/models/sob_efeito.joblib`` não existir, a resposta é
``sem_modelo``. Nenhuma classe é inventada.
"""

from __future__ import annotations

import logging

import paho.mqtt.client as mqtt

from mq3mqtt.classify import montar_resultado
from mq3mqtt.config import broker_recusou, load_settings
from mq3mqtt.messages import dumps, loads, parse_sopro_pronto, parse_topic, topic
from mq3mqtt.store import (
    connect_with_retry,
    evento_por_id,
    inicio_do_sopro,
    insert_resultado,
    leituras_da_sessao,
)

log = logging.getLogger("mq3mqtt.model")


def main() -> None:
    """Conecta no broker e espera um sopro já gravado pelo worker."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    conn = connect_with_retry(settings.database_url)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mq3-model")
    client.user_data_set({"conn": conn, "model_path": settings.model_path})
    client.on_connect = _on_connect
    client.on_message = _on_message
    log.info(
        "servidor do modelo em %s:%s, arquivo %s",
        settings.mqtt_host,
        settings.mqtt_port,
        settings.model_path,
    )
    from mq3mqtt.classificar_http import iniciar_em_fundo

    iniciar_em_fundo(settings.model_path)
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_forever()


def _on_connect(client, userdata, flags, reason_code, properties) -> None:
    if broker_recusou(reason_code):
        log.error("broker recusou a conexão: %s", reason_code)
        return
    client.subscribe("mq3/+/sopro_pronto", qos=1)
    log.info("assinando sopro_pronto")


def _on_message(client, userdata, message) -> None:
    try:
        placa, kind = parse_topic(message.topic)
        if kind != "sopro_pronto":
            return
        aviso = parse_sopro_pronto(loads(message.payload))
        conn = userdata["conn"]
        evento = evento_por_id(conn, aviso["evento_id"])
        if evento is None or evento["evento"] != "sopro_fim":
            log.error("sopro_pronto sem sopro_fim no banco: %s", aviso)
            return
        inicio = inicio_do_sopro(conn, placa, aviso["sessao"], aviso["t_ms"])
        readings = leituras_da_sessao(conn, placa, aviso["sessao"])
        resultado = montar_resultado(
            aviso["sessao"],
            inicio,
            aviso["t_ms"],
            readings,
            userdata["model_path"],
        )
        insert_resultado(conn, placa, resultado)
        client.publish(topic(placa, "resultado"), dumps(resultado), qos=1)
        log.info(
            "resultado %s %s status=%s classe=%s",
            placa,
            aviso["sessao"],
            resultado["status"],
            resultado["prediction"],
        )
    except Exception:
        log.exception("falha ao classificar %s", message.topic)


if __name__ == "__main__":
    main()
