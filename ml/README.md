# Detector de Álcool com MQ-3 — Machine Learning

Parte de Machine Learning e dados de um projeto acadêmico de detector de álcool para carro, combinando os sensores **MQ-3**, **MQ-135** e **DHT11**.

O passo a passo da coleta, do treino e do MQTT está no [README do repositório](../README.md). As decisões antigas estão em `../docs/decisoes_projeto_ml.pdf` (esse PDF ainda descreve três classes; vale a tabela abaixo).

## O que o modelo prevê

Para cada **tentativa de sopro**, o modelo responde só isto:

| Classe | Significado |
| --- | --- |
| `sob_efeito` | A pessoa bebeu (`drink`) |
| `sem_efeito` | A pessoa não bebeu: ar limpo, perfume, álcool em gel, borrifo ou enxaguante |

Perfume e álcool em gel **não** são `sob_efeito`. Eles entram na coleta justamente para o modelo aprender a não marcar essas situações como motorista sob efeito. O modelo não mede concentração em mg/L e não é um etilômetro calibrado. A classe `sob_efeito` significa "bebeu nas condições do experimento".

## Escopo

Este repositório cobre apenas ML e dados. O firmware da ESP32 fica em `../esp32-esp8266/`. Fora do escopo: o que o carro faz com cada resposta.

## Estado atual

O pipeline está pronto e testado e lê diretamente os CSVs gravados pelo firmware: validação, recorte de cada sopro, features, separação treino/teste por participante, comparação de modelos, experimento por conjunto de sensores, modelo final e previsão. **Os dados de treino e teste são coletados pela própria equipe**; o projeto não usa datasets da internet nem dados sintéticos.

| Item | Situação |
| --- | --- |
| Leitura de MQ-3, MQ-135 e DHT11 no firmware, com CSV por sessão | Funcionando |
| Tensão de saída dos MQ e compatibilidade com o ADC do ESP32 | O ADC satura perto de 3,1 V (ver `esp32-esp8266/README.md`) |
| Protocolo de sopro (tempos das fases) | Proposta inicial; ajustar com os dados reais |
| Coleta rotulada (sessões + `attempts.csv`) | Em andamento |
| Coleta das duas classes (bebeu e não bebeu, incluindo perfume e álcool em gel) | Em andamento |
| Modelo treinado com dados reais | Não existe |

Nenhuma calibração ou valor típico dos sensores está assumido neste repositório.

## Formato dos dados

Os dados reais ficam em dois tipos de arquivo.

### Sessões — `data/raw/sessions/*.csv`

Os CSVs gravados pelo firmware (`leituras_<n>.csv`), copiados **sem alteração**. Cada arquivo é uma sessão: do ligar ao desligar (ou reiniciar) da placa, com uma leitura a cada ~1 s.

| Coluna | Uso no ML |
| --- | --- |
| `t_ms` | Tempo desde a partida da placa (obrigatório) |
| `mq3_raw` | Leitura bruta do MQ-3 (obrigatória) |
| `mq135_raw` | Leitura bruta do MQ-135 |
| `temperature_c`, `humidity_pct` | DHT11 (vazios nos primeiros segundos) |
| `amostra`, `ppm`, `mq135_mv`, `alcool` | **Não usadas.** `ppm` e `alcool` são calculados pelo firmware a partir do próprio MQ-3, com o ar da partida como referência; usá-los como rótulo ou feature misturaria a regra do firmware com o modelo. |

Como o firmware reinicia a numeração em cada placa, **renomeie o arquivo ao copiar**, para que o nome seja único: por exemplo `2026-11-04_henrique_leituras_3.csv`.

### Tentativas — `data/raw/attempts.csv`

Uma linha por sopro, preenchida por quem conduz o experimento (modelo em `templates/attempts_template.csv`). Uma sessão pode ter vários sopros.

Nos arquivos de bebida desta coleta (o nome tem "alcool", ou o lote aponta uma origem com "alcool"), o `prepare` reescreve as tentativas: três amostras seguidas são um sopro, e o trio fica de fora se algum PPM está vazio ou abaixo de 0,6. O PPM só descarta o trio; a classe continua sendo `drink` porque o arquivo já é de bebida. `ppm` não vira feature.

Nos outros arquivos, o mesmo `prepare` usa a umidade só para recortar. Hipótese desta coleta: 60% ou mais parece sopro (três amostras seguidas); abaixo disso, ou com umidade vazia, cada amostra é uma linha. Perfume, ar limpo, álcool na mão e enxaguante entram todos como `sem_efeito`. A umidade não decide se a pessoa bebeu. No `attempts.csv` que o `prepare` grava, a coluna `condition` fica só com `sem_efeito` ou `sob_efeito`.

| Coluna | Descrição |
| --- | --- |
| `attempt_id` | Identificador único do sopro (ex.: `p01-perfume-1`) |
| `session_file` | Nome do CSV da sessão em `data/raw/sessions/` |
| `participant_id` | Identificador anônimo da pessoa (ex.: `p01`) |
| `condition` | O que foi feito antes do sopro (tabela abaixo) |
| `blow_start_s` | Segundo da sessão em que o sopro começou (`t_ms / 1000`, visto no monitor serial) |
| `blow_end_s` | Opcional: segundo em que o sopro terminou (padrão: início + 5 s) |
| `reference_mg_l` | Opcional: leitura de um etilômetro de referência |
| `notes` | Opcional: observações |

O ML recorta de cada sessão os **15 s antes** do sopro (ambiente), o **sopro** e os **30 s depois** (pico e recuperação). Deixe pelo menos ~50 s entre dois sopros da mesma sessão; senão o `prepare` avisa que o "antes" de um pega o sopro do outro. Esses tempos ficam em `src/features.py`.

| `condition` | Classe |
| --- | --- |
| `clean` | `sem_efeito` |
| `perfume` | `sem_efeito` |
| `alcohol70_spray` | `sem_efeito` |
| `alcohol70_hands` | `sem_efeito` |
| `mouthwash` | `sem_efeito` |
| `drink` | `sob_efeito` |

O rótulo vem **da condição experimental**, nunca do valor dos sensores. Para acrescentar condições, edite `CONDITIONS` em `src/data_validation.py`.

## Features por sopro

Para cada sensor (MQ-3, MQ-135 e umidade; a temperatura é lida, mas não entra nas features): valor antes do sopro, pico, subida, tempo até o pico e tempo de recuperação. Também há a proporção entre as subidas do MQ-135 e do MQ-3 e o atraso entre o pico do MQ-3 e o de umidade. Os detalhes estão em `src/features.py`. Essas features são o ponto de partida e devem ser revistas na análise exploratória.

## Estrutura

```text
ml/
├── config/split.json         # Criado pelo 'prepare': quem é de treino e quem é de teste
├── data/
│   ├── raw/                  # Sessões e tentativas. CSV de sessão existente não é reescrito
│   │   ├── sessions/*.csv    # CSVs do firmware
│   │   └── attempts.csv      # Um sopro por linha
│   └── processed/            # features_all.csv, train.csv, test.csv, disponivel.json
├── models/                   # Modelos treinados (.joblib + .json)
├── reports/                  # Resultados do experimento e do teste final
├── notebooks/                # Análise exploratória
├── dags/                     # DAG do Airflow; a lógica fica em src/pipeline.py
├── src/
│   ├── cli.py                # Linha de comando
│   ├── pipeline.py           # Ingestão, preparação e disponibilização
│   ├── data_validation.py    # Esquema, condições e validação
│   ├── data_io.py            # Leitura e gravação de CSVs
│   ├── features.py           # Features por sopro e conjuntos de sensores
│   ├── splitting.py          # Separação treino/teste por participante ou sessão
│   ├── train.py              # Modelos, validação cruzada aninhada e modelo final
│   ├── inference.py          # Previsão para tentativas novas
│   └── paths.py              # Caminhos padrão
├── templates/                # Cabeçalho do attempts.csv
├── tests/                    # Testes automatizados (pytest)
├── requirements.txt
└── pytest.ini
```

O conteúdo de `data/` e `models/` não é versionado no Git (veja `.gitignore`). `config/` e `reports/` são versionados, para que toda a equipe use a mesma separação e veja os mesmos resultados.

## Ambiente

```bash
cd ml
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest        # roda os testes
```

## Como usar

1. Copie os CSVs do firmware para `data/raw/sessions/` (com nome único) e cadastre cada sopro em `data/raw/attempts.csv`.
2. Rode, de dentro de `ml/`:

   ```bash
   python -m src.cli validate   # confere os arquivos e mostra quantas tentativas há por condição
   python -m src.cli all        # prepare + train
   ```

| Comando | O que faz | Gera |
| --- | --- | --- |
| `validate` | Confere sessões e tentativas e lista todos os problemas de uma vez | nada |
| `prepare` | Recorta cada sopro, calcula as features e separa treino/teste por participante | `data/processed/*.csv`, `config/split.json` |
| `train` | Compara 4 modelos em 4 conjuntos de sensores e treina o melhor (`sob_efeito` ou `sem_efeito`) | `reports/experiment.csv`, `reports/final.json`, `models/sob_efeito.joblib` |
| `predict` | Classifica um sopro de uma sessão nova | previsões na tela ou em `--output` |
| `pipeline` | Ingestão do Postgres (com `--dsn`), preparação e disponibilização | `data/processed/disponivel.json` e os CSVs do `prepare` |

Opções úteis:

- `--group-by session_file`: separa por arquivo de sessão quando há poucos participantes (são precisos pelo menos 3 grupos no treino);
- `--select-by recall_sob_efeito`: escolhe o modelo final pela métrica de validação cruzada desejada;
- `python -m src.cli predict --session leituras_7.csv --blow-start-s 60 --model models/sob_efeito.joblib`.

Quando chegarem dados novos, basta rodar `all` de novo: quem já estava no teste continua no teste. Para refazer o sorteio do zero, apague `config/split.json`.

### Pipeline no Airflow

O mesmo `prepare` também roda sozinho, depois de buscar no Postgres da coleta as rodadas que ainda não estão em `data/raw/`:

```bash
python -m src.cli pipeline --dsn "$PG_DSN"   # sem --dsn, só prepara os CSVs que já estão em data/raw
```

Isso grava `data/processed/disponivel.json` quando o dataset está pronto para o `train`. A ordem (ingestão, preparação, disponibilização) é o DAG `dataset_para_treino`. Na raiz do repositório:

```bash
docker compose --profile airflow up -d --build
```

A interface fica em http://localhost:8088. O usuário é `admin` e a senha está em `standalone_admin_password.txt` dentro do contêiner (`docker compose exec airflow cat /opt/airflow/standalone_admin_password.txt`). O DAG não reescreve CSV de sessão e ignora rodada de simulador. O treino em si continua no comando `train` (o MLflow ainda não entra aqui).

### Como o treino avalia

- **Modelos:** `baseline` (sempre a classe mais comum), regressão logística, árvore de decisão e Random Forest.
- **Conjuntos de sensores:** `mq3`, `mq3+mq135`, `mq3+dht11`, `mq3+mq135+dht11`. Comparar os conjuntos mostra o quanto cada sensor ajuda.
- **Validação cruzada aninhada por grupo:** o laço externo avalia com participantes que o modelo não viu; o laço interno escolhe os hiperparâmetros (Grid Search) só com os demais.
- **Teste final:** usado uma única vez, para o modelo escolhido.
- **Métricas:** F1 macro, acurácia balanceada, precisão e recall de `sob_efeito` e de `sem_efeito`. O **recall de `sob_efeito`** importa mais: deixar passar quem bebeu é o erro mais grave.

## Limitações

- Com poucos participantes, as métricas variam muito; não exagere as conclusões.
- Perfume, álcool em gel, borrifo e enxaguante são `sem_efeito`. Sem esses exemplos na coleta, o modelo tende a marcar qualquer vapor de álcool como motorista sob efeito.
- Coleta com pessoas que beberam exige aprovação do Comitê de Ética. Um simulador de hálito não reproduz a variação entre pessoas.
- O DHT11 é lento e pouco preciso; a subida de umidade pode demorar alguns segundos depois do sopro.
- Os sensores MQ variam com temperatura, umidade e tempo de aquecimento; registre o aquecimento nas notas.

## Próximos passos

1. Coletar as condições seguras (`clean`, `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash`) com vários participantes, cadastrando cada sopro em `attempts.csv`.
2. Coletar as duas classes: quem bebeu (`sob_efeito`) e quem não bebeu, incluindo perfume e álcool em gel (`sem_efeito`).
3. Análise exploratória em `notebooks/01_eda.ipynb` e revisão das features e dos tempos do protocolo.
4. Registrar os experimentos no MLflow.
5. As leituras ao vivo entram pelo MQTT em `services/`: o worker grava no Postgres e o servidor do modelo espera `models/sob_efeito.joblib`. Quando esse arquivo existir, ele classifica com o mesmo `predict` daqui. O treino ainda não lê o banco direto: o Airflow exporta a rodada encerrada para os CSVs de `data/raw/` e o `prepare` segue a partir daí.

## Segurança

Testes com álcool devem ser controlados, seguros e supervisionados, em local ventilado e longe de chama. Nada de testes com pessoas dirigindo. A equipe de hardware deve confirmar a segurança elétrica antes de ligar os sensores ao ESP32.
