import re
from pathlib import Path

from platformio.public import DeviceMonitorFilterBase  # pyright: ignore[reportMissingImports]

PASTA = Path(__file__).resolve().parents[1] / "leituras"
CABECALHO = (
    "amostra,t_ms,mq3_raw,ppm,rs,rs_rsar,mq135_raw,mq135_mv,"
    "temperature_c,humidity_pct,alcool,tensao_atual_mv,tensao_referencia_mv\n"
)
NOME_OK = re.compile(r"leituras_\d+\.csv\Z")


class LeiturasFilter(DeviceMonitorFilterBase):
    NAME = "leituras"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffer = ""
        self._caminho_atual = None

    def _caminho(self, nome):
        if NOME_OK.fullmatch(nome) is None:
            return None
        return PASTA / nome

    def _proximo_livre(self):
        numero = 1
        while True:
            caminho = PASTA / f"leituras_{numero}.csv"
            if not caminho.exists():
                return caminho
            numero += 1

    def _comecar(self, nome):
        caminho = self._caminho(nome)
        if caminho is None or caminho.exists():
            caminho = self._proximo_livre()
        self._caminho_atual = caminho
        with caminho.open("w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(CABECALHO)

    def rx(self, text):
        self._buffer += text
        while "\n" in self._buffer:
            linha, self._buffer = self._buffer.split("\n", 1)
            linha = linha.rstrip("\r")
            if linha.startswith("CSV_ARQUIVO,"):
                self._comecar(linha[len("CSV_ARQUIVO,") :])
            elif linha.startswith("CSV_LINHA,"):
                nome, separador, dados = linha[len("CSV_LINHA,") :].partition(",")
                if not separador:
                    continue
                if self._caminho_atual is None:
                    self._comecar(nome)
                with self._caminho_atual.open("a", encoding="utf-8", newline="\n") as arquivo:
                    arquivo.write(dados + "\n")
        return text
