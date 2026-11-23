"""HTTP da aba Modelo.

A tela manda um recorte de sopro e recebe a mesma resposta de
``montar_resultado``. Nada é gravado no banco: o exemplo não entra na coleta.

Sobe sozinho (``python -m mq3mqtt.classificar_http``, porta 8010) ou como
thread do servidor MQTT.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from mq3mqtt.classify import montar_resultado
from mq3mqtt.config import load_settings

log = logging.getLogger("mq3mqtt.modelo_http")

MAX_CORPO = 1_000_000
MAX_LEITURAS = 2_000
_CAMPOS = ("t_ms", "mq3_raw", "mq135_raw", "temperature_c", "humidity_pct", "ppm")
_OBRIGATORIOS = ("t_ms", "mq3_raw")


class PedidoInvalido(ValueError):
    """O JSON do pedido não é um sopro que dê para classificar."""


def classificar_pedido(pedido: dict[str, Any], model_path: Path) -> dict[str, Any]:
    """Classifica o recorte. Sem o arquivo do modelo, devolve ``sem_modelo``."""
    leituras = pedido.get("leituras")
    if not isinstance(leituras, list) or not leituras:
        raise PedidoInvalido("o pedido precisa de uma lista de leituras")
    if len(leituras) > MAX_LEITURAS:
        raise PedidoInvalido("recorte longo demais")
    try:
        inicio_s = float(pedido["blow_start_s"])
        fim_s = float(pedido["blow_end_s"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PedidoInvalido("blow_start_s e blow_end_s precisam ser números") from exc
    if fim_s <= inicio_s:
        raise PedidoInvalido("o fim do sopro precisa ser depois do início")

    sessao = str(pedido.get("sessao") or "demo.csv")
    if len(sessao) > 200 or "/" in sessao or "\\" in sessao:
        raise PedidoInvalido("nome de sessão inválido")
    attempt_id = pedido.get("attempt_id")
    if attempt_id is not None:
        attempt_id = str(attempt_id)
        if len(attempt_id) > 200:
            raise PedidoInvalido("attempt_id longo demais")

    limpas = [_leitura(linha, i) for i, linha in enumerate(leituras)]
    inicio = {"t_ms": int(round(inicio_s * 1000)), "attempt_id": attempt_id}
    return montar_resultado(sessao, inicio, int(round(fim_s * 1000)), limpas, Path(model_path))


def responder(metodo: str, caminho: str, corpo: bytes, model_path: Path) -> tuple[int, dict[str, Any]]:
    """Traduz um pedido HTTP na resposta JSON. Não abre socket."""
    rota = caminho.split("?", 1)[0].rstrip("/") or "/"
    if metodo == "GET" and rota in ("/modelo/saude", "/saude"):
        return 200, {"ok": True, "modelo": Path(model_path).is_file()}
    if metodo != "POST" or rota not in ("/modelo/classificar", "/classificar"):
        return 404, {"detail": "rota não encontrada"}
    if len(corpo) > MAX_CORPO:
        return 413, {"detail": "pedido grande demais"}
    try:
        pedido = json.loads(corpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"detail": "JSON inválido"}
    if not isinstance(pedido, dict):
        return 400, {"detail": "o corpo precisa ser um objeto"}
    try:
        return 200, classificar_pedido(pedido, model_path)
    except PedidoInvalido as exc:
        return 400, {"detail": str(exc)}
    except Exception as exc:
        traduzido = _capturar_validacao(exc)
        if traduzido is not None:
            return traduzido
        log.exception("falha ao classificar")
        return 500, {"detail": "o modelo não conseguiu classificar este sopro"}


def servir(model_path: Path, host: str = "0.0.0.0", porta: int = 8010) -> ThreadingHTTPServer:
    """Abre o servidor. ``porta`` 0 escolhe uma porta livre (útil em teste)."""
    handler = _handler(Path(model_path))
    return ThreadingHTTPServer((host, porta), handler)


def iniciar_em_fundo(model_path: Path) -> None:
    """Sobe o HTTP numa thread daemon. Falha de porta fica no log e o MQTT segue."""
    porta = int(os.environ.get("MODEL_HTTP_PORT", "8010"))
    try:
        server = servir(model_path, "0.0.0.0", porta)
    except OSError:
        log.exception("não abri a porta HTTP %s", porta)
        return
    threading.Thread(target=server.serve_forever, name="modelo-http", daemon=True).start()
    log.info("classificação HTTP na porta %s", porta)


def main() -> None:
    """Serve só o HTTP, sem broker. É o processo do container ``model`` da tela."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    porta = int(os.environ.get("MODEL_HTTP_PORT", "8010"))
    server = servir(settings.model_path, "0.0.0.0", porta)
    log.info("classificação HTTP na porta %s, arquivo %s", porta, settings.model_path)
    server.serve_forever()


def _handler(model_path: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._responder(b"")

        def do_POST(self) -> None:
            tamanho = int(self.headers.get("Content-Length", "0") or 0)
            if tamanho > MAX_CORPO:
                self._enviar(413, {"detail": "pedido grande demais"})
                return
            self._responder(self.rfile.read(tamanho))

        def log_message(self, fmt: str, *args: Any) -> None:
            log.info("%s - %s", self.address_string(), fmt % args)

        def _responder(self, corpo: bytes) -> None:
            status, payload = responder(self.command, self.path, corpo, model_path)
            self._enviar(status, payload)

        def _enviar(self, status: int, payload: dict[str, Any]) -> None:
            texto = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(texto)))
            self.end_headers()
            self.wfile.write(texto)

    return Handler


def _capturar_validacao(exc: Exception) -> tuple[int, dict[str, Any]] | None:
    """Traduz erro de esquema do ml/ em 400. Sem o pacote, deixa o 500 genérico."""
    try:
        from src.data_validation import DataValidationError
    except ImportError:
        return None
    if not isinstance(exc, DataValidationError):
        return None
    detalhe = exc.problems[0] if exc.problems else "leituras inválidas"
    return 400, {"detail": detalhe}


def _leitura(linha: Any, indice: int) -> dict[str, Any]:
    if not isinstance(linha, dict):
        raise PedidoInvalido(f"leitura {indice} não é um objeto")
    limpa: dict[str, Any] = {}
    for campo in _CAMPOS:
        if campo not in linha or linha[campo] is None or linha[campo] == "":
            if campo in _OBRIGATORIOS:
                raise PedidoInvalido(f"leitura {indice} sem {campo}")
            continue
        try:
            numero = float(linha[campo])
        except (TypeError, ValueError) as exc:
            raise PedidoInvalido(f"leitura {indice}: {campo} não é número") from exc
        if numero != numero or numero in (float("inf"), float("-inf")):
            raise PedidoInvalido(f"leitura {indice}: {campo} inválido")
        limpa[campo] = int(round(numero)) if campo == "t_ms" else numero
    if limpa["t_ms"] < 0:
        raise PedidoInvalido(f"leitura {indice}: t_ms negativo")
    return limpa


if __name__ == "__main__":
    main()
