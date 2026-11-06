"""Cliente MQTT que publica as mensagens de uma placa sem nunca travar a coleta.

Se o broker estiver fora do ar, ``publicar`` só devolve ``False``: quem chama
continua gravando o CSV, e o cliente reconecta sozinho em segundo plano.
"""

from __future__ import annotations

import threading

import paho.mqtt.client as mqtt

from coleta.mensagens import codificar, payload_status, topico


class Publicador:
    def __init__(self, host: str, port: int, placa: str):
        self.host = host
        self.port = port
        self.placa = placa
        self.conectado = False
        self._conexao = threading.Event()
        self._retidos: dict[str, bytes] = {}
        self._cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._cliente.will_set(topico(placa, "status"), codificar(payload_status(False)), qos=1, retain=True)
        self._cliente.on_connect = self._ao_conectar
        self._cliente.on_disconnect = self._ao_desconectar

    def conectar(self) -> None:
        """Começa a conectar em segundo plano; não espera o broker responder."""
        self._cliente.connect_async(self.host, self.port)
        self._cliente.loop_start()

    def aguardar_conexao(self, segundos: float) -> bool:
        """Espera o broker aceitar a conexão por até ``segundos``."""
        return self._conexao.wait(segundos)

    def publicar(self, tipo: str, payload: dict, retido: bool = False) -> bool:
        """Publica em ``mq3/<placa>/<tipo>``; ``False`` se o broker não estiver conectado.

        Mensagens retidas são guardadas e republicadas a cada reconexão, para o
        broker sempre ter a rodada atual mesmo que tenha caído no meio.
        """
        nome = topico(self.placa, tipo)
        dados = codificar(payload)
        if retido:
            self._retidos[nome] = dados
        if not self.conectado:
            return False
        resultado = self._cliente.publish(nome, dados, qos=1, retain=retido)
        return resultado.rc == mqtt.MQTT_ERR_SUCCESS

    def encerrar(self) -> None:
        """Avisa ``offline`` (se conectado) e para o cliente."""
        if self.conectado:
            offline = codificar(payload_status(False))
            self._cliente.publish(topico(self.placa, "status"), offline, qos=1, retain=True).wait_for_publish(2)
        self._cliente.disconnect()
        self._cliente.loop_stop()

    def _ao_conectar(self, cliente, _userdata, _flags, codigo, _props) -> None:
        if codigo.is_failure:
            return
        self.conectado = True
        cliente.publish(topico(self.placa, "status"), codificar(payload_status(True)), qos=1, retain=True)
        for nome, dados in self._retidos.items():
            cliente.publish(nome, dados, qos=1, retain=True)
        self._conexao.set()

    def _ao_desconectar(self, _cliente, _userdata, _flags, _codigo, _props) -> None:
        self.conectado = False
        self._conexao.clear()
