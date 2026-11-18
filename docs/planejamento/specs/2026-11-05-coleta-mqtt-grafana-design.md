# Design: coleta → MQTT → PostgreSQL → Grafana

Data: 05/11/2026. Status: rascunho para aprovação da equipe.

## 1. Intenção

A equipe vai coletar dados manualmente, em **rodadas**: a placa ligada no notebook pelo USB e, em cada rodada, um único **caso** (bebida, enxaguante, perfume, álcool 70% borrifado, álcool 70% nas mãos, ar limpo). O professor pediu a **média do CSV de cada caso**.

O fluxo completo tem que estar pronto antes da coleta: as leituras saem da placa, passam pelo MQTT, são gravadas no banco e aparecem **ao vivo** no Grafana. Depois de gravadas, servem para comparar os casos. Isso atende ao requisito de Sistemas Embarcados (MQTT e dashboard em tempo real, avaliados no checkpoint de 17/11) e ao primeiro entregável de ML (publicação por MQTT com gravação em banco).

## 2. Objetivos

1. Uma **ponte serial** no notebook lê as linhas `CSV_LINHA,...` que o firmware já emite e publica cada leitura no MQTT, marcada com a rodada (caso + participante).
2. Durante a rodada, o operador aperta **Enter** quando a pessoa sopra. A ponte publica um evento `sopro_inicio` e grava o segundo do sopro. Assim o `attempts.csv` sai pronto, sem ninguém anotar à mão.
3. A ponte também grava um CSV no formato do firmware, com nome único, em `ml/data/raw/sessions/`, para o pipeline de ML continuar funcionando sem mudança.
4. Um comando `docker compose up` sobe Mosquitto, PostgreSQL, um **ingestor** (assina o MQTT e grava no banco) e o agente PDC que liga tudo ao Grafana Cloud.
5. Um **importador** grava no banco os CSVs gravados antes da ponte ou sem ela.
6. Um **simulador** publica um CSV real linha a linha (1 por segundo), para desenvolver e demonstrar sem a placa.
7. Um dashboard no Grafana Cloud, versionado em JSON no repositório, com os painéis da seção 6, e um script que o publica na stack pela API (token de service account no `.env`).

## 3. Fora do escopo

- Wi-Fi e MQTT no firmware da ESP32. Fica com quem mantém o firmware. Quando existir, a ESP32 publica nos mesmos tópicos e a ponte serial deixa de ser necessária.
- Airflow, MLflow, serviço de inferência, API e IPv6.
- Treinar ou mudar o modelo. O painel "resultado do modelo" fica reservado e vazio.

## 4. O que não pode acontecer

- Mudar o formato que o pipeline de ML lê (`ml/data/raw/sessions/*.csv` e `attempts.csv`) ou editar CSVs brutos já gravados.
- Exibir dados inventados. O simulador usa apenas CSVs reais (por exemplo `firmware/leituras.csv`).
- Usar `ppm` ou `alcool` do firmware como rótulo ou feature. Podem ser gravados no banco, mas os painéis de comparação mostram só `mq3_raw`, `mq135_raw`, temperatura e umidade.
- Perder leituras ou duplicá-las ao reconectar. A gravação é idempotente por (rodada, amostra).
- Credenciais versionadas. Senhas vão num `.env`; o repositório tem só um `.env.example`.

## 5. Arquitetura

```text
ESP32 --USB/serial--> ponte (notebook, fora do Docker) --MQTT--> Mosquitto
                       └─> CSV em ml/data/raw/sessions/        │
                       └─> linhas para attempts.csv            ├─> ingestor --> PostgreSQL ─┐
simulador / importador ---------------------------------------┘                              ├─ agente PDC ══túnel══> Grafana Cloud
                                                    Mosquitto (painel ao vivo) ──────────────┘
```

A ponte roda fora do Docker porque o Docker no macOS não enxerga a porta USB. Ela substitui o `pio device monitor` durante a coleta, já que a porta serial aceita um programa por vez.

### 5.1 Tópicos MQTT (seguindo o `AGENTS.md`, seção 7)

| Tópico | Conteúdo (JSON) | Retido |
| --- | --- | --- |
| `mq3/<placa>/rodada` | `rodada_id`, `caso`, `participante`, `inicio` (ISO), `arquivo_sessao` | sim |
| `mq3/<placa>/leituras` | `rodada_id`, `amostra`, `t_ms`, `mq3_raw`, `ppm`, `mq135_raw`, `mq135_mv`, `temperature_c`, `humidity_pct`, `alcool` | não |
| `mq3/<placa>/eventos` | `rodada_id`, `tipo` (`sopro_inicio`, `sopro_fim`, `rodada_fim`), `t_ms` | não |
| `mq3/<placa>/status` | `online`/`offline` (o `offline` vai como last will) | sim |
| `mq3/<placa>/resultado` | reservado para o serviço de inferência | — |

`<placa>` vem de um argumento (padrão `placa01`). Valores ausentes do DHT11 vão como `null`.

### 5.2 Banco (PostgreSQL)

- `rodadas`: id, placa, caso, participante, inicio, fim, arquivo_sessao, origem (`ponte`, `importador`, `simulador`) e notas.
- `leituras`: rodada_id, amostra, t_ms, as colunas do CSV e recebido_em. Chave única (rodada_id, amostra).
- `eventos`: rodada_id, tipo, t_ms.
- Uma view por rodada com: média do arquivo inteiro (a que o professor pediu), pico, linha de base (média dos 15 s antes do primeiro sopro) e média na janela do sopro. As janelas seguem `ml/src/features.py`: 15 s antes, sopro de 5 s se não houver `sopro_fim`, 30 s depois.

Os casos aceitos são os de `CONDITIONS` em `ml/src/data_validation.py`. A ponte e o importador recusam caso desconhecido.

### 5.3 Ponte serial — uso pretendido

```bash
python -m coleta.ponte --porta /dev/cu.usbserial-XXXX --caso perfume --participante p01
#   --duracao 120   encerra a rodada sozinha depois de 120 s de leituras (todas as rodadas têm o mesmo tamanho)
# Enter = início do sopro; "f" + Enter = fim do sopro; Ctrl+C = encerra antes da hora
```

Ao encerrar, a ponte acrescenta uma linha por sopro marcado em `ml/data/raw/attempts.csv` (criando o arquivo com o cabeçalho do template se ele não existir). `blow_start_s` é o `t_ms` da última leitura recebida antes do Enter, dividido por 1000.

O nome do CSV de sessão é `AAAA-MM-DD_<participante>_<caso>_<n>.csv`. Mantém as colunas do firmware, com os valores de `t_ms` da placa sem alteração.

Se o broker cair, a ponte continua gravando o CSV e avisa no terminal. A coleta não pode parar por causa da infraestrutura.

## 6. Dashboard

Variáveis do dashboard: caso(s), participante(s), rodada e janela (`arquivo inteiro` ou `sopro`).

| Painel | Fonte | Tipo |
| --- | --- | --- |
| Ao vivo: MQ-3, MQ-135, umidade e temperatura | MQTT | Time series nativo |
| Rodada atual (caso, participante) e status da placa | MQTT | Stat nativo |
| Média por caso (tabela e barras), na janela escolhida | PostgreSQL | Table / Bar chart nativos |
| Boxplot por caso, um por sensor | PostgreSQL | Business Charts (ECharts) |
| Heatmap caso × sensor, cor = média normalizada por sensor (0–1 entre o menor e o maior caso) | PostgreSQL | Business Charts |
| Scatterplot: subida do MQ-135 × subida do MQ-3, um ponto por sopro, cor = caso | PostgreSQL | XY chart nativo |
| Histórico: curva completa de uma rodada, com os sopros marcados | PostgreSQL | Time series nativo com anotações |
| Resultado do modelo | reservado | texto "sem modelo treinado" |

**Quantos sopros por rodada ainda não foi decidido**, então tudo funciona com 1 ou mais sopros por rodada:

- O scatterplot tem **um ponto por sopro** (a mesma unidade do `attempts.csv` e do modelo). "Subida" é o pico na janela do sopro e dos 30 s seguintes menos a linha de base daquele sopro (mediana dos 15 s antes dele). Rodadas sem sopro marcado ficam fora e aparecem numa lista à parte.
- A janela `sopro` é a união das janelas de todos os sopros da rodada (sopro + 30 s depois).

**Média do caso** (a que o professor pediu): as rodadas têm todas o mesmo tamanho, então a média de todas as leituras e a média das médias de cada CSV dão o mesmo número. O dashboard calcula a média das médias, para que uma rodada encerrada antes da hora não pese menos, e mostra ao lado quantas rodadas entraram.

O boxplot usa todas as leituras das rodadas de cada caso, na janela escolhida.

Plugins: `grafana-mqtt-datasource` e `volkovlabs-echarts-panel`, com as versões fixadas no Compose. O Business Charts exige Grafana ≥ 12.3.

**Grafana Cloud, plano gratuito.** O Grafana não roda no Compose: o dashboard fica numa stack do Grafana Cloud (plano free: até 3 usuários). Como o Cloud não enxerga o notebook, o Compose sobe também o **agente PDC** (Private Data Source Connect, disponível no plano free), que abre um túnel de saída da máquina para o Cloud. Por esse túnel o Cloud consulta o PostgreSQL e assina o Mosquitto locais, sem abrir portas no roteador. O token do PDC e o da stack vão no `.env`. Os dois plugins são instalados pelo catálogo da stack; PostgreSQL é nativo. Conferir na construção que o MQTT via PDC funciona no plano free (o suporte a PDC no plugin MQTT foi anunciado em maio/2026); se não funcionar, o painel ao vivo passa a ler o PostgreSQL com atualização a cada 1–2 s.

## 7. Estrutura no repositório

Decisão minha: a pasta nova segue o template da disciplina (`/applications`). O que já existe não muda de lugar.

```text
docker-compose.yml  .env.example
applications/
├── coleta/            # pacote Python: ponte, ingestor, importador, simulador, mensagens, banco
│   ├── requirements.txt  Dockerfile  tests/
├── mosquitto/         # mosquitto.conf
├── db/                # init.sql (tabelas e views)
├── pdc/               # instruções do agente PDC (o serviço fica no docker-compose.yml)
└── grafana/           # dashboards/*.json e script que publica na stack do Grafana Cloud
```

## 8. Decisões tomadas por mim (Claude), para a equipe conferir

- **Placa reiniciou no meio da rodada** (abrir a serial costuma reiniciar a ESP32): quando chega `CSV_ARQUIVO` ou a `amostra` volta para trás, a ponte fecha a rodada atual e abre outra com o mesmo caso e participante, num CSV novo, e avisa no terminal. Assim (rodada, amostra) continua único e o `blow_start_s` sempre se refere ao CSV certo.
- **Duplicatas:** `rodadas` guarda o SHA-256 do CSV, e o importador recusa um arquivo já importado. A regra de uso é que a cópia da LittleFS só é importada quando a rodada não passou pela ponte. Os painéis de comparação mostram `origem` ≠ `simulador` por padrão; uma variável do dashboard permite incluir o simulador.
- **Importador:** recebe `--caso` e `--participante` por argumento. Se o arquivo aparecer no `attempts.csv` com mais de uma condição, recusa e explica.
- **Linha de base:** mediana dos 15 s antes do sopro, igual a `ml/src/features.py`.
- **Eixo de tempo:** cada leitura guarda `tempo_s` (segundos desde o início da rodada). O histórico desenha a curva em `inicio da rodada + tempo_s`; em rodadas importadas, `inicio` é o momento da importação.
- **Plugins:** o scatterplot usa o **XY chart nativo**. O Business Charts fica só para o boxplot (que não existe nativo) e o heatmap caso × sensor. Versão fixada: 7.2.5 (maio/2026, exige Grafana ≥ 12.3). Se não funcionar, o heatmap passa para tabela com cor de fundo nativa, e só o boxplot depende do plugin.

## 9. Decisões que deixei para quem for construir

- Bibliotecas: pyserial, paho-mqtt e psycopg (ou equivalentes).
- A ponte, o simulador e o importador rodam no `ml/.venv` (o `AGENTS.md` pede um ambiente só); o ingestor roda em contêiner. Decisão minha.
- Mosquitto aceita conexões anônimas, só na máquina e na rede local da coleta; o Cloud chega a ele só pelo túnel PDC. O Grafana Cloud consulta o PostgreSQL com um usuário só de leitura. Decisão minha; registrar como limitação.
- O dashboard só mostra dados enquanto o Compose está rodando em alguma máquina da equipe. Para a apresentação de 12/12, o notebook da demo roda o Compose.
- Testes: pytest para as funções puras (parse da linha serial, montagem das mensagens, linhas do `attempts.csv`, cálculo das janelas). Mais um teste de fumaça com o Compose: simulador → banco → consulta retorna as leituras.
- Layout visual exato dos painéis, cores e intervalos de atualização.
- Documentar o uso no `README` da raiz ou em `applications/README.md`, e atualizar o `AGENTS.md` (seções 4, 7 e 10).
