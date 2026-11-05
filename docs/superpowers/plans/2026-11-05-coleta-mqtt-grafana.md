# Coleta → MQTT → PostgreSQL → Grafana Cloud — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levar cada leitura da ESP32 (via serial no notebook) até o MQTT, gravar no PostgreSQL e exibir ao vivo e comparada por caso no Grafana Cloud, sem mudar o que o pipeline de ML lê.

**Architecture:** Um pacote Python `coleta` (em `applications/`) contém funções puras (parse da serial, mensagens, estado da rodada) e quatro programas: `ponte` (host, serial → MQTT + CSV + attempts.csv), `ingestor` (contêiner, MQTT → PostgreSQL), `simulador` e `importador`. Toda a lógica das médias, janelas e subidas fica em views SQL no `init.sql`, para que os painéis do Grafana façam só `SELECT` simples. O Docker Compose sobe Mosquitto, PostgreSQL, ingestor e o agente PDC, que liga a rede local à stack do Grafana Cloud.

**Tech Stack:** Python ≥ 3.9 (`from __future__ import annotations`), pyserial, paho-mqtt 2.x, psycopg 3, pytest; PostgreSQL 16; Eclipse Mosquitto 2; `grafana/pdc-agent`; Grafana Cloud (free) com `grafana-mqtt-datasource` e `volkovlabs-echarts-panel`.

**Spec:** `docs/superpowers/specs/2026-11-05-coleta-mqtt-grafana-design.md`

## Global Constraints

- Não mudar o formato de `ml/data/raw/sessions/*.csv` nem de `ml/data/raw/attempts.csv`; nunca editar CSV bruto já gravado.
- CSV de sessão: cabeçalho exato `amostra,t_ms,mq3_raw,ppm,mq135_raw,mq135_mv,temperature_c,humidity_pct,alcool`; `t_ms` da placa sem alteração.
- Nome do CSV de sessão: `AAAA-MM-DD_<participante>_<caso>_<n>.csv`, `n` = menor inteiro ≥ 1 ainda livre na pasta.
- Casos aceitos = chaves de `CONDITIONS` em `ml/src/data_validation.py` (fonte única; não copiar a lista).
- `ppm` e `alcool` são gravados, mas nenhuma view de comparação os expõe.
- Gravação idempotente: chave primária (`rodada_id`, `amostra`) em `leituras`; eventos únicos por (`rodada_id`, `tipo`, `t_ms`).
- Janelas: 15 s antes do sopro (linha de base = **mediana**), sopro = até `sopro_fim` ou 5 s, depois 30 s. Valores de `ml/src/features.py`.
- Tópicos: `mq3/<placa>/{rodada,leituras,eventos,status}`, `<placa>` padrão `placa01`; `rodada` e `status` retidos; `status` com last will `offline`.
- Ponte: broker fora do ar nunca interrompe a gravação do CSV.
- Credenciais só em `.env` (ignorado pelo Git); versionar só `.env.example`.
- Python roda no `ml/.venv` no host; só o ingestor tem Dockerfile.
- Comentários, mensagens de terminal e documentação em português, no estilo didático do `ml/`.

## Review Focus

1. **Placa reinicia ao abrir a serial**: o primeiro `CSV_ARQUIVO` chega antes de qualquer leitura; não pode gerar rodada vazia nem CSV vazio. Teste em Task 3.
2. **Broker fora do ar** no início ou no meio da rodada: a ponte continua gravando CSV e avisa. Teste em Task 4.
3. **Enter antes da primeira leitura**: não há `t_ms`; o sopro é ignorado com aviso. Teste em Task 3.
4. **Linhas de serial quebradas** (lixo do boot, linha cortada, bytes não UTF-8, DHT vazio): ignoradas ou viram `None`, nunca derrubam a ponte. Teste em Task 1.
5. **Mensagem MQTT repetida ou ingestor reiniciado**: nada duplica no banco; leitura que chega antes da mensagem `rodada` não se perde. Teste em Task 6.

---

## Estrutura de arquivos

```text
docker-compose.yml                    # Task 6 (mosquitto, postgres, ingestor), Task 8 (pdc)
.env.example                          # Task 6, completado na Task 8
.gitignore                            # Task 6: acrescentar .env
applications/
├── README.md                         # Task 9
├── pytest.ini                        # Task 1
├── coleta/
│   ├── __init__.py
│   ├── requirements.txt              # Task 1
│   ├── Dockerfile                    # Task 6
│   ├── serial_proto.py               # Task 1: parse das linhas da serial
│   ├── casos.py                      # Task 2: CASOS lidos de ml/src/data_validation.py
│   ├── mensagens.py                  # Task 2: tópicos e payloads JSON
│   ├── rodada.py                     # Task 3: estado da rodada (puro)
│   ├── arquivos.py                   # Task 3: CSV de sessão e attempts.csv
│   ├── publicador.py                 # Task 4: cliente MQTT resiliente
│   ├── ponte.py                      # Task 4: CLI da ponte
│   ├── config.py                     # Task 4: variáveis de ambiente
│   ├── banco.py                      # Task 5: acesso ao PostgreSQL
│   ├── ingestor.py                   # Task 6
│   ├── simulador.py                  # Task 7
│   ├── importador.py                 # Task 7
│   └── tests/
│       ├── conftest.py               # Task 5: fixture `pg` (pula sem PG_DSN)
│       ├── test_serial_proto.py  test_mensagens.py  test_rodada.py  test_arquivos.py
│       ├── test_publicador.py  test_banco.py  test_ingestor.py  test_importador.py
├── mosquitto/mosquitto.conf          # Task 6
├── db/
│   ├── 01-schema.sql                 # Task 5: tabelas e views
│   └── 02-leitor.sh                  # Task 5: usuário só leitura para o Grafana
├── pdc/README.md                     # Task 8
└── grafana/
    ├── README.md                     # Task 8: configurar a stack (data sources, plugins)
    ├── dashboards/coleta.json        # Task 8
    └── publicar.py                   # Task 8
AGENTS.md                             # Task 9
```

Testes rodam de `applications/`: `python -m pytest`. Os de banco são marcados `integracao` e pulam quando `PG_DSN` não está definido.

---

### Task 1: Pacote e protocolo da serial

**Files:**
- Create: `applications/pytest.ini`, `applications/coleta/__init__.py`, `applications/coleta/requirements.txt`, `applications/coleta/serial_proto.py`
- Test: `applications/coleta/tests/__init__.py`, `applications/coleta/tests/test_serial_proto.py`

**Interfaces:**
- Produces:
  - `COLUNAS_FIRMWARE: tuple[str, ...]` = as 9 colunas do cabeçalho, na ordem.
  - `@dataclass(frozen=True) class Leitura: amostra: int; t_ms: int; mq3_raw: int; ppm: float | None; mq135_raw: int | None; mq135_mv: int | None; temperature_c: float | None; humidity_pct: float | None; alcool: int | None` com `def como_linha_csv(self) -> str` (campo `None` → vazio; floats como chegaram, sem reformatar) e `def como_dict(self) -> dict`.
  - `@dataclass(frozen=True) class ArquivoNovo: nome: str`
  - `def ler_linha(bruta: bytes | str) -> Leitura | ArquivoNovo | None`

- [ ] **Step 1: Write the failing tests** (`test_serial_proto.py`)

```python
LINHA = "CSV_LINHA,leituras_3.csv,40,2940,1232,0.4,451,525,36.3,49.4,0"

def test_leitura_completa():
    l = ler_linha(LINHA)
    assert l == Leitura(40, 2940, 1232, 0.4, 451, 525, 36.3, 49.4, 0)

def test_dht_vazio_vira_none():
    l = ler_linha("CSV_LINHA,leituras_3.csv,38,811,1222,0.4,462,514,,,0")
    assert l.temperature_c is None and l.humidity_pct is None

def test_arquivo_novo():
    assert ler_linha("CSV_ARQUIVO,leituras_4.csv\r\n") == ArquivoNovo("leituras_4.csv")

def test_linhas_ignoradas():
    for lixo in ["Leitura: 1232  ppm: 0.4", "", "CSV_LINHA,leituras_3.csv,40,29", b"\xff\xfe\x00", "CSV_LINHA,x.csv,a,b,c,d,e,f,g,h,i"]:
        assert ler_linha(lixo) is None

def test_bytes_aceitos():
    assert ler_linha(LINHA.encode()) == ler_linha(LINHA)

def test_ida_e_volta_csv():
    l = ler_linha("CSV_LINHA,leituras_3.csv,38,811,1222,0.4,462,514,,,0")
    assert l.como_linha_csv() == "38,811,1222,0.4,462,514,,,0"
```

Para `como_linha_csv` reproduzir exatamente o que chegou, guarde em `Leitura` um campo extra `bruta: str = field(default="", compare=False, repr=False)` com o trecho depois do nome do arquivo, e use-o quando não estiver vazio.

- [ ] **Step 2:** `cd applications && python -m pytest coleta/tests/test_serial_proto.py -v` → FAIL (módulo não existe).
- [ ] **Step 3: Implement `serial_proto.py`.** Bytes decodificados com `errors="replace"`; linha com qualquer `�`, número de campos ≠ 9 ou campo obrigatório (`amostra`, `t_ms`, `mq3_raw`) não numérico → `None`. `pytest.ini`: `[pytest]`, `pythonpath = .`, `testpaths = coleta/tests`, `markers = integracao: precisa de PostgreSQL (PG_DSN)`. `requirements.txt`: `pyserial>=3.5`, `paho-mqtt>=2.1`, `psycopg[binary]>=3.2`, `pytest>=8.0`.
- [ ] **Step 4:** mesmo comando → PASS. Conferir também que todas as linhas de `firmware/leituras.csv` prefixadas com `CSV_LINHA,leituras_1.csv,` são aceitas e voltam idênticas por `como_linha_csv` (teste `test_amostra_real_ida_e_volta`, lendo o arquivo pelo caminho relativo ao repositório).
- [ ] **Step 5: Commit** `feat(coleta): parse das linhas da serial do firmware`

---

### Task 2: Casos e mensagens MQTT

**Files:**
- Create: `applications/coleta/casos.py`, `applications/coleta/mensagens.py`
- Test: `applications/coleta/tests/test_mensagens.py`

**Interfaces:**
- Consumes: `Leitura.como_dict()` (Task 1).
- Produces:
  - `casos.CASOS: frozenset[str]`: carrega `ml/src/data_validation.py` com `importlib.util.spec_from_file_location` (caminho a partir de `Path(__file__).resolve().parents[2] / "ml" / "src" / "data_validation.py"`) e pega `CONDITIONS.keys()`. No contêiner do ingestor o arquivo não existe e `CASOS` não é usado; importe `casos` só na ponte, no simulador e no importador.
  - `casos.validar_caso(caso: str) -> str`: devolve o caso ou levanta `ValueError` com a lista de casos aceitos.
  - `mensagens.topico(placa: str, tipo: str) -> str` → `"mq3/<placa>/<tipo>"`; `tipo` ∈ `{"rodada","leituras","eventos","status"}`, outro → `ValueError`.
  - `mensagens.payload_rodada(rodada_id: str, placa: str, caso: str, participante: str, inicio: datetime, arquivo_sessao: str, origem: str) -> dict` (`inicio` em ISO 8601 com fuso; `origem` ∈ `{"ponte","simulador"}`)
  - `mensagens.payload_leitura(rodada_id: str, leitura: Leitura) -> dict` (os 9 campos + `rodada_id`)
  - `mensagens.payload_evento(rodada_id: str, tipo: str, t_ms: int, sha256: str | None = None) -> dict` (`tipo` ∈ `{"sopro_inicio","sopro_fim","rodada_fim"}`; `sha256` só em `rodada_fim`)
  - `mensagens.codificar(payload: dict) -> bytes` / `mensagens.decodificar(dados: bytes) -> dict` (JSON UTF-8; `decodificar` levanta `ValueError` em JSON inválido)

- [ ] **Step 1: Write the failing tests**

```python
def test_topicos():
    assert topico("placa01", "leituras") == "mq3/placa01/leituras"
    with pytest.raises(ValueError): topico("placa01", "outro")

def test_leitura_com_dht_vazio_vira_null():
    l = ler_linha("CSV_LINHA,a.csv,38,811,1222,0.4,462,514,,,0")
    d = decodificar(codificar(payload_leitura("r1", l)))
    assert d["rodada_id"] == "r1" and d["temperature_c"] is None and d["t_ms"] == 811

def test_evento_tipo_invalido():
    with pytest.raises(ValueError): payload_evento("r1", "outro", 10)

def test_casos_vem_do_ml():
    assert "perfume" in CASOS and "drink" in CASOS
    with pytest.raises(ValueError): validar_caso("vodka")
```

- [ ] **Step 2:** rodar → FAIL. **Step 3:** implementar. **Step 4:** rodar → PASS.
- [ ] **Step 5: Commit** `feat(coleta): tópicos e mensagens MQTT`

---

### Task 3: Estado da rodada e arquivos

**Files:**
- Create: `applications/coleta/rodada.py`, `applications/coleta/arquivos.py`
- Test: `applications/coleta/tests/test_rodada.py`, `applications/coleta/tests/test_arquivos.py`

**Interfaces:**
- Consumes: `Leitura`, `ArquivoNovo` (Task 1).
- Produces:
  - `@dataclass class Sopro: inicio_ms: int; fim_ms: int | None = None`
  - `class Rodada` (pura, sem I/O):
    - `Rodada(caso: str, participante: str, duracao_s: float | None)`
    - `.id: str` (uuid4), `.leituras: int`, `.sopros: list[Sopro]`, `.ultimo_t_ms: int | None`
    - `.receber(evento: Leitura | ArquivoNovo) -> str`: devolve `"leitura"`, `"ignorar"` ou `"reiniciou"`. `ArquivoNovo` ou `amostra` ≤ última amostra **quando já houve leitura** → `"reiniciou"`; `ArquivoNovo` antes da primeira leitura → `"ignorar"`.
    - `.marcar_inicio_sopro() -> Sopro | None` (sem leitura ainda → `None`); `.marcar_fim_sopro() -> Sopro | None` (sem sopro aberto → `None`).
    - `.terminou() -> bool`: `duracao_s` definida e `ultimo_t_ms - primeiro_t_ms >= duracao_s * 1000`.
  - `arquivos.nome_sessao(pasta: Path, data: date, participante: str, caso: str) -> Path`
  - `class arquivos.CsvSessao`: `CsvSessao(caminho: Path)` cria com o cabeçalho; `.escrever(leitura: Leitura) -> None` (append + flush); `.fechar() -> str` devolve SHA-256 hex do arquivo. Arquivo sem nenhuma leitura é apagado em `fechar()` e devolve `""`.
  - `arquivos.linhas_attempts(rodada: Rodada, arquivo_sessao: str, data: date, n: int) -> list[dict]`: uma por sopro; `attempt_id = f"{data:%Y-%m-%d}_{participante}_{caso}_{n}_s{k}"` (k a partir de 1), `blow_start_s = inicio_ms / 1000`, `blow_end_s = fim_ms / 1000` ou vazio, `reference_mg_l` e `notes` vazios.
  - `arquivos.anexar_attempts(caminho: Path, linhas: list[dict]) -> None`: cria com o cabeçalho de `ml/templates/attempts_template.csv` se não existir; senão só acrescenta.

- [ ] **Step 1: Write the failing tests** (leituras feitas com um helper `leitura(amostra, t_ms)`)

```python
def test_arquivo_novo_antes_da_primeira_leitura_e_ignorado():
    r = Rodada("perfume", "p01", None)
    assert r.receber(ArquivoNovo("leituras_2.csv")) == "ignorar"
    assert r.receber(leitura(1, 800)) == "leitura"

def test_reinicio_no_meio():
    r = Rodada("perfume", "p01", None); r.receber(leitura(10, 9000))
    assert r.receber(leitura(1, 800)) == "reiniciou"
    assert r.receber(ArquivoNovo("x.csv")) == "reiniciou"

def test_sopro_sem_leitura_e_ignorado():
    assert Rodada("perfume", "p01", None).marcar_inicio_sopro() is None

def test_sopro_usa_ultimo_t_ms():
    r = Rodada("perfume", "p01", None); r.receber(leitura(5, 20400))
    assert r.marcar_inicio_sopro() == Sopro(20400)
    r.receber(leitura(6, 25500)); assert r.marcar_fim_sopro() == Sopro(20400, 25500)

def test_duracao():
    r = Rodada("clean", "p01", 120); r.receber(leitura(1, 1000)); r.receber(leitura(2, 120999))
    assert not r.terminou(); r.receber(leitura(3, 121000)); assert r.terminou()

def test_nome_sessao_pula_existentes(tmp_path):
    (tmp_path / "2026-11-05_p01_perfume_1.csv").touch()
    assert nome_sessao(tmp_path, date(2026, 11, 5), "p01", "perfume").name == "2026-11-05_p01_perfume_2.csv"

def test_csv_sessao_formato_e_hash(tmp_path):
    c = CsvSessao(tmp_path / "s.csv"); c.escrever(ler_linha(LINHA)); h = c.fechar()
    assert (tmp_path / "s.csv").read_text() == CABECALHO + "40,2940,1232,0.4,451,525,36.3,49.4,0\n"
    assert len(h) == 64

def test_csv_vazio_e_apagado(tmp_path):
    c = CsvSessao(tmp_path / "s.csv"); assert c.fechar() == "" and not (tmp_path / "s.csv").exists()

def test_attempts_cria_com_cabecalho_e_acrescenta(tmp_path):
    ...  # duas chamadas → 1 cabeçalho + 2 linhas; colunas == cabeçalho do template; blow_start_s == "20.4"
```

- [ ] **Step 2:** rodar → FAIL. **Step 3:** implementar. **Step 4:** rodar → PASS.
- [ ] **Step 5: Commit** `feat(coleta): estado da rodada, CSV de sessão e attempts.csv`

---

### Task 4: Publicador MQTT e CLI da ponte

**Files:**
- Create: `applications/coleta/config.py`, `applications/coleta/publicador.py`, `applications/coleta/ponte.py`
- Test: `applications/coleta/tests/test_publicador.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - `config.Config` (dataclass, `Config.do_ambiente() -> Config`): `mqtt_host` (`MQTT_HOST`, padrão `localhost`), `mqtt_port` (`MQTT_PORT`, 1883), `pg_dsn` (`PG_DSN`, padrão `postgresql://mq3:mq3@localhost:5432/mq3`), `placa` (`PLACA`, `placa01`).
  - `class publicador.Publicador`: `Publicador(host: str, port: int, placa: str)`; `.conectar() -> None` (usa `connect_async` + `loop_start`, last will `offline` retido em `status`; publica `online` retido no `on_connect`); `.publicar(tipo: str, payload: dict, retido: bool = False) -> bool` (devolve `False`, sem levantar, se desconectado); `.conectado: bool`; `.encerrar() -> None` (publica `offline` retido se conectado, para o loop).
  - CLI: `python -m coleta.ponte --porta PORTA --caso CASO --participante ID [--duracao S] [--placa P] [--sessoes PASTA] [--attempts ARQ]`. Padrões: `--sessoes ml/data/raw/sessions`, `--attempts ml/data/raw/attempts.csv` (relativos à raiz do repositório, calculados a partir de `__file__`), 115200 baud.

- [ ] **Step 1: Write the failing tests**

```python
def test_publicar_sem_broker_nao_levanta():
    p = Publicador("127.0.0.1", 1, "placa01"); p.conectar()   # porta 1: ninguém escuta
    assert p.publicar("leituras", {"x": 1}) is False
    p.encerrar()
```

- [ ] **Step 2:** rodar → FAIL. **Step 3:** implementar `config.py` e `publicador.py`. **Step 4:** rodar → PASS.
- [ ] **Step 5: Implement `ponte.py`.** Fluxo do `main(argv: list[str] | None = None) -> int`:
  1. `validar_caso`; abrir a serial; criar `Rodada`, `CsvSessao(nome_sessao(...))`, publicar `rodada` (retido, `origem="ponte"`).
  2. Uma thread lê `stdin`: linha vazia → `marcar_inicio_sopro`, `f` → `marcar_fim_sopro`; cada sopro marcado publica `eventos` e imprime `Sopro 1 às 20.4 s`; `None` imprime o aviso correspondente. Comunicação com o laço principal por `queue.Queue`.
  3. Laço: `ler_linha(serial.readline())`; `"leitura"` → CSV + `leituras`; `"reiniciou"` → encerrar a rodada atual (passo 4) e abrir outra com o mesmo caso e participante, imprimindo `Placa reiniciou: rodada nova <arquivo>`; reprocessar o evento na rodada nova.
  4. Encerrar (por `terminou()`, Ctrl+C ou reinício): `sha = csv.fechar()`; publicar `eventos` `rodada_fim` com `sha256`; `anexar_attempts`; imprimir resumo (arquivo, leituras, sopros, se o broker esteve fora).
  5. Quando `publicar` devolver `False` pela primeira vez numa sequência, imprimir uma vez `Broker fora do ar: continuo gravando o CSV`; ao voltar, `Broker de volta`.
- [ ] **Step 6: Verificação manual** (sem placa, com `socat` ou com a placa real se disponível): `python -m coleta.ponte --help` mostra as opções. Com a placa: rodar 30 s com `--duracao 30`, apertar Enter uma vez, conferir o CSV novo em `ml/data/raw/sessions/`, a linha em `attempts.csv` e `cd ml && python -m src.cli validate` sem erro para esse arquivo.
- [ ] **Step 7: Commit** `feat(coleta): ponte serial → MQTT com CSV e attempts.csv`

---

### Task 5: Esquema do banco e views

**Files:**
- Create: `applications/db/01-schema.sql`, `applications/db/02-leitor.sh`, `applications/coleta/banco.py`, `applications/coleta/tests/conftest.py`
- Test: `applications/coleta/tests/test_banco.py`

**Interfaces:**
- Produces (SQL):
  - `rodadas(id uuid PK, placa text, caso text, participante text, inicio timestamptz, fim timestamptz NULL, arquivo_sessao text, origem text CHECK IN ('ponte','importador','simulador'), sha256 text UNIQUE NULL, notas text NULL)`. Campos além de `id` e `placa` aceitam `NULL` (rodada "esqueleto" criada por leitura que chegou antes da mensagem `rodada`).
  - `leituras(rodada_id uuid FK, amostra int, t_ms bigint, mq3_raw int, ppm real, mq135_raw int, mq135_mv int, temperature_c real, humidity_pct real, alcool smallint, recebido_em timestamptz DEFAULT now(), PRIMARY KEY (rodada_id, amostra))`
  - `eventos(rodada_id uuid FK, tipo text CHECK IN ('sopro_inicio','sopro_fim','rodada_fim'), t_ms bigint, UNIQUE (rodada_id, tipo, t_ms))`
  - `v_leituras`: leituras + `caso`, `participante`, `origem`, `tempo_s = (t_ms - min(t_ms) OVER rodada) / 1000.0`, `ts = inicio + tempo_s * interval '1 second'`, `em_sopro boolean` (dentro de `[inicio_ms, fim_ms + 30000]` de algum sopro de `v_sopros`). Sem `ppm` nem `alcool`.
  - `v_sopros`: um por `sopro_inicio`; `n` (ordem na rodada), `inicio_ms`, `fim_ms` (= primeiro `sopro_fim` > início e < próximo início, senão `inicio_ms + 5000`); para `mq3_raw`, `mq135_raw`, `humidity_pct`, `temperature_c`: `base_*` = mediana (`percentile_cont(0.5)`) em `[inicio_ms - 15000, inicio_ms)`, `pico_*` = máximo em `[inicio_ms, fim_ms + 30000]`, `subida_* = pico_* - base_*`.
  - `v_media_rodada`: uma linha por (rodada, `janela` ∈ `{'arquivo','sopro'}`), com `caso`, `participante`, `origem`, `n_leituras`, `media_*` e `pico_*` dos 4 sensores. Janela `sopro` usa só `em_sopro`; rodada sem sopro tem `n_leituras = 0` e médias `NULL`.
  - `v_rodadas_sem_sopro`: rodadas com `origem` ≠ `simulador` e nenhum `sopro_inicio`.
- Produces (Python, `banco.py`, psycopg 3, cada função recebe uma `psycopg.Connection` e faz commit):
  - `garantir_rodada(con, rodada_id: str, placa: str) -> None` (INSERT … ON CONFLICT DO NOTHING)
  - `gravar_rodada(con, payload_rodada: dict) -> None` (upsert de todos os campos; usado também para completar o esqueleto)
  - `gravar_leitura(con, payload_leitura: dict) -> bool` (ON CONFLICT DO NOTHING; `True` se inseriu)
  - `gravar_evento(con, payload_evento: dict) -> None` (ON CONFLICT DO NOTHING; `rodada_fim` também grava `fim = now()` e `sha256` na rodada)
  - `rodada_por_sha(con, sha256: str) -> str | None`
  - `importar_rodada(con, rodada: dict, leituras: list[dict], sopros: list[tuple[int, int | None]]) -> str` (uma transação)
- `02-leitor.sh`: cria o papel `grafana_leitor` com senha `$GRAFANA_PG_SENHA`, `GRANT SELECT` nas views e tabelas do schema `public`.
- `conftest.py`: fixture `pg` que pula o teste (`pytest.skip`) sem `PG_DSN`; com ele, aplica `01-schema.sql` num schema temporário (`CREATE SCHEMA t_<uuid>`; `SET search_path`) e o derruba ao final.

- [ ] **Step 1: Write the failing tests** (`@pytest.mark.integracao`; dados montados à mão no teste, como em `ml/tests/conftest.py`)

```python
def test_leitura_repetida_nao_duplica(pg): ...  # gravar_leitura 2x → True, False; count == 1
def test_leitura_antes_da_rodada(pg): ...       # garantir_rodada + gravar_leitura, depois gravar_rodada → v_leituras tem caso preenchido
def test_sopro_sem_fim_usa_5s(pg): ...          # sopro_inicio em 20000 → v_sopros.fim_ms == 25000
def test_base_e_mediana(pg): ...                # mq3 antes = [100, 100, 900] → base_mq3_raw == 100
def test_subida(pg): ...                        # pico 600 dentro de [20000, 55000] e base 100 → subida_mq3_raw == 500; leitura 700 em 56000 fica fora
def test_media_arquivo_e_sopro(pg): ...         # janela 'arquivo' = média de tudo; 'sopro' = só em_sopro
def test_rodada_sem_sopro(pg): ...              # aparece em v_rodadas_sem_sopro; janela 'sopro' com n_leituras 0
def test_v_leituras_sem_ppm(pg): ...            # 'ppm' e 'alcool' não estão nas colunas de v_leituras nem de v_media_rodada
```

- [ ] **Step 2:** subir um Postgres descartável: `docker run --rm -d --name pg-teste -e POSTGRES_PASSWORD=t -p 55432:5432 postgres:16`; `PG_DSN=postgresql://postgres:t@localhost:55432/postgres python -m pytest -m integracao -v` → FAIL.
- [ ] **Step 3:** implementar `01-schema.sql`, `02-leitor.sh`, `banco.py`, `conftest.py`.
- [ ] **Step 4:** mesmo comando → PASS; `python -m pytest` sem `PG_DSN` → testes de banco aparecem como `skipped`. Depois `docker stop pg-teste`.
- [ ] **Step 5: Commit** `feat(db): esquema, views de médias e subidas, acesso pelo coleta.banco`

---

### Task 6: Ingestor e Docker Compose local

**Files:**
- Create: `applications/coleta/ingestor.py`, `applications/coleta/Dockerfile`, `applications/mosquitto/mosquitto.conf`, `docker-compose.yml`, `.env.example`
- Modify: `.gitignore` (raiz; criar se não existir) com `.env`
- Test: `applications/coleta/tests/test_ingestor.py`

**Interfaces:**
- Consumes: `mensagens.decodificar`, `banco.*` (Tasks 2, 5).
- Produces:
  - `ingestor.tratar(con, topico: str, dados: bytes) -> None`: `.../rodada` → `gravar_rodada`; `.../leituras` → `garantir_rodada` + `gravar_leitura`; `.../eventos` → `garantir_rodada` + `gravar_evento`; `.../status` → ignora; JSON inválido ou campo faltando → loga `aviso:` e segue.
  - `python -m coleta.ingestor`: assina `mq3/+/rodada`, `mq3/+/leituras`, `mq3/+/eventos` com QoS 1 e `clean_start=False`/sessão persistente (client id fixo `mq3-ingestor`), reconecta sozinho; reconecta ao banco se a conexão cair.
- Compose:
  - `mosquitto`: `eclipse-mosquitto:2`, porta `1883:1883`, `mosquitto.conf` com `listener 1883`, `allow_anonymous true`, `persistence true`.
  - `postgres`: `postgres:16`, `POSTGRES_DB/USER/PASSWORD` do `.env`, `127.0.0.1:5432:5432`, volume nomeado, `applications/db` montado em `/docker-entrypoint-initdb.d`, healthcheck `pg_isready`.
  - `ingestor`: build `applications/coleta`, `MQTT_HOST=mosquitto`, `PG_DSN` apontando para `postgres`, `depends_on` com `service_healthy`, `restart: unless-stopped`.
  - `.env.example`: `POSTGRES_DB=mq3`, `POSTGRES_USER=mq3`, `POSTGRES_PASSWORD=troque-isto`, `GRAFANA_PG_SENHA=troque-isto`.
- Dockerfile: `python:3.12-slim`, instala só `paho-mqtt` e `psycopg[binary]`, copia o pacote `coleta`, `CMD ["python", "-m", "coleta.ingestor"]`. O contexto do build precisa conter o pacote como `coleta/` (usar `context: applications` e `dockerfile: coleta/Dockerfile`).

- [ ] **Step 1: Write the failing tests** (`integracao`)

```python
def test_rodada_leituras_eventos(pg): ...          # tratar() com as 3 mensagens → 1 rodada, N leituras, 1 evento
def test_mensagem_repetida(pg): ...                # mesma leitura 2x → 1 linha
def test_leitura_antes_da_rodada(pg): ...          # leitura e depois rodada → nada perdido, caso preenchido
def test_json_invalido_nao_derruba(pg, capsys): ...# tratar(con, "mq3/placa01/leituras", b"{") → sem exceção, "aviso" na saída
def test_rodada_fim_grava_sha(pg): ...
```

- [ ] **Step 2:** rodar com `PG_DSN` → FAIL. **Step 3:** implementar. **Step 4:** rodar → PASS.
- [ ] **Step 5: Verificação do Compose:** `cp .env.example .env && docker compose up -d --build`; `docker compose ps` mostra os 3 serviços `running`/`healthy`. `mosquitto_pub` não precisa estar instalado: publicar uma rodada e uma leitura com `python -c` usando `coleta.publicador`, e conferir `docker compose exec postgres psql -U mq3 -c "select count(*) from leituras"` → 1. `docker compose restart ingestor` e republicar a mesma leitura → continua 1.
- [ ] **Step 6: Commit** `feat(infra): ingestor MQTT → PostgreSQL e docker compose`

---

### Task 7: Simulador e importador

**Files:**
- Create: `applications/coleta/simulador.py`, `applications/coleta/importador.py`
- Test: `applications/coleta/tests/test_importador.py`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces:
  - `python -m coleta.simulador CSV --caso C --participante P [--intervalo 1.0] [--sopros 20.4,80] [--placa P]`: publica `rodada` (`origem="simulador"`), cada linha do CSV como `leituras` no ritmo de `--intervalo`, `sopro_inicio` quando o `t_ms` da leitura passar de cada valor de `--sopros` (segundos), e `rodada_fim` (sem `sha256`, para o simulador nunca bloquear a importação do mesmo arquivo). Recusa caminho dentro de `ml/data/processed/`; aceita qualquer CSV com o cabeçalho do firmware.
  - `importador.ler_csv_sessao(caminho: Path) -> list[Leitura]` (usa `Leitura` com os campos do cabeçalho; linhas inválidas → `ValueError` com o número da linha)
  - `importador.sopros_do_attempts(attempts: Path, arquivo: str) -> tuple[set[str], list[tuple[int, int | None]]]` (condições e sopros em ms das linhas cujo `session_file == arquivo`; arquivo inexistente → `(set(), [])`)
  - `importador.importar(con, caminho: Path, caso: str, participante: str, placa: str, attempts: Path) -> str`: valida o caso; SHA-256 já existente → `ValueError("já importado como rodada <id>")`; condições no `attempts.csv` diferentes de `{caso}` → `ValueError` explicando; grava com `origem="importador"`, `inicio=now()`, `arquivo_sessao=caminho.name`; devolve o id.
  - CLI: `python -m coleta.importador CSV --caso C --participante P [--placa P] [--attempts ARQ]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_le_amostra_real():  # firmware/leituras.csv → len > 0, primeira amostra == 38
def test_sopros_do_attempts(tmp_path): ...  # 2 linhas do arquivo + 1 de outro → 2 sopros, {"perfume"}
@pytest.mark.integracao
def test_importar_duas_vezes_recusa(pg, tmp_path): ...
@pytest.mark.integracao
def test_condicoes_misturadas_recusa(pg, tmp_path): ...  # attempts com perfume e clean para o mesmo arquivo
@pytest.mark.integracao
def test_importa_sopros_como_eventos(pg, tmp_path): ...  # v_sopros tem 1 linha com inicio_ms == blow_start_s * 1000
```

- [ ] **Step 2:** rodar → FAIL. **Step 3:** implementar. **Step 4:** rodar → PASS.
- [ ] **Step 5: Verificação:** com o Compose de pé, `python -m coleta.simulador ../firmware/leituras.csv --caso clean --participante p00 --intervalo 0.05` → `select origem, count(*) from v_leituras group by 1` mostra `simulador`.
- [ ] **Step 6: Commit** `feat(coleta): simulador e importador de CSV`

---

### Task 8: Grafana Cloud (PDC e dashboard)

**Files:**
- Modify: `docker-compose.yml` (serviço `pdc`), `.env.example`
- Create: `applications/pdc/README.md`, `applications/grafana/README.md`, `applications/grafana/dashboards/coleta.json`, `applications/grafana/publicar.py`

**Interfaces:**
- Consumes: as views da Task 5 e os tópicos da Task 2.
- Produces:
  - Serviço `pdc`: imagem `grafana/pdc-agent:latest` fixada na versão estável atual no momento da implementação; comando com `-token ${GCLOUD_PDC_SIGNING_TOKEN} -cluster ${GCLOUD_PDC_CLUSTER} -gcloud-hosted-grafana-id ${GCLOUD_HOSTED_GRAFANA_ID}` (conferir os nomes exatos das flags na página do PDC da stack, que mostra o comando pronto); sem portas expostas; `restart: unless-stopped`; `profiles: ["cloud"]`, para o Compose local subir sem token (`docker compose --profile cloud up -d`).
  - `.env.example` acrescenta: `GCLOUD_PDC_SIGNING_TOKEN=`, `GCLOUD_PDC_CLUSTER=`, `GCLOUD_HOSTED_GRAFANA_ID=`, `GRAFANA_URL=https://<stack>.grafana.net`, `GRAFANA_TOKEN=`.
  - `grafana/README.md` (passo a passo para a equipe): criar a stack free; instalar `grafana-mqtt-datasource` e `volkovlabs-echarts-panel` pelo catálogo (no Cloud a versão não é fixada no Compose: anotar no README a versão instalada, 7.2.5 ou mais nova; se o Business Charts não estiver disponível, o heatmap vira Table nativa com cor de fundo por célula e só o boxplot fica sem painel); criar a rede PDC e copiar os valores para o `.env`; criar data source PostgreSQL (host `postgres:5432`, banco `mq3`, usuário `grafana_leitor`, PDC ligado) e MQTT (`tcp://mosquitto:1883`, PDC ligado); criar service account com papel Editor e token em `GRAFANA_TOKEN`. Se o MQTT via PDC falhar, trocar os dois painéis ao vivo para o PostgreSQL (`v_leituras` da rodada mais recente, refresh 1 s) e registrar isso como limitação.
  - `publicar.py`: `python applications/grafana/publicar.py` lê `GRAFANA_URL`/`GRAFANA_TOKEN` do ambiente ou do `.env`, faz `POST /api/dashboards/db` com `{"dashboard": <json>, "overwrite": true}` e imprime a URL devolvida; erro HTTP → mensagem clara e código de saída 1. Só biblioteca padrão (`urllib`).
  - `coleta.json` (uid `mq3-coleta`, título `MQ-3 — Coleta`):
    - Variáveis: `ds_pg` (tipo datasource, `postgres`), `ds_mqtt` (tipo datasource, `grafana-mqtt-datasource`), `caso` (multi, `select distinct caso from rodadas`), `participante` (multi), `rodada` (`select id as __value, ... as __text from rodadas order by inicio desc`), `janela` (custom `arquivo,sopro`), `incluir_simulador` (custom `nao,sim`, padrão `nao`). Painéis usam `${ds_pg}`/`${ds_mqtt}`, nunca um uid fixo.
    - Painéis da seção 6 do spec, nesta ordem: ao vivo (Time series, MQTT `mq3/placa01/leituras`, 4 séries); rodada atual e status (Stat, MQTT `rodada` e `status`); média por caso (Table + Bar chart: `select caso, count(*) as rodadas, avg(media_mq3_raw), ... from v_media_rodada where janela = '$janela' and caso in ($caso) and (origem <> 'simulador' or '$incluir_simulador' = 'sim') group by caso`); boxplot (Business Charts, uma série por caso, `select caso, mq3_raw, ... from v_leituras` filtrado por janela via `em_sopro`; quartis calculados no JavaScript do painel); heatmap (Business Charts, a partir da mesma consulta da média por caso; normalização min–max por sensor no JavaScript); scatterplot (XY chart nativo, `select caso, subida_mq135_raw, subida_mq3_raw from v_sopros join rodadas ...`, cor por `caso`); lista de rodadas sem sopro (Table, `v_rodadas_sem_sopro`); histórico (Time series de `v_leituras` com `rodada_id = '$rodada'`, eixo `ts`, anotações de `eventos` tipo `sopro_inicio`); resultado do modelo (Text: `Sem modelo treinado com dados reais.`).
- [ ] **Step 1: Validar o JSON:** `python -c "import json;d=json.load(open('applications/grafana/dashboards/coleta.json'));assert d['uid']=='mq3-coleta'"` e `grep -c '"uid": "' applications/grafana/dashboards/coleta.json` não encontra uid de data source fixo (só o do dashboard).
- [ ] **Step 2: Validar cada SQL dos painéis** contra o banco local: rodar cada consulta (substituindo as variáveis por valores) em `docker compose exec postgres psql -U grafana_leitor ...` depois de importar `firmware/leituras.csv` com o importador → todas executam sem erro com o usuário só leitura.
- [ ] **Step 3: Verificação ponta a ponta (precisa da stack da equipe):** seguir `grafana/README.md`, `docker compose --profile cloud up -d`, `python applications/grafana/publicar.py`, rodar o simulador e ver as curvas ao vivo no dashboard. Se a equipe ainda não tiver a stack, registrar esse passo como pendente no resumo da entrega, sem marcar como feito.
- [ ] **Step 4: Commit** `feat(grafana): PDC no compose, dashboard versionado e script de publicação`

---

### Task 9: Documentação

**Files:**
- Create: `applications/README.md`
- Modify: `AGENTS.md` (seções 4, 7.1, 8 e 10)

- [ ] **Step 1: `applications/README.md`** com: o diagrama da seção 5 do spec; instalar dependências no `ml/.venv` (`pip install -r applications/coleta/requirements.txt`); subir o Compose (local e `--profile cloud`); roteiro de um dia de coleta (achar a porta com `ls /dev/cu.*`, rodar a ponte com `--duracao`, Enter no sopro, `f` no fim, conferir com `python -m src.cli validate`); simulador; importador e a regra da cópia da LittleFS; testes (`python -m pytest`, e com `PG_DSN` para os de banco); limitações (Mosquitto sem senha na rede local, dashboard só com o Compose de pé, MQTT via PDC a confirmar).
- [ ] **Step 2: `AGENTS.md`:** seção 4 move "MQTT, banco, dashboard Grafana e Compose" para o que existe (sem dizer "testado com dados reais"); seção 7.1 troca "Grafana no Docker Compose, provisionado por arquivo" por Grafana Cloud free + PDC + `publicar.py`; seção 8 acrescenta `applications/` e `docker-compose.yml` na árvore; seção 10 marca as tarefas 3 e 4 como feitas e mantém a publicação pela ESP32 como pendente do firmware.
- [ ] **Step 3:** `cd applications && python -m pytest` → tudo PASS (banco `skipped` sem `PG_DSN`); `cd ml && python -m pytest` → PASS (nada do ML mudou).
- [ ] **Step 4: Commit** `docs: como coletar, subir a infraestrutura e publicar o dashboard`
