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
| `pdc` | Docker Compose (perfil `cloud`) | Túnel até o Grafana Cloud |
| `coleta.simulador` | notebook | Publica um CSV real como se a placa estivesse ligada |
| `coleta.importador` | notebook | Grava no banco um CSV feito sem a ponte |

A ponte roda fora do Docker porque o Docker no macOS não enxerga a porta USB.

## Preparar (uma vez)

```bash
cd ml && python3 -m venv .venv && source .venv/bin/activate   # se ainda não existir
pip install -r requirements.txt -r ../applications/coleta/requirements.txt
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
python -m coleta.simulador ../firmware/leituras.csv --caso clean --participante p00 --sopros 20
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

- O Mosquitto aceita conexões sem senha: use só na rede local da coleta.
- O dashboard só tem dados enquanto o Compose (com o perfil `cloud`) estiver
  rodando em alguma máquina.
- O painel ao vivo depende do plugin MQTT funcionar pelo PDC na stack; se
  não funcionar, veja a alternativa em `grafana/README.md`.
- Mensagens publicadas enquanto o broker está fora do ar não chegam ao banco;
  o CSV da rodada fica completo. Se a rodada não chegou ao banco, importe o CSV.
