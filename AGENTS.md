# AGENTS.md — Detector de Álcool com MQ-3

## 1. Papel deste arquivo

Este arquivo orienta o Cursor e outros agentes a continuar o projeto acadêmico de detector de álcool. O resumo das decisões (classes, sensores, casos, regras e caminho) está em `decisoes_projeto_ml.pdf`; o uso do pipeline, em `ml/README.md`.

Trabalhe incrementalmente, explique decisões importantes e não trate hipóteses experimentais como fatos. A equipe está aprendendo; prefira código claro, modular e didático.

Antes de mudanças grandes, inspecione o repositório e preserve o que já existe. O firmware em `firmware/` é mantido por outro integrante: não o reescreva sem necessidade.

## 2. Contexto

- Detector de álcool para carro, acadêmico.
- Hardware funcionando: **ESP32** (`esp32dev`, Arduino/PlatformIO) com **MQ-3** (GPIO 34), **MQ-135** (GPIO 35) e **DHT11** (GPIO 4). O firmware lê cerca de 1 vez por segundo e grava um CSV por sessão.
- O que o sistema faz depois de uma detecção (alerta, bloqueio) ainda não foi decidido e não é decisão do modelo.
- **Só dados coletados pela equipe.** Não usar datasets da internet nem dados sintéticos. Os dados de treino e de teste vêm das sessões gravadas pelo firmware.
- O ADC da ESP32 satura perto de 3,1 V; leituras muito altas dos MQ ficam achatadas (ver `firmware/README.md`).

## 3. O que o modelo prevê

Cada **tentativa de sopro** recebe uma classe:

| Classe | Significado |
| --- | --- |
| `sem_alcool` | Nada detectado |
| `externo` | Álcool no ar, mas não vindo do hálito (perfume, álcool 70%, enxaguante) |
| `bebida` | O ar que veio dos pulmões tem álcool |

O mesmo problema é treinado de três formas: `3classes` (as três de uma vez), `etapa1` (há álcool?) e `etapa2` (bebida ou externo, só quando há álcool).

O modelo **não** prevê embriaguez, quantidade ingerida nem concentração em mg/L. A classe `bebida` significa "álcool no hálito nas condições do experimento".

A tabela de casos esperados (perfume, álcool 70% borrifado, enxaguante, caso misto) está no PDF e são **hipóteses** a confirmar na análise exploratória. O que separa bebida de álcool externo é o álcool **subir durante o sopro**, partindo de um ambiente sem álcool. "Valor alto demais" não é critério.

## 4. Estado atual

Pronto e testado:

- Firmware lendo os três sensores e gravando CSV por sessão (`firmware/src/main.cpp`, `firmware/monitor/filter_leituras.py`).
- Pipeline de ML em `ml/src/`, que lê esses CSVs sem alterá-los: validação, recorte de cada sopro, features, separação treino/teste por participante, comparação de modelos, modelo final e previsão. Comandos em `ml/README.md`.

Ainda não existe:

- [ ] Coleta rotulada suficiente (sessões + `ml/data/raw/attempts.csv` preenchido pela equipe).
- [ ] Definição, com o professor, de como obter a classe `bebida` (simulador de hálito ou coleta aprovada pelo Comitê de Ética).
- [ ] Análise exploratória e revisão das features com dados reais.
- [ ] Modelo treinado e avaliado com dados reais. Métricas dos testes automatizados usam curvas montadas à mão e **não** dizem nada sobre o sensor.
- [ ] MLflow, MQTT, banco de dados, Airflow, serviço de inferência, API, dashboard e Docker Compose.

Não inventar calibração, limites de detecção ou valores típicos dos sensores, e não afirmar que um entregável está pronto antes de estar implementado e testado.

## 5. Dados

### 5.1 Sessões — `ml/data/raw/sessions/*.csv`

Cópias **sem edição** dos CSVs do firmware. Cada arquivo vai do ligar ao reiniciar da placa. Como a numeração recomeça em cada placa, renomear ao copiar para um nome único (por exemplo `2026-11-04_p01_leituras_3.csv`).

| Coluna | Uso |
| --- | --- |
| `t_ms` | Tempo em ms desde a partida (obrigatório) |
| `mq3_raw`, `mq135_raw`, `temperature_c`, `humidity_pct` | Leituras usadas nas features. O DHT11 fica vazio nos primeiros segundos |
| `amostra`, `ppm`, `mq135_mv`, `alcool` | **Nunca usar.** `ppm` e `alcool` são calculados pelo firmware a partir do próprio MQ-3; usá-los como rótulo ou feature ensina a regra do firmware, não o problema |

### 5.2 Sopros — `ml/data/raw/attempts.csv`

Uma linha por sopro, preenchida por quem conduz o experimento (modelo em `ml/templates/attempts_template.csv`): `attempt_id`, `session_file`, `participant_id` (anônimo), `condition`, `blow_start_s` (segundo da sessão em que o sopro começou) e, opcionalmente, `blow_end_s`, `reference_mg_l` e `notes`.

O rótulo vem da `condition`, nunca dos sensores:

| Condição | Classe |
| --- | --- |
| `clean` | `sem_alcool` |
| `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash`, `alcohol_cup` | `externo` |
| `drink`, `drink_perfume` | `bebida` |

Novas condições entram em `CONDITIONS`, em `ml/src/data_validation.py`.

### 5.3 Recorte e features

`assign_phases` recorta 15 s antes do sopro (`before`), o sopro (`blow`, 5 s se `blow_end_s` estiver vazio) e 30 s depois (`after`). Dois sopros da mesma sessão precisam de cerca de 50 s de intervalo. As features (antes, pico, subida, tempo até o pico, recuperação, proporção MQ-135/MQ-3 e atraso entre o pico do MQ-3 e o da umidade) estão em `ml/src/features.py` e devem ser revistas depois da análise exploratória.

## 6. Entregáveis da disciplina

1. **Dataset inicial:** coleta própria, CSVs do firmware e `attempts.csv`; publicação por MQTT com gravação em banco (hoje os CSVs cumprem a coleta; MQTT ainda não existe).
2. **EDA** em `ml/notebooks/`, com a lógica reutilizável permanecendo em `ml/src/`.
3. **Pipeline** de validação, limpeza e preparação, reprodutível (`python -m src.cli prepare`).
4. **Baseline, três modelos, Grid Search, validação cruzada por grupo e métricas**, já estruturados em `ml/src/train.py`; falta rodar com dados reais e registrar no **MLflow**. Métricas: F1 macro, acurácia balanceada, precisão e recall por classe, matriz de confusão. A prioridade é o **recall de `bebida`**: deixar passar quem bebeu é o erro mais grave.
5. **Inferência** com o mesmo pré-processamento do treino (já é um `Pipeline` do scikit-learn).
6. **Integração:** Airflow orquestra a preparação e o treino; um serviço consome as leituras, classifica e publica o resultado; dashboard e API exibem.
7. **Docker Compose** sobe broker MQTT, banco, MLflow, Airflow, API e dashboard com um comando.

## 7. MQTT (direção acordada, ainda não implementada)

A ESP publica; não envia direto ao servidor do modelo. Um broker (Mosquitto) entrega cópias a quem assina.

| Tópico | Quem publica | Conteúdo |
| --- | --- | --- |
| `mq3/<placa>/leituras` | ESP32 | Uma mensagem por leitura, com os mesmos campos do CSV |
| `mq3/<placa>/eventos` | ESP32 | `sopro_inicio` e `sopro_fim`, para não depender de anotar o segundo à mão |
| `mq3/<placa>/status` | ESP32 | `online`/`offline` |
| `mq3/<placa>/resultado` | serviço de inferência | Classe e probabilidades |

Um serviço assina `leituras` e `eventos` e grava num PostgreSQL, ignorando repetidas (mesma placa, sessão e amostra). O formato é o mesmo do CSV, então o código de ML não muda quando a fonte passar de arquivo para banco: muda só a leitura dos dados. Para desenvolver sem a placa, um simulador publica um CSV do firmware linha a linha. A ESP e o broker precisam estar na mesma rede.

## 8. Estrutura e estilo

```text
firmware/                 # ESP32 (PlatformIO); não reescrever sem necessidade
ml/
├── data/raw/sessions/    # CSVs do firmware, sem edição (não versionados)
├── data/raw/attempts.csv # um sopro por linha (não versionado)
├── data/processed/       # features, train e test (não versionados)
├── config/split.json     # separação treino/teste; versionado
├── models/  reports/  notebooks/
├── src/                  # data_validation, data_io, features, splitting, train, inference, cli
├── tests/  templates/  requirements.txt
decisoes_projeto_ml.pdf
```

Python com numpy, pandas, scikit-learn, matplotlib, seaborn e jupyter (versões em `ml/requirements.txt`). MLflow, MQTT e banco entram quando o entregável correspondente for implementado. Não criar outro gerenciador de ambiente: o existente é `ml/.venv`.

- Código simples, com tipos e docstrings nas funções públicas; testes para validação, features e treino.
- Separar treino e teste **por participante** (`participant_id`) ou, com poucos participantes, por arquivo de sessão. Nunca misturar a mesma pessoa nos dois lados, nem dividir leituras de um sopro entre treino e teste.
- Escolher hiperparâmetros só dentro do treino (a validação cruzada aninhada por grupo já faz isso) e usar o teste uma única vez.
- Não salvar dados derivados por cima dos brutos, nem versionar `.venv/`, credenciais, dados pessoais ou os CSVs de sessão.
- Não usar caminhos absolutos da máquina de alguém.

## 9. Regras para o agente

- Trabalhar em etapas pequenas; ao terminar, dizer o que mudou, como executar e o que foi testado.
- Inspecionar o repositório antes de criar algo novo.
- Não reintroduzir gerador sintético nem dataset da internet.
- Não usar `ppm` nem `alcool` do firmware como rótulo ou feature.
- Não apresentar métricas dos testes automatizados como desempenho real.
- Não inventar medições, calibração, resultados ou fontes.
- Não adicionar horário ou dia da semana como preditor sem justificativa e avaliação.
- Testes com álcool: supervisionados, em local ventilado, longe de chama, sem ninguém dirigindo. Coleta com pessoas que beberam exige Comitê de Ética e termo de consentimento.
- Explicar o conceito de forma direta, com exemplo concreto.

## 10. Próximas tarefas, em ordem

1. Análise exploratória das sessões já gravadas e revisão das features e dos tempos do protocolo.
2. Apoiar a coleta: conferir `attempts.csv` e os CSVs copiados (`python -m src.cli validate`).
3. Base do MQTT: Mosquitto e PostgreSQL no Docker Compose, simulador que publica um CSV do firmware, e serviço que grava no banco. A publicação pela ESP32 fica com quem mantém o firmware.
4. Rodar o experimento com dados reais e registrar no MLflow.
5. Airflow, serviço de inferência, API, dashboard e o Compose completo.

Não implementar essas etapas todas de uma vez.
