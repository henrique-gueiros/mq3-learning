"""Alerta por Telegram quando o modelo classifica um sopro como ``sob_efeito``.

Assina ``mq3/+/resultado`` (publicado por ``mq3mqtt.ao_vivo``) e manda uma
mensagem pela Bot API do Telegram. Sem ``TELEGRAM_TOKEN`` e ``TELEGRAM_CHAT_ID``
o serviço só registra no log: nada é enviado.

``sob_efeito`` quer dizer "bebeu nas condições do experimento". O texto não
afirma embriaguez nem concentração.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Callable

log = logging.getLogger("mq3mqtt.alerta")

API = "https://api.telegram.org/bot{token}/sendMessage"


def _porcentagem(valor: Any) -> str:
    if not isinstance(valor, (int, float)):
        return "—"
    return f"{valor * 100:.1f}%".replace(".", ",")


def texto_do_alerta(placa: str, resultado: dict[str, Any]) -> str:
    """Mensagem enviada ao Telegram para um resultado ``sob_efeito``."""
    segundos = int(resultado.get("t_ms", 0)) // 1000
    return (
        f"Sopro Seguro — alerta da placa {placa}\n"
        f"O modelo classificou o sopro que terminou em {segundos // 60}:{segundos % 60:02d} "
        f"como sob efeito (probabilidade {_porcentagem(resultado.get('prob_sob_efeito'))}).\n"
        "Significa que a pessoa bebeu, nas condições do experimento; não é medida de concentração."
    )


def enviar_http(url: str, dados: dict[str, Any]) -> None:
    """POST em JSON. Erro de rede sobe como exceção."""
    pedido = urllib.request.Request(
        url,
        data=json.dumps(dados).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(pedido, timeout=10) as resposta:
        resposta.read()


class Alertador:
    """Decide se um ``resultado`` vira alerta e envia uma vez por sopro."""

    def __init__(
        self,
        token: str,
        chat_id: str,
        enviar: Callable[[str, dict[str, Any]], None] = enviar_http,
    ) -> None:
        self._token = token
        self._chat_id = chat_id
        self._enviar = enviar
        self._enviados: set[tuple[str, int]] = set()

    def ao_receber(self, topico: str, corpo: bytes) -> None:
        """Trata uma mensagem do broker; qualquer outra coisa é ignorada."""
        partes = topico.split("/")
        if len(partes) != 3 or partes[0] != "mq3" or partes[2] != "resultado":
            return
        try:
            resultado = json.loads(corpo.decode("utf-8"))
            if not isinstance(resultado, dict) or resultado.get("prediction") != "sob_efeito":
                return
            # modelo contínuo: só a janela que fecha a sequência de N sob_efeito alerta
            if not resultado.get("alerta", True):
                return
            chave = (str(resultado["rodada_id"]), int(resultado["t_ms"]))
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return
        if chave in self._enviados:
            return

        texto = texto_do_alerta(partes[1], resultado)
        if not (self._token and self._chat_id):
            self._enviados.add(chave)
            log.info("alerta (Telegram não configurado): %s", texto)
            return
        try:
            self._enviar(API.format(token=self._token), {"chat_id": self._chat_id, "text": texto})
        except Exception:
            # não marca como enviado: uma reentrega do mesmo resultado tenta de novo
            log.exception("falha ao enviar o alerta pelo Telegram")
            return
        self._enviados.add(chave)
        log.info("alerta enviado: placa %s, rodada %s", partes[1], chave[0])


def main() -> None:
    """Conecta no broker e alerta a cada ``sob_efeito``."""
    import paho.mqtt.client as mqtt

    from mq3mqtt.config import broker_recusou, load_settings

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    alertador = Alertador(os.environ.get("TELEGRAM_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", ""))

    def ao_conectar(cliente, _userdata, _flags, codigo, _props) -> None:
        if broker_recusou(codigo):
            log.error("broker recusou a conexão: %s", codigo)
            return
        cliente.subscribe("mq3/+/resultado", qos=1)
        log.info("assinando mq3/+/resultado")

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mq3-alerta")
    cliente.on_connect = ao_conectar
    cliente.on_message = lambda _c, _u, mensagem: alertador.ao_receber(mensagem.topic, mensagem.payload)
    cliente.connect_async(settings.mqtt_host, settings.mqtt_port)
    cliente.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
