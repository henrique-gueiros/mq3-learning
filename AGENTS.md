# AGENTS.md — Detector de Álcool com MQ-3

## 1. Papel deste arquivo

Este arquivo orienta o Cursor, o Claude Code e outros agentes a continuar o projeto acadêmico de detector de álcool. É a fonte única das regras do projeto; o `CLAUDE.md` só aponta para cá.

Onde está o resto:

- `ml/README.md`: uso do pipeline de ML (comandos, formato dos dados, como o treino avalia).
- `firmware/README.md`: firmware da ESP32 e limitações do ADC.
- `docs/`: requisitos das duas disciplinas. `Projeto-Embarcados_CesarSchool-CSBC.pdf` (Sistemas Embarcados) e `Entregáveis 6ºP - Projeto 2026.2.xlsx` (entregáveis de Machine Learning, coluna CC).
- `docs/decisoes_projeto_ml.pdf` (versão de 04/11/2026): sensores, tabela de casos, regras e caminho. **Está desatualizado nas classes**: ainda descreve 3 classes (`sem_alcool`, `externo`, `bebida`), duas etapas e as condições `alcohol_cup` e `drink_perfume`. Em 05/11/2026 a equipe passou para a classificação binária da seção 3, que é a que vale e a que o código implementa. O resto do PDF continua válido.

Trabalhe incrementalmente, explique decisões importantes e trate hipóteses experimentais como hipóteses. A equipe está aprendendo; prefira código claro, modular e didático.

Antes de mudanças grandes, inspecione o repositório e preserve o que já existe. O firmware em `firmware/` é mantido por outro integrante: mude-o só quando a tarefa pedir.

## 2. Contexto

- Detector de álcool para carro, acadêmico, usado em duas disciplinas: **Machine Learning** (pipeline, modelos, MLflow, Airflow) e **Sistemas Embarcados** (ESP32, Wi-Fi, MQTT, dashboard em tempo real).
- Hardware funcionando: **ESP32** (`esp32dev`, Arduino/PlatformIO) com **MQ-3** (GPIO 34), **MQ-135** (GPIO 35) e **DHT11** (GPIO 4). O firmware lê cerca de 1 vez por segundo e grava um CSV por sessão. Ainda não há Wi-Fi nem MQTT no firmware.
- O que o sistema faz depois de uma detecção (alerta, bloqueio) ainda não foi decidido e não é decisão do modelo.
- **Só dados coletados pela equipe.** Nada de datasets da internet nem dados sintéticos. Treino e teste vêm das sessões gravadas pelo firmware.
- O ADC da ESP32 satura perto de 3,1 V; leituras muito altas dos MQ ficam achatadas (ver `firmware/README.md`).

### Datas e regras de Sistemas Embarcados

- **17/11** checkpoint (protótipo, código-fonte, arquitetura, dashboard e protótipo do front-end). **03/12** relatório (modelo CSBC/ABNT2) e repositório. **12/12** apresentação na Mostra TechDesign.
- Avaliação: funcionamento com MQTT, dashboard em tempo real, relatório, organização do GitHub (README detalhado, commits de todos) e apresentação. Bônus: alertas por e-mail ou mensageiro e comunicação em IPv6.
- **Uso de IA no relatório só para revisão de texto**, com declaração de uso. Agentes não redigem o relatório; podem revisar texto escrito pela equipe e produzir código, figuras e tabelas de resultados.
- O PDF sugere a estrutura `/docs`, `/applications`, `/esp32-esp8266`, `/schematics`. O repositório hoje usa `firmware/`, `ml/`, `applications/` e `services/`; renomear ou reorganizar é decisão da equipe, não do agente.

## 3. O que o modelo prevê

Cada **tentativa de sopro** recebe uma de duas classes:

| Classe | Significado |
| --- | --- |
| `sob_efeito` | A pessoa bebeu (`drink`) |
| `sem_efeito` | A pessoa não bebeu. Inclui ar limpo, perfume, álcool em gel, borrifo e enxaguante |

Perfume, álcool 70% e enxaguante são exemplos de `sem_efeito`: estão na coleta para o modelo aprender a separar vapor de álcool no ambiente de motorista que bebeu. O modelo não mede mg/L. `sob_efeito` significa "bebeu nas condições do experimento", não um laudo de embriaguez.

## 4. Estado atual

Pronto e testado:

- Firmware lendo os três sensores e gravando CSV por sessão (`firmware/src/main.cpp`, `firmware/monitor/filter_leituras.py`). `firmware/leituras.csv` é a primeira amostra real.
- Pipeline de ML em `ml/src/`, que lê esses CSVs sem alterá-los: validação, recorte de cada sopro, features, separação treino/teste por participante, comparação de 4 modelos (baseline, regressão logística, árvore de decisão, Random Forest) em 4 conjuntos de sensores, Grid Search em validação cruzada aninhada por grupo, modelo final e previsão. Comandos em `ml/README.md`.
- Coleta até o dashboard em `applications/` (uso em `applications/README.md`): ponte serial → MQTT que grava o CSV de sessão e completa o `attempts.csv`, Docker Compose com Mosquitto, PostgreSQL e ingestor, simulador, importador e dashboard versionado para o Grafana Cloud (ligado pelo agente PDC). Testado com a amostra `firmware/leituras.csv`, uma porta serial simulada e um Grafana local; falta testar com a placa e na stack do Grafana Cloud.
- Servidor do modelo em `services/` (uso em `services/README.md`): Mosquitto, PostgreSQL, simulador de um CSV do firmware, worker que grava no banco e servidor que só classifica quando existir `ml/models/sob_efeito.joblib`, e um Grafana local (`bancada`, só leituras ao vivo e resultado do sopro; MQTT por WebSocket na porta 9001, que não funciona no Grafana Cloud). O scikit-learn é fixo em 1.6.1 em `ml/requirements.txt` e em `services/Dockerfile.model`: o `.joblib` só abre na versão que o gravou. A ESP32 ainda não publica.

`applications/` e `services/` foram feitas em paralelo. Cada uma sobe o próprio broker e o próprio Postgres. As portas 1883 e 5432 coincidem (e a 3000 e a 9001, do Grafana local de `services/`), então as duas stacks não sobem juntas. Na coleta, só `applications/` roda. Unificar os dois fluxos é decisão da equipe.

Ainda não existe:

- [ ] Coleta rotulada suficiente (sessões + `ml/data/raw/attempts.csv`), com as duas classes.
- [ ] Análise exploratória e revisão das features com dados reais.
- [ ] Modelo treinado e avaliado com dados reais. Métricas dos testes automatizados usam curvas montadas à mão e **não** dizem nada sobre o sensor.
- [ ] Wi-Fi/MQTT na ESP32. Hoje a ponte serial em `applications/` publica no lugar da placa.
- [ ] MLflow, Airflow e API. O dashboard da coleta, para o Grafana Cloud, já está em `applications/grafana/`.

Calibração, limites de detecção e valores típicos dos sensores só entram quando medidos. Um entregável está pronto quando está implementado e testado.

## 5. Dados

### 5.1 Sessões — `ml/data/raw/sessions/*.csv`

Cópias **sem edição** dos CSVs do firmware. Cada arquivo vai do ligar ao reiniciar da placa. Como a numeração recomeça em cada placa, renomear ao copiar para um nome único (por exemplo `2026-11-04_p01_leituras_3.csv`).

| Coluna | Uso |
| --- | --- |
| `t_ms` | Tempo em ms desde a partida (obrigatório) |
| `mq3_raw`, `mq135_raw`, `humidity_pct` | Leituras usadas nas features. O DHT11 fica vazio nos primeiros segundos |
| `temperature_c` | Gravada, mas fora das features (não distingue hálito de ambiente; num carro varia com o clima) |
| `amostra`, `ppm`, `mq135_mv`, `alcool` | **Nunca usar.** `ppm` e `alcool` são calculados pelo firmware a partir do próprio MQ-3; usá-los como rótulo ou feature ensina a regra do firmware, não o problema |

### 5.2 Sopros — `ml/data/raw/attempts.csv`

Uma linha por sopro, preenchida por quem conduz o experimento (modelo em `ml/templates/attempts_template.csv`): `attempt_id`, `session_file`, `participant_id` (anônimo), `condition`, `blow_start_s` (segundo da sessão em que o sopro começou) e, opcionalmente, `blow_end_s`, `reference_mg_l` e `notes`.

O rótulo vem da `condition`, nunca dos sensores:

| Condição | Classe |
| --- | --- |
| `clean`, `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash` | `sem_efeito` |
| `drink` | `sob_efeito` |

Novas condições entram em `CONDITIONS`, em `ml/src/data_validation.py`. O PDF também propõe `alcohol_cup` (`sem_efeito`) e `drink_perfume` (`sob_efeito`); só adicione quando a equipe for coletá-las.

### 5.3 Recorte e features

`assign_phases` recorta 15 s antes do sopro (`before`), o sopro (`blow`, 5 s se `blow_end_s` estiver vazio) e 30 s depois (`after`). Dois sopros da mesma sessão precisam de cerca de 50 s de intervalo. As features (antes, pico, subida, tempo até o pico, recuperação, proporção MQ-135/MQ-3 e atraso entre o pico do MQ-3 e o da umidade) estão em `ml/src/features.py` e devem ser revistas depois da análise exploratória.

## 6. Entregáveis de Machine Learning

Fonte: coluna CC de `docs/Entregáveis 6ºP - Projeto 2026.2.xlsx`. Há duas bases MQTT no repositório, feitas em paralelo: a coleta e o dashboard em `applications/`, e o worker com o servidor do modelo em `services/`. A ESP32 ainda não publica.

1. **Infraestrutura e dataset inicial:** coleta própria (CSVs do firmware + `attempts.csv`) e publicação por MQTT com gravação em banco.
2. **Pipeline no Airflow** (ingestão, preparação, disponibilização) e **notebook de EDA** em `ml/notebooks/`, justificando limpeza, normalização, ausentes etc. A lógica reutilizável fica em `ml/src/`.
3. **Baseline** justificado, com métricas de validação e registro no **MLflow**.
4. **Pelo menos três modelos** comparados, no MLflow, com visualizações (matriz de confusão, ROC/AUC) e análise crítica. Hoje: regressão logística, árvore e Random Forest além do baseline; KNN é um candidato natural a mais, citado na planilha.
5. **Otimização de hiperparâmetros** (Grid Search já implementado; Random Search ou Optuna são alternativas), documentada e no MLflow.
6. **Validação cruzada k-fold** com análise de estabilidade (variação entre folds), overfitting/underfitting (comparar score de treino e de validação) e generalização. Aqui o k-fold é **`GroupKFold` por participante**: um k-fold comum põe sopros da mesma pessoa no treino e na validação e infla as métricas.
7. **Integração:** o pipeline consome dados novos da ESP32 (ou simulador), processa e infere com o modelo validado.
8. **Docker Compose** com broker MQTT, banco, Airflow, MLflow, API e dashboard, subindo com um comando.
9. **Dashboard** consumindo MQTT e/ou API, com indicadores, inferências e monitoramento (seção 7.3).
10. **Apresentação** da arquitetura completa, com decisões técnicas e limitações.

Métricas: F1 macro, acurácia balanceada, precisão e recall por classe, matriz de confusão. A prioridade é o **recall de `sob_efeito`**. A inferência usa o mesmo pré-processamento do treino (já é um `Pipeline` do scikit-learn).

## 7. MQTT

Há dois contratos no repositório, feitos em paralelo. A ESP32 ainda não publica em nenhum dos dois. A placa e o broker precisam estar na mesma rede. Quem mantém o firmware escolhe o contrato na hora de publicar.

### 7.1 Coleta em `applications/`

A ponte serial no notebook publica. Quando a ESP32 tiver Wi-Fi, ela publica as mesmas mensagens e a ponte sai. O formato está em `applications/coleta/mensagens.py`. O ingestor grava no PostgreSQL sem duplicar (chave rodada + amostra). O esquema e as views (médias, sopros, subidas) estão em `applications/db/01-schema.sql`.

| Tópico | Quem publica | Conteúdo |
| --- | --- | --- |
| `mq3/<placa>/rodada` | ponte (depois a ESP32) | Rodada atual: caso, participante, arquivo; retida |
| `mq3/<placa>/leituras` | ponte (depois a ESP32) | Uma mensagem por leitura, com os mesmos campos do CSV e o `rodada_id` |
| `mq3/<placa>/eventos` | ponte (depois a ESP32) | `sopro_inicio`, `sopro_fim` e `rodada_fim` |
| `mq3/<placa>/status` | ponte (depois a ESP32) | `{"estado": "online"}` / `"offline"` (last will); retida |
| `mq3/<placa>/resultado` | serviço de inferência | Classe e probabilidades (ainda não existe neste fluxo) |

### 7.2 Servidor do modelo em `services/`

A ESP publica no broker. O servidor do modelo é um container do Compose de `services/`, no computador da bancada. A placa não abre conexão com ele. O formato está em `services/mq3mqtt/messages.py`.

| Tópico | Quem publica | Conteúdo |
| --- | --- | --- |
| `mq3/<placa>/leituras` | ESP32 (hoje, o simulador) | Uma mensagem por leitura, com os mesmos campos do CSV |
| `mq3/<placa>/eventos` | ESP32 (hoje, o simulador) | `sopro_inicio` e `sopro_fim`, para não depender de anotar o segundo à mão |
| `mq3/<placa>/status` | ESP32 (hoje, o simulador) | `online`/`offline` |
| `mq3/<placa>/sopro_pronto` | worker, depois de gravar o `sopro_fim` | Aviso interno para o servidor do modelo. A ESP não publica aqui |
| `mq3/<placa>/resultado` | servidor do modelo | `sem_modelo` enquanto não houver `ml/models/sob_efeito.joblib`; depois, classe e probabilidades |

O worker assina `leituras`, `eventos` e `status` e grava no PostgreSQL, ignorando repetidas (mesma placa, sessão e amostra). O formato é o mesmo do CSV, então o código de ML não muda quando a fonte passar de arquivo para banco: muda só a leitura dos dados. O servidor do modelo lê o sopro no banco e chama `ml/src/inference.py`. Para desenvolver sem a placa, o simulador publica um CSV do firmware linha a linha. A publicação pela ESP32 continua com quem mantém o firmware.

### 7.3 Dashboard (Grafana Cloud)

Grafana Cloud no plano gratuito: o Grafana não roda no Compose. O agente PDC (serviço `pdc`, perfil `cloud`) abre um túnel de saída para a stack consultar o PostgreSQL e assinar o Mosquitto locais. O dashboard é versionado em `applications/grafana/dashboards/coleta.json` e publicado com `applications/grafana/publicar.py`; a configuração da stack está em `applications/grafana/README.md`.

- **PostgreSQL** (nativo): médias por caso, boxplot, heatmap, subidas por sopro, histórico e situação da placa. A lógica fica nas views do banco; os painéis só fazem `SELECT`.
- **MQTT** (`grafana-mqtt-datasource`): curvas ao vivo.
- **Business Charts** (`volkovlabs-echarts-panel`): só boxplot e heatmap, que não existem nativos. O resto é painel nativo.

## 8. Estrutura e estilo

```text
AGENTS.md  CLAUDE.md  docker-compose.yml  .env.example
applications/             # coleta (ponte, ingestor, simulador, importador), db/, mosquitto/, grafana/, pdc/
docs/                     # requisitos das disciplinas, decisoes_projeto_ml.pdf e superpowers/ (design e plano)
firmware/                 # ESP32 (PlatformIO); src/main.cpp, monitor/, leituras.csv
ml/
├── data/raw/sessions/    # CSVs do firmware, sem edição (não versionados)
├── data/raw/attempts.csv # um sopro por linha (não versionado)
├── data/processed/       # features, train e test (não versionados)
├── config/split.json     # separação treino/teste; versionado
├── models/  reports/  notebooks/
├── src/                  # data_validation, data_io, features, splitting, train, inference, cli, paths
├── tests/  templates/  requirements.txt  pytest.ini
services/               # Mosquitto, Postgres, worker, servidor do modelo, simulador
```

Python 3.9+ com numpy, pandas, scikit-learn, matplotlib, seaborn e jupyter (versões em `ml/requirements.txt`). O cliente MQTT e o Postgres estão em `applications/coleta/requirements.txt` e em `services/requirements.txt`; os dois entram no mesmo `ml/.venv`, criado como em `ml/README.md`. Não criar outro gerenciador de ambiente. MLflow entra quando o experimento real for registrado. O ingestor de `applications/` e o worker e o servidor de `services/` têm imagem Docker própria.

- Código simples, com tipos e docstrings nas funções públicas; testes para validação, features e treino.
- Separar treino e teste **por participante** (`participant_id`) ou, com poucos participantes, por arquivo de sessão. A mesma pessoa fica de um lado só, e todas as leituras de um sopro ficam juntas.
- Escolher hiperparâmetros só dentro do treino (a validação cruzada aninhada por grupo já faz isso) e usar o teste uma única vez.
- Dados derivados vão para `data/processed/`; os brutos ficam intactos. Fora do Git: `.venv/`, credenciais, dados pessoais e CSVs de sessão.
- Caminhos relativos ao repositório (`ml/src/paths.py`).

## 9. Regras para o agente

- Trabalhar em etapas pequenas; ao terminar, dizer o que mudou, como executar e o que foi testado.
- Inspecionar o repositório antes de criar algo novo.
- Dados só da coleta da equipe; `ppm` e `alcool` do firmware ficam fora de rótulos e features.
- Métricas dos testes automatizados não são desempenho real.
- Medições, calibração, resultados e fontes vêm de dados ou documentos reais.
- Horário ou dia da semana como preditor só com justificativa e avaliação.
- Testes com álcool: supervisionados, em local ventilado, longe de chama, sem ninguém dirigindo. Coleta com pessoas que beberam exige Comitê de Ética e termo de consentimento.
- Explicar o conceito de forma direta, com exemplo concreto.

## 10. Próximas tarefas, em ordem

Feito em paralelo, ainda sem unificar:

- coleta, ponte serial, ingestor e dashboard para o Grafana Cloud, em `applications/`;
- broker, banco, simulador, worker e servidor do modelo, em `services/`.

1. Coleta com a ponte (`applications/README.md`, "Dia de coleta") e conferência com `python -m src.cli validate`.
2. Configurar a stack do Grafana Cloud e o PDC (`applications/grafana/README.md`) e conferir o painel ao vivo pelo MQTT.
3. Análise exploratória das sessões coletadas e revisão das features e dos tempos do protocolo.
4. Rodar o experimento com dados reais e registrar no MLflow, com a análise de k-fold e overfitting. Aí o `ml/models/sob_efeito.joblib` passa a existir e o servidor em `services/` deixa de responder `sem_modelo`.
5. A equipe escolhe um dos dois contratos MQTT e a ESP32 passa a publicar (quem mantém o firmware).
6. Airflow, API e um único Compose.

Uma etapa por vez.
