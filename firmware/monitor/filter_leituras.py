from pathlib import Path

from platformio.public import DeviceMonitorFilterBase

ARQUIVO_CSV = Path(__file__).resolve().parents[1] / "leituras.csv"
CABECALHO = (
    "amostra,t_ms,mq3_raw,ppm,mq135_raw,mq135_mv,"
    "temperature_c,humidity_pct,alcool\n"
)


class LeiturasFilter(DeviceMonitorFilterBase):
    NAME = "leituras"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffer = ""
        self._garantir_cabecalho()

    def _garantir_cabecalho(self):
        if ARQUIVO_CSV.exists() and ARQUIVO_CSV.stat().st_size > 0:
            return
        with ARQUIVO_CSV.open("w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(CABECALHO)

    def rx(self, text):
        self._buffer += text
        while "\n" in self._buffer:
            linha, self._buffer = self._buffer.split("\n", 1)
            linha = linha.rstrip("\r")
            if linha.startswith("CSV_LINHA,"):
                with ARQUIVO_CSV.open("a", encoding="utf-8", newline="\n") as arquivo:
                    arquivo.write(linha[len("CSV_LINHA,") :] + "\n")
        return text
