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
├── reports/                  # experiment.csv, folds.csv, final.json e figuras/*.png
├── notebooks/                # Análise exploratória
├── dags/                     # DAG do Airflow; a lógica fica em src/pipeline.py
├── src/
│   ├── cli.py                # Linha de comando
│   ├── pipeline.py           # Ingestão, preparação e disponibilização
│   ├── data_validation.py    # Esquema, condições e validação
│   ├── data_io.py            # Leitura e gravação de CSVs
│   ├── features.py           # Features por sopro e conjuntos de sensores
│   ├── splitting.py          # Separação treino/teste por participante ou sessão
│   ├── train.py              # Modelos, validação cruzada aninhada (por fold) e modelo final
│   ├── figuras.py            # Matriz de confusão, ROC, barras por modelo, curva de aprendizado
│   ├── rastreio.py           # Registro no MLflow (só com MLFLOW_TRACKING_URI)
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
| `prepare` | Recorta cada sopro, tira a janela que pega o sopro anterior e equilibra as duas classes com o que cabe em cada lado | `data/processed/*.csv`, `config/split.json` |
| `train` | Compara a regra das subidas com o baseline e grava a regra (`sob_efeito` ou `sem_efeito`) | `reports/experiment.csv`, `reports/final.json`, `models/sob_efeito.joblib` |
| `predict` | Classifica um sopro de uma sessão nova | previsões na tela ou em `--output` |
| `pipeline` | Ingestão do Postgres (com `--dsn`), preparação e disponibilização | `data/processed/disponivel.json` e os CSVs do `prepare` |

Opções úteis:

- `--group-by session_file`: separa por arquivo de sessão quando há poucos participantes (são precisos pelo menos 3 grupos no treino). Com um único `participant_id`, o `prepare` já faz isso;
- `--por-classe 40`: teto opcional de tentativas de cada classe. Sem o argumento, cada lado fica com o mínimo das duas classes naquele lado;
- `--select-by recall_sob_efeito`: escolhe o modelo final pela métrica de validação cruzada desejada;
- `python -m src.cli predict --session leituras_7.csv --blow-start-s 60 --model models/sob_efeito.joblib`.

Quando chegarem dados novos, basta rodar `all` de novo: quem já estava no teste continua no teste. Para refazer o sorteio do zero, apague `config/split.json`. A bateria equilibra as duas classes em cada lado e reparte a classe maior entre os arquivos, para um CSV grande não ocupar o `sem_efeito` inteiro. `features_all.csv` guarda as tentativas sem janela sobreposta, antes desse equilíbrio.

### Pipeline no Airflow

O passo a passo da interface está no [README do repositório](../README.md). Na raiz:

```bash
docker compose up -d --build   # o Airflow e o MLflow sobem junto com o resto
```

A interface fica em http://localhost:8088 (usuário `admin`; a senha sai de `docker compose exec airflow cat /opt/airflow/standalone_admin_password.txt`). O DAG `dataset_para_treino` é manual. A ordem é ingerir, preparar, disponibilizar, treinar e testar. O resultado de cada caixa está na aba XCom. Com `MLFLOW_TRACKING_URI` definida no serviço do Airflow (no Compose, `http://mlflow:5000`), o treino e o teste também são registrados no MLflow (veja "MLflow" abaixo). O DAG não reescreve CSV de sessão e ignora rodada de simulador.

Sem a interface, de dentro de `ml/`, o comando abaixo faz só a ingestão, a preparação e o `disponivel.json`. O treino e o teste ficam no DAG, ou em `python -m src.cli train`:

```bash
python -m src.cli pipeline --dsn "$PG_DSN"   # sem --dsn, só prepara os CSVs que já estão em data/raw
```

### Como o treino avalia

- **Modelo da execução:** `regra_subida`. `sob_efeito` só quando a umidade e o MQ-3 sobem. Os limiares saem das tentativas de treino (F1 macro; empate fica com a subida maior). O `baseline` (sempre a classe mais comum) entra na comparação. Árvore e Random Forest continuam em `model_specs` para rodar fora dessa execução.
- **Sensores:** o treino e o teste usam as três subidas contra o começo do arquivo, `subidas` (`humidity_rise_comeco`, `mq135_rise_comeco`, `mq3_rise_comeco`). O começo é a mediana dos primeiros 20 s. O MQ-135 não é condição da regra. O patamar de antes do sopro fica no CSV e não entra na decisão.
- **Validação cruzada aninhada por grupo:** o laço externo avalia com participantes que o modelo não viu; o laço interno escolhe os hiperparâmetros (Grid Search) só com os demais.
- **Teste final:** usado uma única vez, para o modelo escolhido.
- **Métricas:** F1 macro, acurácia balanceada, precisão e recall de `sob_efeito` e de `sem_efeito`. O **recall de `sob_efeito`** importa mais: deixar passar quem bebeu é o erro mais grave. `roc_auc` usa a probabilidade de `sob_efeito` (`predict_proba`); o baseline não tem probabilidade útil.
- **Estabilidade:** cada métrica tem uma coluna `*_std`, o desvio padrão entre os folds externos em `reports/experiment.csv`. Desvio alto em relação à média significa que o resultado depende de quais participantes caíram no fold. As métricas de cada fold ficam em `reports/folds.csv`.
- **Over/underfitting:** `f1_macro_treino` é o F1 no próprio treino de cada fold, a ser comparado com `f1_macro` (validação). Treino muito acima da validação indica overfitting; os dois baixos, underfitting. A figura `treino_vs_validacao.png` mostra isso e `curva_aprendizado.png` mostra o F1 conforme o treino cresce, para o modelo escolhido.
- **Figuras** (`reports/figuras/`, também no MLflow): `f1_por_modelo.png` (F1 por modelo × sensores, barra de erro = desvio), `treino_vs_validacao.png`, `curva_aprendizado.png`, `matriz_confusao.png` e `roc.png` (teste, do modelo final).

### Janelas sobrepostas e vazamento entre treino e validação

O recorte ainda gera uma tentativa por amostra (ou por trio, quando a umidade é ≥ 60% ou o arquivo é de álcool). As features olham 15 s antes e 30 s depois (`BEFORE_SECONDS`/`AFTER_SECONDS` em `src/features.py`). O `prepare` fica só com a tentativa cuja janela não pega o sopro anterior, então a linha que o modelo vê não é cópia da vizinha.

Treino e teste separam pelo arquivo inteiro (`split.json`). `run_experiment` chama `checar_sessoes_nos_grupos` e recusa o treino se alguma sessão aparece em mais de um grupo.

O que conta é o número de **grupos** (`n_groups`) e de sessões (`n_sessions` em `experiment.csv`). Com poucos grupos, o desvio entre folds é grande. Cada lado da bateria usa o que os arquivos têm, com as duas classes na mesma quantidade.

### MLflow

`src/rastreio.py` só age quando `MLFLOW_TRACKING_URI` está definida; sem ela nada muda. Para testar sem servidor:

```bash
MLFLOW_TRACKING_URI=file:./mlruns python -m src.cli train
mlflow ui --backend-store-uri ./mlruns   # http://localhost:5000 (mlflow ui local, sem Compose)
```

No Docker Compose (serviço `mlflow`, mantido fora desta pasta) a URI dentro da rede é `http://mlflow:5000`, definida no serviço do Airflow, e a interface no host fica em http://localhost:5050 (a 5000 do macOS é do AirPlay); a DAG não precisa de mais nada. O experimento `sopro-seguro` ganha:

- um run pai `comparacao_de_modelos` com `experiment.csv`, `folds.csv` e as figuras de comparação como artifacts, e um run filho por (conjunto de sensores × modelo) com os params `sensor_set`, `model`, `chosen_params` e todas as métricas, inclusive `*_std`, `f1_macro_treino` e `roc_auc` (o baseline é o run de referência);
- um run `modelo_final` com o modelo (`model/`), as métricas de teste com prefixo `teste_`, `cv_score` e as figuras de matriz de confusão e ROC.

No ambiente local (`ml/requirements.txt`) a dependência é `mlflow-skinny>=2.17,<3`: o pacote completo puxa o pyarrow, que não compila no Python 3.14. No Airflow (`airflow/requirements.txt`) fica `mlflow>=2.17,<3` (imagem Python 3.12, com pyarrow). As duas séries batem com o servidor MLflow 2.17.2 do Compose e com o `scikit-learn==1.6.1`. O `airflow/Dockerfile` reinstala o scikit-learn depois, o que mantém a versão do modelo.

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
4. Rodar o treino com dados reais pelo DAG; ele registra no MLflow (http://localhost:5050).
5. As leituras ao vivo entram pelo MQTT: o ingestor grava no Postgres e o servidor do modelo (`services/mq3mqtt/ao_vivo.py`) espera `models/sob_efeito.joblib`. Quando esse arquivo existir, ele classifica com o mesmo `predict` daqui. O treino ainda não lê o banco direto: o Airflow exporta a rodada encerrada para os CSVs de `data/raw/` e o `prepare` segue a partir daí.

## Segurança

Testes com álcool devem ser controlados, seguros e supervisionados, em local ventilado e longe de chama. Nada de testes com pessoas dirigindo. A equipe de hardware deve confirmar a segurança elétrica antes de ligar os sensores ao ESP32.
