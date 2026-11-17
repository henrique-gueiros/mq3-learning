# Coleta: da placa ao dashboard

Leva cada leitura da ESP32 até o MQTT, grava no PostgreSQL e mostra no
Grafana Cloud, sem mudar o que o pipeline de ML lê.

```text
ESP32 --USB--> ponte (notebook) --MQTT--> Mosquitto --> ingestor --> PostgreSQL ─┐
                 ├─> CSV em ml/data/raw/sessions/        └───────────────────────┼─ agente PDC ══> Grafana Cloud
                 └─> linhas em ml/data/raw/attempts.csv                           │
simulador ------MQTT-----^          importador ------------> PostgreSQL ──────────┘
```

| Peça | Onde roda | O que faz |
| --- | --- | --- |
| `coleta.ponte` | notebook (`ml/.venv`) | Lê a serial, grava o CSV de sessão, publica no MQTT e completa o `attempts.csv` |
| Mosquitto, PostgreSQL, ingestor | Docker Compose | Broker, banco e gravação das mensagens |
| `api` | Docker Compose (`127.0.0.1:8000`) | API somente leitura com os dados dos gráficos da tela (`api/`) |
| `pdc` | Docker Compose (perfil `cloud`) | Túnel até o Grafana Cloud |
| `coleta.simulador` | notebook | Publica um CSV real como se a placa estivesse ligada |
| `coleta.importador` | notebook | Grava no banco um CSV feito sem a ponte |

A ponte roda fora do Docker porque o Docker no macOS não enxerga a porta USB.

## Preparar (uma vez)

```bash
cd ml && python3 -m venv .venv && source .venv/bin/activate   # se ainda não existir
pip install -r requirements.txt -r ../applications/coleta/requirements.txt -r ../applications/api/requirements.txt
cd .. && cp .env.example .env    # troque as senhas
docker compose up -d --build
```

Para ligar ao Grafana Cloud, siga [`grafana/README.md`](grafana/README.md) e
depois use `docker compose --profile cloud up -d`.

## Dia de coleta

1. Ligue a placa no USB e descubra a porta: `ls /dev/cu.*`
   (algo como `/dev/cu.usbserial-0001`). Feche o `pio device monitor`: a
   porta serial aceita um programa por vez.
2. Suba a infraestrutura: `docker compose up -d` (ou com `--profile cloud`).
3. Para cada rodada, de dentro de `applications/`:

   ```bash
   python -m coleta.ponte --porta /dev/cu.usbserial-0001 --caso perfume --participante p01 --duracao 120
   ```

   - **Enter** quando a pessoa começa a soprar; **f** + Enter quando para.
   - A rodada termina sozinha depois de `--duracao` segundos de leituras
     (todas do mesmo tamanho). **Ctrl+C** encerra antes.
   - Casos aceitos: os de `CONDITIONS` em `ml/src/data_validation.py`
     (`clean`, `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash`,
     `drink`). Outro nome é recusado.
   - Se a placa reiniciar no meio, a ponte fecha a rodada e abre outra com o
     mesmo caso, num CSV novo.
   - Se o broker cair, a ponte avisa e continua gravando o CSV.
4. No fim, confira os arquivos para o ML:

   ```bash
   cd ../ml && python -m src.cli validate
   ```

Cada rodada gera `ml/data/raw/sessions/AAAA-MM-DD_<participante>_<caso>_<n>.csv`
e uma linha por sopro em `ml/data/raw/attempts.csv`.

## Sem a placa

```bash
python -m coleta.simulador ../esp32-esp8266/leituras.csv --caso clean --participante p00 --sopros 20
```

As rodadas do simulador saem com origem `simulador` e ficam fora das
comparações do dashboard (variável **Incluir simulador** = `nao`).

## CSV gravado sem a ponte

```bash
python -m coleta.importador ../ml/data/raw/sessions/arquivo.csv --caso perfume --participante p01
```

Os sopros vêm das linhas do `attempts.csv` com o mesmo `session_file`. O
importador recusa um arquivo já importado e um arquivo que o `attempts.csv`
associa a outra condição. A cópia que a placa grava na própria memória
(LittleFS) só deve ser importada quando a rodada não passou pela ponte; senão
os dados entram duas vezes.

## Ver o dashboard sem o Grafana Cloud

O Compose tem um Grafana local, no perfil `local`, já ligado ao banco e com o
dashboard `coleta`. Não use junto com o Compose de `services/` (mesmas portas).

```bash
docker compose --profile local up -d --build
```

Abra http://localhost:3000. Usuário `admin`; a senha é `GRAFANA_ADMIN_SENHA` do
`.env` (padrão `admin` quando a variável não existe; o Grafana só escuta em
`127.0.0.1`). Os data sources e o dashboard vêm de `grafana/provisioning/` e
`grafana/dashboards/`, e as edições feitas na interface não são salvas: exporte o
JSON como descrito em `grafana/README.md`.

## API da tela

A tela em React (em construção, substituirá o Grafana) lê os gráficos de análise
pela API e as leituras ao vivo direto do Mosquitto, por WebSocket (porta 9001, só
em `127.0.0.1`). A API roda as mesmas consultas do dashboard do Grafana com o
usuário só leitura, e os filtros vão na query string:

```bash
curl 'http://localhost:8000/api/resumo?caso=drink&caso=perfume&janela=sopro'
```

A lista de rotas está em http://localhost:8000/api/docs. Para rodar fora do
Docker, de `applications/`: `uvicorn api.app:app --reload`.

## CSVs já coletados

`dados/lote-2026-11.csv` lista os 12 CSVs válidos (bateria de 12/11 em diante),
com o nome que cada sessão recebe em `ml/data/raw/sessions/`, o caso e o
participante (`equipe`, porque não se sabe quem soprou em cada arquivo). Para copiar
e importar tudo de uma vez, com o Compose de pé:

```bash
python -m coleta.lote
```

É seguro repetir: arquivo igual é aceito e sessão já importada é só contada. Sem
`attempts.csv` os sopros não estão marcados, então os painéis "Subida por sopro" e
"Janela de sopro" ficam vazios e todas as rodadas aparecem em "Rodadas sem sopro
marcado".

O firmware já gravou CSVs com 9, 11 e 13 colunas; os três formatos são aceitos
pela ponte e pelo importador.

## Testes

```bash
cd applications && python -m pytest
```

Os testes de banco são pulados sem `PG_DSN`. Para rodá-los:

```bash
docker run --rm -d --name pg-teste -e POSTGRES_PASSWORD=t -p 55432:5432 postgres:16
PG_DSN=postgresql://postgres:t@localhost:55432/postgres python -m pytest
docker stop pg-teste
```

## Limitações

- Não suba junto o Compose de `services/` (Henrique): as portas 1883 e 5432
  coincidem, e o Grafana dele usa 3000 e 9001. Na coleta, só este roda.
- O Mosquitto aceita conexões sem senha: use só na rede local da coleta.
- O dashboard só tem dados enquanto o Compose (com o perfil `cloud`) estiver
  rodando em alguma máquina.
- O painel ao vivo depende do plugin MQTT funcionar pelo PDC na stack; se
  não funcionar, veja a alternativa em `grafana/README.md`.
- Mensagens publicadas enquanto o broker está fora do ar não chegam ao banco;
  o CSV da rodada fica completo. Se a rodada não chegou ao banco, importe o CSV.
