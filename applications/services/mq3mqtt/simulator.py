"""Publica um CSV do firmware no broker, uma linha por vez.

Serve para desenvolver sem a ESP32. Não gera dados novos: só reenvia um CSV
que a placa já gravou. Os segundos do sopro são os que você passar na linha
de comando, os mesmos que iriam para o attempts.csv.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import paho.mqtt.client as mqtt

from mq3mqtt.config import load_settings
from mq3mqtt.messages import dumps, leitura_de_linha_csv, topic


def main(argv: list[str] | None = None) -> None:
    """Lê o CSV e publica leituras, e o início e o fim do sopro se forem passados."""
    args = _parser().parse_args(argv)
    settings = load_settings()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mq3-simulator")
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_start()
    try:
        client.publish(topic(args.placa, "status"), dumps({"status": "online"}), qos=1)
        if args.blow_start_s is not None:
            _publicar_evento(client, args, "sopro_inicio", args.blow_start_s)
        with args.csv.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                leitura = leitura_de_linha_csv(raw, args.sessao)
                client.publish(topic(args.placa, "leituras"), dumps(leitura), qos=1)
                print(f"amostra {leitura['amostra']} t_ms={leitura['t_ms']}")
                if args.interval > 0:
                    time.sleep(args.interval)
        if args.blow_end_s is not None:
            _publicar_evento(client, args, "sopro_fim", args.blow_end_s)
        time.sleep(0.5)
    finally:
        client.loop_stop()
        client.disconnect()


def _publicar_evento(client, args, evento: str, segundo: float) -> None:
    payload = {
        "sessao": args.sessao,
        "evento": evento,
        "t_ms": int(round(segundo * 1000)),
    }
    if args.attempt_id:
        payload["attempt_id"] = args.attempt_id
    client.publish(topic(args.placa, "eventos"), dumps(payload), qos=1)
    print(f"{evento} em {segundo:g} s")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Republica um CSV do firmware no MQTT.")
    parser.add_argument("--csv", type=Path, required=True, help="CSV gravado pelo firmware")
    parser.add_argument("--placa", required=True, help="nome da placa no tópico, por exemplo bancada")
    parser.add_argument("--sessao", required=True, help="nome do arquivo da sessão, por exemplo leituras_1.csv")
    parser.add_argument("--blow-start-s", type=float, help="segundo da sessão em que o sopro começou")
    parser.add_argument("--blow-end-s", type=float, help="segundo em que o sopro terminou")
    parser.add_argument("--attempt-id", help="identificador opcional do sopro")
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="segundos entre leituras (0 publica tudo de uma vez; padrão: 1)",
    )
    return parser


if __name__ == "__main__":
    main()
