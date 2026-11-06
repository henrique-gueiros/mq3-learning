"""Publica o dashboard versionado na stack do Grafana Cloud.

Uso, da raiz do repositório::

    python applications/grafana/publicar.py

Lê ``GRAFANA_URL`` e ``GRAFANA_TOKEN`` do ambiente ou do ``.env`` da raiz. O
token é de uma service account com papel Editor. Publicar de novo sobrescreve
o dashboard (mesmo uid), então edições feitas só na interface se perdem:
exporte o JSON para ``dashboards/`` antes de publicar.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ENV_REPOSITORIO = PASTA.parents[1] / ".env"
DASHBOARD = PASTA / "dashboards" / "coleta.json"


def _ler_env(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    valores = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, _, valor = linha.partition("=")
            valores[chave.strip()] = valor.strip()
    return valores


def _configuracao() -> tuple:
    env = _ler_env(ENV_REPOSITORIO)
    url = os.environ.get("GRAFANA_URL") or env.get("GRAFANA_URL", "")
    token = os.environ.get("GRAFANA_TOKEN") or env.get("GRAFANA_TOKEN", "")
    return url.rstrip("/"), token


def main() -> int:
    url, token = _configuracao()
    if not url or not token:
        print("Defina GRAFANA_URL e GRAFANA_TOKEN no .env (veja applications/grafana/README.md).", file=sys.stderr)
        return 1

    corpo = json.dumps({"dashboard": json.loads(DASHBOARD.read_text(encoding="utf-8")), "overwrite": True})
    pedido = urllib.request.Request(
        f"{url}/api/dashboards/db",
        data=corpo.encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=30) as resposta:
            resultado = json.load(resposta)
    except urllib.error.HTTPError as erro:
        print(f"O Grafana recusou o dashboard ({erro.code}): {erro.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 1
    except urllib.error.URLError as erro:
        print(f"Não consegui falar com {url}: {erro.reason}", file=sys.stderr)
        return 1

    print(f"Dashboard publicado: {url}{resultado.get('url', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
