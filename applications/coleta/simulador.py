"""Simulador: publica um CSV real do firmware no MQTT, como se a placa estivesse ligada.

Serve para desenvolver e demonstrar o dashboard sem a placa. Usa só CSVs
gravados pela placa (por exemplo ``esp32-esp8266/leituras/leituras.csv``); as rodadas saem
com origem ``simulador`` e ficam fora das comparações por padrão.

Uso (de dentro de ``applications/``)::

    python -m coleta.simulador ../esp32-esp8266/leituras/leituras.csv --caso clean --participante p00 --sopros 20
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from coleta.arquivos import ML
from coleta.casos import validar_caso
from coleta.config import Config
from coleta.importador import ler_csv_sessao
from coleta.mensagens import payload_evento, payload_leitura, payload_rodada
from coleta.publicador import Publicador
from coleta.serial_proto import Leitura

_PROCESSADOS = ML / "data" / "processed"


def validar_origem(caminho: Path) -> Path:
    """Recusa dados derivados: o simulador só reproduz leituras gravadas pela placa."""
    if _PROCESSADOS in caminho.resolve().parents:
        raise ValueError(f"{caminho} é um dado processado; use um CSV de sessão do firmware")
    return caminho


def instantes_de_sopro(leituras: List[Leitura], sopros_s: List[float]) -> Dict[int, int]:
    """Para cada sopro pedido, o índice e o ``t_ms`` da primeira leitura a partir dele."""
    instantes = {}
    for segundos in sopros_s:
        for indice, leitura in enumerate(leituras):
            if leitura.t_ms >= segundos * 1000:
                instantes[indice] = leitura.t_ms
                break
    return instantes


def _segundos(texto: str) -> List[float]:
    return [float(parte) for parte in texto.split(",") if parte.strip()]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m coleta.simulador", description=__doc__.split("\n\n")[0])
    parser.add_argument("csv", type=Path, help="CSV de sessão no formato do firmware")
    parser.add_argument("--caso", required=True)
    parser.add_argument("--participante", required=True)
    parser.add_argument("--intervalo", type=float, default=1.0, help="segundos entre leituras (padrão 1)")
    parser.add_argument("--sopros", type=_segundos, default=[], help="segundos da sessão com sopro, ex.: 20.4,80")
    parser.add_argument("--placa", help="padrão: PLACA ou placa01")
    args = parser.parse_args(argv)

    try:
        validar_caso(args.caso)
        leituras = ler_csv_sessao(validar_origem(args.csv))
    except (ValueError, OSError) as erro:
        print(erro, file=sys.stderr)
        return 1

    config = Config.do_ambiente()
    publicador = Publicador(config.mqtt_host, config.mqtt_port, args.placa or config.placa)
    publicador.conectar()
    if not publicador.aguardar_conexao(5):
        print(f"Broker {config.mqtt_host}:{config.mqtt_port} não respondeu.", file=sys.stderr)
        return 1

    rodada_id = str(uuid.uuid4())
    inicio = datetime.now(timezone.utc)
    publicador.publicar(
        "rodada",
        payload_rodada(rodada_id, publicador.placa, args.caso, args.participante, inicio, args.csv.name, "simulador"),
        retido=True,
    )
    sopros = instantes_de_sopro(leituras, args.sopros)
    print(f"Simulando {args.csv.name}: {len(leituras)} leituras, rodada {rodada_id}")
    try:
        for indice, leitura in enumerate(leituras):
            publicador.publicar("leituras", payload_leitura(rodada_id, leitura))
            if indice in sopros:
                publicador.publicar("eventos", payload_evento(rodada_id, "sopro_inicio", sopros[indice]))
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print()
    finally:
        publicador.publicar("eventos", payload_evento(rodada_id, "rodada_fim", leitura.t_ms))
        publicador.encerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
