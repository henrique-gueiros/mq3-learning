"""Ponte serial → MQTT usada durante a coleta.

Lê as leituras que a ESP32 manda pelo USB e, para cada rodada:

- grava o CSV de sessão em ``ml/data/raw/sessions/`` (formato do firmware);
- publica cada leitura no MQTT, marcada com o caso e o participante;
- registra os sopros marcados pelo operador e, no fim, acrescenta as linhas
  correspondentes ao ``ml/data/raw/attempts.csv``.

Uso (de dentro de ``applications/``)::

    python -m coleta.ponte --porta /dev/cu.usbserial-0001 --caso perfume --participante p01 --duracao 120

Durante a rodada: Enter marca o início de um sopro, ``f`` + Enter marca o fim,
Ctrl+C encerra antes da hora. O broker fora do ar não interrompe a gravação.
"""

from __future__ import annotations

import argparse
import queue
import signal
import sys
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

import serial

from coleta.arquivos import ARQUIVO_ATTEMPTS, PASTA_SESSOES, CsvSessao, anexar_attempts, linha_attempt, nome_sessao
from coleta.casos import validar_caso
from coleta.config import Config
from coleta.mensagens import payload_evento, payload_leitura, payload_rodada
from coleta.publicador import Publicador
from coleta.rodada import IGNORAR, REINICIOU, Rodada
from coleta.serial_proto import ArquivoNovo, Leitura, ler_linha

BAUD = 115200
ESPERA_BROKER_S = 3.0


class Coleta:
    """Uma rodada por vez: abre, recebe leituras e sopros, e fecha entregando os arquivos."""

    def __init__(self, args: argparse.Namespace, publicador: Publicador):
        self.args = args
        self.publicador = publicador
        self.rodada: Optional[Rodada] = None
        self.csv: Optional[CsvSessao] = None
        self._sopros_gravados = 0
        self._broker_ok = True
        self._broker_caiu = False

    def abrir_rodada(self) -> None:
        hoje = date.today()
        caminho = nome_sessao(self.args.sessoes, hoje, self.args.participante, self.args.caso)
        self.rodada = Rodada(self.args.caso, self.args.participante, self.args.duracao)
        self.csv = CsvSessao(caminho)
        self._sopros_gravados = 0
        inicio = datetime.now(timezone.utc)
        self._publicar(
            "rodada",
            payload_rodada(
                self.rodada.id, self.publicador.placa, self.args.caso, self.args.participante,
                inicio, caminho.name, "ponte",
            ),
            retido=True,
        )
        print(f"Rodada aberta: {caminho.name}")

    def receber(self, evento: Union[Leitura, ArquivoNovo]) -> None:
        resultado = self.rodada.receber(evento)
        if resultado == IGNORAR:
            return
        if resultado == REINICIOU:
            print("Placa reiniciou: encerrando a rodada e abrindo outra com o mesmo caso.")
            self.encerrar_rodada()
            self.abrir_rodada()
            self.receber(evento)
            return
        self.csv.escrever(evento)
        self._publicar("leituras", payload_leitura(self.rodada.id, evento))

    def comando(self, texto: str) -> None:
        if texto == "":
            sopro = self.rodada.marcar_inicio_sopro()
            if sopro is None:
                if self.rodada.ultimo_t_ms is None:
                    print("Ainda não chegou nenhuma leitura: sopro não marcado.")
                else:
                    print("Já há um sopro marcado neste instante.")
                return
            self._publicar("eventos", payload_evento(self.rodada.id, "sopro_inicio", sopro.inicio_ms))
            self._gravar_sopros(fechando=False)
            print(f"Sopro {len(self.rodada.sopros)} às {sopro.inicio_ms / 1000:.1f} s")
        elif texto.lower() == "f":
            sopro = self.rodada.marcar_fim_sopro()
            if sopro is None:
                print("Nenhum sopro aberto, ou ele acabou de começar: aperte f de novo em 1 s.")
                return
            self._publicar("eventos", payload_evento(self.rodada.id, "sopro_fim", sopro.fim_ms))
            self._gravar_sopros(fechando=False)
            print(f"Fim do sopro às {sopro.fim_ms / 1000:.1f} s")
        else:
            print("Comandos: Enter = início do sopro, f + Enter = fim do sopro, Ctrl+C = encerrar.")

    def encerrar_rodada(self) -> None:
        rodada, caminho = self.rodada, self.csv.caminho
        sha = self.csv.fechar()
        if not sha:
            print("Rodada sem leituras: nada gravado.")
            return
        t_fim = rodada.ultimo_t_ms
        self._publicar("eventos", payload_evento(rodada.id, "rodada_fim", t_fim, sha256=sha))
        self._gravar_sopros(fechando=True)
        print(
            f"Rodada encerrada: {caminho.name}, {rodada.leituras} leituras, {len(rodada.sopros)} sopros"
            + (" (o broker esteve fora do ar; o CSV está completo)" if self._broker_caiu else "")
        )

    def _gravar_sopros(self, fechando: bool) -> None:
        """Leva ao ``attempts.csv`` os sopros já definidos, sem esperar o fim da rodada.

        Um sopro está definido quando tem fim, quando outro sopro começou depois
        dele ou quando a rodada fecha. Assim, se o terminal for fechado no meio,
        só o sopro em andamento se perde.
        """
        sopros = self.rodada.sopros
        linhas = []
        while self._sopros_gravados < len(sopros):
            k = self._sopros_gravados
            em_aberto = sopros[k].fim_ms is None and k == len(sopros) - 1
            if em_aberto and not fechando:
                break
            linhas.append(linha_attempt(self.rodada, k + 1, self.csv.caminho))
            self._sopros_gravados += 1
        anexar_attempts(self.args.attempts, linhas)

    def _publicar(self, tipo: str, payload: dict, retido: bool = False) -> None:
        ok = self.publicador.publicar(tipo, payload, retido=retido)
        if not ok and self._broker_ok:
            print("Broker fora do ar: continuo gravando o CSV.")
            self._broker_caiu = True
        elif ok and not self._broker_ok:
            print("Broker de volta.")
        self._broker_ok = ok


def _encerrar_por_sinal(_sinal, _quadro) -> None:
    raise KeyboardInterrupt


def _ler_teclado(comandos: "queue.Queue[str]") -> None:
    for linha in sys.stdin:
        comandos.put(linha.strip())


def _argumentos(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m coleta.ponte", description=__doc__.split("\n\n")[0])
    parser.add_argument("--porta", required=True, help="porta serial da ESP32 (ex.: /dev/cu.usbserial-0001)")
    parser.add_argument("--caso", required=True, help="condição da rodada (ex.: perfume, drink)")
    parser.add_argument("--participante", required=True, help="identificador anônimo (ex.: p01)")
    parser.add_argument("--duracao", type=float, help="encerra a rodada depois de tantos segundos de leituras")
    parser.add_argument("--placa", help="nome da placa nos tópicos MQTT (padrão: PLACA ou placa01)")
    parser.add_argument("--sessoes", type=Path, default=PASTA_SESSOES, help="pasta dos CSVs de sessão")
    parser.add_argument("--attempts", type=Path, default=ARQUIVO_ATTEMPTS, help="attempts.csv a completar")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _argumentos(argv)
    try:
        validar_caso(args.caso)
    except ValueError as erro:
        print(erro, file=sys.stderr)
        return 2

    config = Config.do_ambiente()
    publicador = Publicador(config.mqtt_host, config.mqtt_port, args.placa or config.placa)
    publicador.conectar()
    if not publicador.aguardar_conexao(ESPERA_BROKER_S):
        print(f"Broker {config.mqtt_host}:{config.mqtt_port} não respondeu; a rodada será gravada só no CSV.")

    comandos: "queue.Queue[str]" = queue.Queue()
    threading.Thread(target=_ler_teclado, args=(comandos,), daemon=True).start()

    for sinal in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sinal, _encerrar_por_sinal)

    coleta = Coleta(args, publicador)
    with serial.Serial(args.porta, BAUD, timeout=0.2) as porta:
        porta.reset_input_buffer()
        coleta.abrir_rodada()
        try:
            while not coleta.rodada.terminou():
                while not comandos.empty():
                    coleta.comando(comandos.get())
                evento = ler_linha(porta.readline())
                if evento is not None:
                    coleta.receber(evento)
        except KeyboardInterrupt:
            print()
        finally:
            coleta.encerrar_rodada()
            publicador.encerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
