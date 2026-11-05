"""Worker MQTT: assina a placa, grava no Postgres e avisa o servidor do modelo.

Depois de gravar um ``sopro_fim``, publica ``mq3/<placa>/sopro_pronto``. Esse
tópico é interno. A ESP32 não publica nele. O servidor do modelo só classifica
depois que as linhas já estão no banco.
"""

from __future__ import annotations

import logging

import paho.mqtt.client as mqtt

from mq3mqtt.config import broker_recusou, load_settings
from mq3mqtt.messages import (
    dumps,
    loads,
    parse_evento,
    parse_leitura,
    parse_status,
    parse_topic,
    topic,
)
from mq3mqtt.store import connect_with_retry, insert_evento, insert_leitura, upsert_status

log = logging.getLogger("mq3mqtt.ingest")


def main() -> None:
    """Conecta no broker e no banco e fica gravando mensagens."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    conn = connect_with_retry(settings.database_url)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mq3-ingest")
    client.user_data_set({"conn": conn})
    client.on_connect = _on_connect
    client.on_message = _on_message
    log.info("worker conectando em %s:%s", settings.mqtt_host, settings.mqtt_port)
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_forever()


def _on_connect(client, userdata, flags, reason_code, properties) -> None:
    if broker_recusou(reason_code):
        log.error("broker recusou a conexão: %s", reason_code)
        return
    client.subscribe("mq3/+/leituras", qos=1)
    client.subscribe("mq3/+/eventos", qos=1)
    client.subscribe("mq3/+/status", qos=1)
    log.info("assinando leituras, eventos e status")


def _on_message(client, userdata, message) -> None:
    try:
        placa, kind = parse_topic(message.topic)
        data = loads(message.payload)
        conn = userdata["conn"]
        if kind == "leituras":
            inserted = insert_leitura(conn, placa, parse_leitura(data))
            log.info("leitura %s %s amostra nova=%s", placa, data.get("sessao"), inserted)
        elif kind == "eventos":
            evento = parse_evento(data)
            evento_id = insert_evento(conn, placa, evento)
            log.info("evento %s %s %s id=%s", placa, evento["evento"], evento["t_ms"], evento_id)
            if evento["evento"] == "sopro_fim" and evento_id is not None:
                client.publish(
                    topic(placa, "sopro_pronto"),
                    dumps(
                        {
                            "sessao": evento["sessao"],
                            "t_ms": evento["t_ms"],
                            "evento_id": evento_id,
                        }
                    ),
                    qos=1,
                )
        elif kind == "status":
            upsert_status(conn, placa, parse_status(data))
    except Exception:
        log.exception("mensagem ignorada em %s", message.topic)


if __name__ == "__main__":
    main()
