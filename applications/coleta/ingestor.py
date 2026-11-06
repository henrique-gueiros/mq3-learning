"""Ingestor: assina o MQTT e grava rodadas, leituras e eventos no PostgreSQL.

Roda no Docker Compose (``python -m coleta.ingestor``). A sessão MQTT é
persistente: se o ingestor cair, o broker guarda as mensagens de QoS 1 e as
entrega quando ele voltar. Mensagens repetidas não duplicam nada no banco.
"""

from __future__ import annotations

import sys
import time

import paho.mqtt.client as mqtt
import psycopg

from coleta import banco
from coleta.config import Config
from coleta.mensagens import decodificar

ASSINATURAS = ("mq3/+/rodada", "mq3/+/leituras", "mq3/+/eventos")
_ERROS_DE_MENSAGEM = (ValueError, KeyError, psycopg.DataError, psycopg.IntegrityError, psycopg.ProgrammingError)


def tratar(con: psycopg.Connection, topico: str, dados: bytes) -> None:
    """Grava uma mensagem; mensagem inválida vira um aviso e é descartada."""
    partes = topico.split("/")
    if len(partes) != 3 or partes[0] != "mq3":
        return
    _, placa, tipo = partes
    if tipo not in ("rodada", "leituras", "eventos"):
        return
    try:
        payload = decodificar(dados)
        if tipo == "rodada":
            banco.gravar_rodada(con, {**payload, "placa": placa})
        elif tipo == "leituras":
            banco.garantir_rodada(con, payload["rodada_id"], placa)
            banco.gravar_leitura(con, payload)
        else:
            banco.garantir_rodada(con, payload["rodada_id"], placa)
            banco.gravar_evento(con, payload)
    except _ERROS_DE_MENSAGEM as erro:
        print(f"aviso: mensagem descartada em {topico}: {erro}", flush=True)


def _conectar_banco(dsn: str) -> psycopg.Connection:
    while True:
        try:
            return psycopg.connect(dsn)
        except psycopg.OperationalError as erro:
            print(f"Banco indisponível ({erro}); tentando de novo em 2 s.", flush=True)
            time.sleep(2)


def main() -> int:
    config = Config.do_ambiente()
    estado = {"con": _conectar_banco(config.pg_dsn)}

    def ao_conectar(cliente, _userdata, _flags, codigo, _props):
        if codigo.is_failure:
            print(f"Broker recusou a conexão: {codigo}", flush=True)
            return
        for assinatura in ASSINATURAS:
            cliente.subscribe(assinatura, qos=1)
        print(f"Ingestor conectado a {config.mqtt_host}:{config.mqtt_port}.", flush=True)

    def ao_receber(_cliente, _userdata, mensagem):
        try:
            tratar(estado["con"], mensagem.topic, mensagem.payload)
        except psycopg.OperationalError:
            print("Conexão com o banco caiu; reconectando.", flush=True)
            estado["con"] = _conectar_banco(config.pg_dsn)
            tratar(estado["con"], mensagem.topic, mensagem.payload)

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mq3-ingestor", clean_session=False)
    cliente.on_connect = ao_conectar
    cliente.on_message = ao_receber
    cliente.connect_async(config.mqtt_host, config.mqtt_port)
    cliente.loop_forever(retry_first_connection=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
