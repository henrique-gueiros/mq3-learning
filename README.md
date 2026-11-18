# Sopro Seguro

Detector de álcool para carros, com ESP32, sensores MQ-3, MQ-135 e DHT11 e machine learning. Projeto
das disciplinas de **Sistemas Embarcados** e **Machine Learning** (CESAR School, grupo 15).

Cada sopro recebe uma classe:

| Classe | Quando |
| --- | --- |
| `sob_efeito` | A pessoa bebeu (`drink`) |
| `sem_efeito` | A pessoa não bebeu: ar do carro, perfume, álcool em gel, borrifo ou enxaguante |

A classe vem do que foi feito no teste, anotado pela equipe. O sistema não mede mg/L e **não é um
etilômetro**: `sob_efeito` significa "bebeu nas condições do experimento".

## Equipe

| Integrante | GitHub | Responsabilidade |
| --- | --- | --- |
| Luis Felipe Perylo Benicio | `LFPerylo` | Decisões do projeto, dashboard e coleta de dados |
| Henrique Wanderley Gueiros | `henrique-gueiros` | Dashboard e coleta de dados |
| Artur Barros Dowsley | `Artur-Dowsley` | Circuito, firmware e coleta de dados |
| Samuel Lucas de Abreu Gouveia | `sam-abreu` | Circuito, documentação e coleta de dados |
| Felipe Barros de Carvalho | `fbclipe` | Coleta de dados |

## Como funciona

```text
ESP32 ──USB──▶ ponte serial ──MQTT──▶ Mosquitto ──▶ ingestor ──▶ PostgreSQL ──▶ API ──▶ tela React
 MQ-3 · MQ-135 · DHT11                  (1883 · ws 9001)                                   (ao vivo por /mqtt)
```

A ESP32 grava um CSV por sessão. Hoje a ponte serial (ou o simulador) publica as leituras no MQTT no
lugar dela; a ESP32 ainda não tem Wi-Fi/MQTT. O ingestor grava no PostgreSQL, a API (somente leitura)
alimenta os gráficos de análise e a tela recebe as leituras ao vivo direto do broker. O diagrama
completo, os contratos e as decisões estão em [`ARCHITECTURE.md`](ARCHITECTURE.md); o estado do
projeto e os próximos passos, em [`docs/roadmap.md`](docs/roadmap.md).

## Requisitos

- **Hardware:** ESP32 DevKit (`esp32dev`), sensor MQ-3, sensor MQ-135, DHT11, protoboard e fios;
  esquemático e foto em [`schematics/`](schematics/).
- **Software:** Docker com Compose; Python 3.12+ (coleta, API e ML); Node 22 (tela, para desenvolver);
  PlatformIO (firmware).

## Como rodar

```bash
cp .env.example .env            # troque as senhas
docker compose up -d --build    # Mosquitto, PostgreSQL, ingestor, API e tela
```

Abra **http://localhost:8080**. Para ver o dashboard antigo do Grafana: `docker compose --profile local up -d`
(http://localhost:3000). O Compose de `applications/services/` usa as mesmas portas: não suba os dois juntos.

Com os CSVs já coletados, no ambiente Python (`applications/ml/.venv`, criado como em `applications/ml/README.md`):

```bash
cd applications
python -m coleta.lote           # importa o lote de 12 CSVs válidos para o banco
python -m pytest                # testes (os de banco precisam de PG_DSN; veja applications/AGENTS.md)
```

Dia de coleta, com a placa ligada por USB e sopros marcados: `applications/README.md`.
Passo a passo de rotulagem, treino e do servidor do modelo: [`docs/guia-coleta-e-ml.md`](docs/guia-coleta-e-ml.md).

## Estrutura

```text
├── README.md              # Descrição do projeto, requisitos e instruções
├── ARCHITECTURE.md        # Mapa do sistema e contratos
├── docs/                  # requisitos/, relatorio/ (PDF CSBC-ABNT2), imagens/, planejamento/, roadmap.md
├── applications/          # Código de back-end, front-end e ML
│   ├── coleta/            #   ponte serial, ingestor, simulador, importador e lote de CSVs
│   ├── db/                #   esquema, views e migrações do PostgreSQL
│   ├── api/               #   API FastAPI somente leitura
│   ├── frontend/          #   tela React (ao vivo + análise)
│   ├── ml/                #   pipeline de ML: validação, features, treino, inferência
│   ├── services/          #   fluxo paralelo: worker e servidor do modelo
│   └── grafana/, pdc/     #   dashboard antigo e túnel do Grafana Cloud
├── esp32-esp8266/         # Firmware da ESP32 (PlatformIO); leituras/ guarda os CSVs gravados
└── schematics/            # Esquemático e foto da montagem
```

## Limitações

- A ESP32 ainda não publica no MQTT; o modelo de ML ainda não foi treinado com dados reais (a tela mostra
  só o detector ambiente × sopro, uma heurística).
- O Mosquitto aceita conexões sem senha: use só na rede local da coleta.
- Os dados coletados têm poucas pessoas e poucos casos; as métricas só valem depois da coleta rotulada.

Regras para quem continua o projeto: [`AGENTS.md`](AGENTS.md).
