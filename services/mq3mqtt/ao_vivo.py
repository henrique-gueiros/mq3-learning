"""Servidor do modelo ao vivo.

Usa o mesmo contrato MQTT da coleta (``applications/coleta/mensagens.py``) e o
mesmo banco que o ingestor grava (``applications/db/01-schema.sql``):

1. assina ``mq3/+/eventos`` e ``mq3/+/leituras``;
2. num ``sopro_fim`` marcado (ponte, simulador) ou, quando a rodada não tem
   marcação (a placa sozinha), em **janelas deslizantes**: o próprio modelo
   classifica uma janela de 3 amostras a cada 3 s, como as do treino (ar parado
   e sopros de bebida também são janelas de 1 a 3 amostras). Nenhum limiar
   decide quando classificar; o alerta só sai depois de várias janelas
   ``sob_efeito`` seguidas.
3. em cada caso, espera a janela "depois do sopro" do treino
   (``AFTER_SECONDS`` de ``ml/src/features.py``) para o ingestor gravar as
   leituras que o modelo usa;
3. lê a rodada no Postgres, recorta o sopro como no treino e classifica;
4. grava em ``resultados`` e publica em ``mq3/<placa>/resultado``.

Sem ``ml/models/sob_efeito.joblib`` a resposta é ``sem_modelo``: nenhuma classe
é inventada. O mesmo processo serve o HTTP da aba Modelo (porta 8010).
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from mq3mqtt.classify import montar_resultado

log = logging.getLogger("mq3mqtt.ao_vivo")

# 30 s da janela "after" do treino, mais folga para as últimas leituras chegarem.
ESPERA_APOS_SOPRO_S = 35.0
# Leituras atrasadas (placa reconectando, ingestor atrasado): espera mais um pouco.
ESPERA_EXTRA_S = 15.0
MAX_ESPERAS_EXTRAS = 4
JANELA_DEPOIS_MS = 30_000  # AFTER_SECONDS de ml/src/features.py

# Modelo contínuo (rodada sem sopro marcado).
CONTINUO_BEFORE_MS = 15_000  # BEFORE_SECONDS: a 1ª janela precisa do "antes"
CONTINUO_SOPRO_MS = 2_000  # 3 amostras de ~1 s, como os sopros de bebida do treino
CONTINUO_AFTER_MS = JANELA_DEPOIS_MS
CONTINUO_PASSO_MS = 3_000  # uma janela nova a cada 3 s
CONTINUO_ESPERA_S = 2.0  # folga para o ingestor gravar a última leitura
CONTINUO_MAX_POR_LEITURA = 5  # leituras atrasadas não geram uma rajada de janelas
ALERTA_JANELAS_SEGUIDAS = 3  # alerta só com 3 janelas sob_efeito seguidas (~9 s)
MAX_RODADAS_CONTINUAS = 50


@dataclass(frozen=True)
class FimDeSopro:
    """Fim de um sopro marcado (``sopro_fim``) ou de uma janela do modelo contínuo.

    ``inicio_ms`` vem da janela contínua; ``None`` quando o início está no banco.
    """

    placa: str
    rodada_id: str
    t_ms: int
    inicio_ms: Optional[int] = None

    @property
    def continuo(self) -> bool:
        return self.inicio_ms is not None


def fim_de_sopro(topico: str, corpo: bytes) -> Optional[FimDeSopro]:
    """Lê a mensagem; devolve o fim de sopro, ou ``None`` para qualquer outra coisa."""
    partes = topico.split("/")
    if len(partes) != 3 or partes[0] != "mq3" or partes[2] != "eventos":
        return None
    try:
        dados = json.loads(corpo.decode("utf-8"))
        if not isinstance(dados, dict) or dados.get("tipo") != "sopro_fim":
            return None
        return FimDeSopro(placa=partes[1], rodada_id=str(dados["rodada_id"]), t_ms=int(dados["t_ms"]))
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def sessao_da_rodada(arquivo_sessao: Optional[str], rodada_id: str) -> str:
    """Nome usado como sessão no recorte: o CSV da placa ou, sem ele, o id da rodada."""
    return arquivo_sessao or f"{rodada_id}.csv"


def ultima_leitura_ms(con, rodada_id: str) -> Optional[int]:
    """``t_ms`` da leitura mais recente já gravada da rodada."""
    linha = con.execute("SELECT max(t_ms) FROM leituras WHERE rodada_id = %s", (rodada_id,)).fetchone()
    return None if linha is None or linha[0] is None else int(linha[0])


def classificar_sopro(con, fim: FimDeSopro, model_path: Path, aviso: str = "") -> dict[str, Any]:
    """Classifica o sopro que terminou em ``fim`` e grava o resultado no banco.

    ``aviso`` vai junto do ``detalhe`` (por exemplo, janela incompleta).
    """
    rodada = con.execute("SELECT arquivo_sessao FROM rodadas WHERE id = %s", (fim.rodada_id,)).fetchone()
    sessao = sessao_da_rodada(rodada[0] if rodada else None, fim.rodada_id)
    inicio = (fim.inicio_ms,) if fim.inicio_ms is not None else con.execute(
        """
        SELECT t_ms FROM eventos
        WHERE rodada_id = %s AND tipo = 'sopro_inicio' AND t_ms <= %s
          AND NOT EXISTS (
              SELECT 1 FROM eventos f
              WHERE f.rodada_id = eventos.rodada_id AND f.tipo = 'sopro_fim'
                AND f.t_ms >= eventos.t_ms AND f.t_ms < %s)
        ORDER BY t_ms DESC LIMIT 1
        """,
        (fim.rodada_id, fim.t_ms, fim.t_ms),
    ).fetchone()
    with con.cursor() as cur:
        cur.execute(
            """
            SELECT amostra, t_ms, mq3_raw, ppm, mq135_raw, mq135_mv,
                   temperature_c, humidity_pct, alcool
            FROM leituras WHERE rodada_id = %s ORDER BY t_ms, amostra
            """,
            (fim.rodada_id,),
        )
        colunas = [c.name for c in cur.description]
        leituras = [dict(zip(colunas, linha)) for linha in cur.fetchall()]

    resultado = montar_resultado(
        sessao,
        None if inicio is None else {"t_ms": inicio[0], "attempt_id": None},
        fim.t_ms,
        leituras,
        Path(model_path),
    )
    resultado = {"rodada_id": fim.rodada_id, "t_ms": fim.t_ms, **resultado}
    if aviso:
        resultado["detalhe"] = "; ".join(parte for parte in (aviso, resultado.get("detalhe")) if parte)
    con.execute(
        """
        INSERT INTO resultados (rodada_id, t_ms, attempt_id, status, prediction,
                                prob_sem_efeito, prob_sob_efeito, detalhe)
        VALUES (%(rodada_id)s, %(t_ms)s, %(attempt_id)s, %(status)s, %(prediction)s,
                %(prob_sem_efeito)s, %(prob_sob_efeito)s, %(detalhe)s)
        ON CONFLICT (rodada_id, t_ms) DO NOTHING
        """,
        resultado,
    )
    return resultado


class ServidorAoVivo:
    """Agenda e executa a classificação de cada ``sopro_fim``.

    As dependências entram pelo construtor para os testes trocarem o banco, o
    broker e o relógio. Um ``sopro_fim`` repetido (reentrega do QoS 1) é
    classificado uma vez só. Se o banco cair, reconecta e tenta de novo.
    """

    def __init__(
        self,
        conectar: Callable[[], Any],
        model_path: Path,
        publicar: Callable[[str, str], None],
        agendar: Callable[..., None],
        classificar: Callable[..., dict[str, Any]] = classificar_sopro,
        ultima_leitura_ms: Callable[[Any, str], Optional[int]] = ultima_leitura_ms,
    ) -> None:
        self._conectar = conectar
        self._con = conectar()
        self._model_path = Path(model_path)
        self._publicar = publicar
        self._agendar = agendar
        self._classificar = classificar
        self._ultima_leitura_ms = ultima_leitura_ms
        self._trava = threading.Lock()  # uma conexão de banco, um timer de cada vez
        self._vistos: set[tuple[str, int]] = set()
        self._marcadas: set[str] = set()  # rodadas com sopro marcado: sem modelo contínuo
        self._proxima_janela: dict[str, int] = {}  # rodada -> início da próxima janela
        self._seguidos: dict[str, int] = {}  # rodada -> janelas sob_efeito seguidas

    def ao_receber(self, topico: str, corpo: bytes) -> None:
        """Recebe uma mensagem do broker e agenda o que precisa ser classificado."""
        partes = topico.split("/")
        if len(partes) == 3 and partes[0] == "mq3" and partes[2] == "leituras":
            for janela in self._janelas_prontas(partes[1], corpo):
                self._agendar(CONTINUO_ESPERA_S, self._executar, janela, 0)
            return
        self._anotar_marcacao(topico, corpo)
        fim = fim_de_sopro(topico, corpo)
        if fim is None:
            return
        with self._trava:
            chave = (fim.rodada_id, fim.t_ms)
            if chave in self._vistos:
                return
            self._vistos.add(chave)
        self._agendar(ESPERA_APOS_SOPRO_S, self._executar, fim, 0)

    def _anotar_marcacao(self, topico: str, corpo: bytes) -> None:
        """Rodada com ``sopro_inicio``/``sopro_fim``: vale a marcação, o contínuo para."""
        if not topico.endswith("/eventos"):
            return
        try:
            dados = json.loads(corpo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if isinstance(dados, dict) and dados.get("tipo") in ("sopro_inicio", "sopro_fim") and dados.get("rodada_id"):
            with self._trava:
                self._marcadas.add(str(dados["rodada_id"]))
                self._proxima_janela.pop(str(dados["rodada_id"]), None)

    def _janelas_prontas(self, placa: str, corpo: bytes) -> list[FimDeSopro]:
        """Janelas da rodada que já têm os 30 s de "depois" (modelo contínuo)."""
        try:
            dados = json.loads(corpo.decode("utf-8"))
            rodada_id = str(dados["rodada_id"])
            t_ms = int(dados["t_ms"])
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []
        with self._trava:
            if rodada_id in self._marcadas:
                return []
            inicio = self._proxima_janela.get(rodada_id)
            if inicio is None:
                if len(self._proxima_janela) >= MAX_RODADAS_CONTINUAS:
                    self._proxima_janela.pop(next(iter(self._proxima_janela)))
                self._proxima_janela[rodada_id] = t_ms + CONTINUO_BEFORE_MS
                return []
            prontas = []
            while t_ms >= inicio + CONTINUO_SOPRO_MS + CONTINUO_AFTER_MS:
                prontas.append(FimDeSopro(placa, rodada_id, inicio + CONTINUO_SOPRO_MS, inicio_ms=inicio))
                inicio += CONTINUO_PASSO_MS
            self._proxima_janela[rodada_id] = inicio
        # leituras que chegaram atrasadas: classifica só as janelas mais recentes
        return prontas[-CONTINUO_MAX_POR_LEITURA:]

    def _com_alerta(self, fim: FimDeSopro, resultado: dict[str, Any]) -> dict[str, Any]:
        """Acrescenta ``origem``, ``sob_efeito_seguidos`` e ``alerta`` ao resultado."""
        sob = resultado.get("prediction") == "sob_efeito"
        if not fim.continuo:
            return {**resultado, "origem": "marcado", "sob_efeito_seguidos": int(sob), "alerta": sob}
        with self._trava:
            seguidos = self._seguidos.get(fim.rodada_id, 0) + 1 if sob else 0
            self._seguidos[fim.rodada_id] = seguidos
        return {
            **resultado,
            "origem": "continuo",
            "sob_efeito_seguidos": seguidos,
            "alerta": seguidos == ALERTA_JANELAS_SEGUIDAS,  # avisa uma vez por sequência
        }

    def _executar(self, fim: FimDeSopro, esperas: int) -> None:
        try:
            with self._trava:
                resultado = self._com_reconexao(lambda con: self._tentar(con, fim, esperas))
            if resultado is None:
                self._agendar(ESPERA_EXTRA_S, self._executar, fim, esperas + 1)
                return
            resultado = self._com_alerta(fim, resultado)
            self._publicar(f"mq3/{fim.placa}/resultado", json.dumps(resultado, ensure_ascii=False))
            log.info("resultado %s %s: %s %s", fim.placa, fim.rodada_id, resultado["status"], resultado["prediction"])
        except Exception:
            log.exception("falha ao classificar o sopro %s", fim)

    def _tentar(self, con, fim: FimDeSopro, esperas: int) -> Optional[dict[str, Any]]:
        """Classifica, ou devolve ``None`` para esperar mais leituras."""
        ultima = self._ultima_leitura_ms(con, fim.rodada_id)
        completa = ultima is not None and ultima >= fim.t_ms + JANELA_DEPOIS_MS
        if not completa and esperas < MAX_ESPERAS_EXTRAS:
            return None
        aviso = "" if completa else (
            f"a janela depois do sopro estava incompleta (leituras até {(ultima or 0) / 1000:.1f} s)"
        )
        return self._classificar(con, fim, self._model_path, aviso)

    def _com_reconexao(self, operacao: Callable[[Any], Any]) -> Any:
        import psycopg

        try:
            return operacao(self._con)
        except psycopg.OperationalError:
            log.warning("conexão com o banco caiu; reconectando")
            self._con = self._conectar()
            return operacao(self._con)


def main() -> None:
    """Conecta no broker e no banco; classifica cada sopro que termina."""
    import paho.mqtt.client as mqtt

    from mq3mqtt.classificar_http import iniciar_em_fundo
    from mq3mqtt.config import broker_recusou, connect_with_retry, load_settings

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mq3-modelo")

    def agendar(atraso_s: float, funcao, *args) -> None:
        timer = threading.Timer(atraso_s, funcao, args)
        timer.daemon = True
        timer.start()

    # O HTTP da aba Modelo não depende do banco: sobe antes, mesmo com o Postgres fora.
    iniciar_em_fundo(settings.model_path)
    servidor = ServidorAoVivo(
        conectar=lambda: connect_with_retry(settings.database_url, attempts=0),
        model_path=settings.model_path,
        publicar=lambda topico, corpo: cliente.publish(topico, corpo, qos=1),
        agendar=agendar,
    )

    def ao_conectar(cli, _userdata, _flags, codigo, _props) -> None:
        if broker_recusou(codigo):
            log.error("broker recusou a conexão: %s", codigo)
            return
        cli.subscribe([("mq3/+/eventos", 1), ("mq3/+/leituras", 1)])
        log.info("assinando mq3/+/eventos e mq3/+/leituras")

    cliente.on_connect = ao_conectar
    cliente.on_message = lambda _cli, _userdata, mensagem: servidor.ao_receber(mensagem.topic, mensagem.payload)
    cliente.connect_async(settings.mqtt_host, settings.mqtt_port)
    cliente.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
