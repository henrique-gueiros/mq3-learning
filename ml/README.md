# Detector de Álcool com MQ-3 — Machine Learning

Parte de Machine Learning e dados de um projeto acadêmico de detector de álcool para carro, combinando os sensores **MQ-3**, **MQ-135** e **DHT11**.

As decisões do projeto (o que o modelo prevê, a tabela de casos, as regras e o caminho) estão resumidas em `../decisoes_projeto_ml.pdf`.

## O que o modelo prevê

Para cada **tentativa de sopro**, o modelo responde de onde vem o álcool:

| Classe | Significado |
| --- | --- |
| `sem_alcool` | Nada detectado |
| `externo` | Há álcool no ar, mas não vindo do hálito (perfume, álcool 70%, enxaguante) |
| `bebida` | O ar que veio dos pulmões tem álcool |

Isso pode ser treinado de três formas (tarefas):

- `3classes`: as três classes de uma vez;
- `etapa1`: há álcool? (`alcool` ou `sem_alcool`);
- `etapa2`: de onde vem o álcool? (`bebida` ou `externo`), só com tentativas que têm álcool.

O modelo **não** prevê embriaguez, quanto a pessoa bebeu, nem a concentração em mg/L. O MQ-3 não é um etilômetro calibrado. A classe `bebida` significa "álcool no hálito nas condições do experimento".

## Escopo

Este repositório cobre apenas ML e dados. O firmware da ESP32 fica em `../firmware/`. Fora do escopo: o que o carro faz com cada resposta.

## Estado atual

O pipeline está pronto e testado e lê diretamente os CSVs gravados pelo firmware: validação, recorte de cada sopro, features, separação treino/teste por participante, comparação de modelos, experimento por conjunto de sensores, modelo final e previsão. **Os dados de treino e teste são coletados pela própria equipe**; o projeto não usa datasets da internet nem dados sintéticos.

| Item | Situação |
| --- | --- |
| Leitura de MQ-3, MQ-135 e DHT11 no firmware, com CSV por sessão | Funcionando |
| Tensão de saída dos MQ e compatibilidade com o ADC do ESP32 | O ADC satura perto de 3,1 V (ver `firmware/README.md`) |
| Protocolo de sopro (tempos das fases) | Proposta inicial; ajustar com os dados reais |
| Coleta rotulada (sessões + `attempts.csv`) | Em andamento |
| Classe `bebida` (simulador de hálito ou coleta aprovada pelo Comitê de Ética) | A definir com o professor |
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
| `clean` | `sem_alcool` |
| `perfume` | `externo` |
| `alcohol70_spray` | `externo` |
| `alcohol70_hands` | `externo` |
| `mouthwash` | `externo` |
| `alcohol_cup` | `externo` |
| `drink` | `bebida` |
| `drink_perfume` | `bebida` |

O rótulo vem **da condição experimental**, nunca do valor dos sensores. Para acrescentar condições, edite `CONDITIONS` em `src/data_validation.py`.

## Features por sopro

Para cada sensor (MQ-3, MQ-135, umidade e temperatura): valor antes do sopro, pico, subida, tempo até o pico e tempo de recuperação. Também há a proporção entre as subidas do MQ-135 e do MQ-3 e o atraso entre o pico do MQ-3 e o de umidade. Os detalhes estão em `src/features.py`. Essas features são o ponto de partida e devem ser revistas na análise exploratória.

## Estrutura

```text
ml/
├── config/split.json         # Criado pelo 'prepare': quem é de treino e quem é de teste
├── data/
│   ├── raw/                  # Dados reais originais (nunca alterados pelo código)
│   │   ├── sessions/*.csv    # CSVs do firmware
│   │   └── attempts.csv      # Um sopro por linha
│   └── processed/            # features_all.csv, train.csv, test.csv
├── models/                   # Modelos treinados (.joblib + .json)
├── reports/                  # Resultados do experimento e do teste final
├── notebooks/                # Análise exploratória
├── src/
│   ├── cli.py                # Linha de comando
│   ├── data_validation.py    # Esquema, condições e validação
│   ├── data_io.py            # Leitura e gravação de CSVs
│   ├── features.py           # Features por sopro, conjuntos de sensores e tarefas
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
| `train` | Para cada tarefa: compara 4 modelos em 4 conjuntos de sensores e treina o melhor | `reports/experiment_<tarefa>.csv`, `reports/final_<tarefa>.json`, `models/<tarefa>.joblib` |
| `predict` | Classifica um sopro de uma sessão nova | previsões na tela ou em `--output` |

Opções úteis:

- `--group-by session_file`: separa por arquivo de sessão quando há poucos participantes (são precisos pelo menos 3 grupos no treino);
- `--task etapa2`: treina só uma tarefa;
- `--select-by recall_bebida`: escolhe o modelo final pela métrica de validação cruzada desejada;
- `python -m src.cli predict --session leituras_7.csv --blow-start-s 60 --model models/3classes.joblib`.

Quando chegarem dados novos, basta rodar `all` de novo: quem já estava no teste continua no teste. Para refazer o sorteio do zero, apague `config/split.json`.

### Como o treino avalia

- **Modelos:** `baseline` (sempre a classe mais comum), regressão logística, árvore de decisão e Random Forest.
- **Conjuntos de sensores:** `mq3`, `mq3+mq135`, `mq3+dht11`, `mq3+mq135+dht11`. Comparar os conjuntos mostra o quanto cada sensor ajuda.
- **Validação cruzada aninhada por grupo:** o laço externo avalia com participantes que o modelo não viu; o laço interno escolhe os hiperparâmetros (Grid Search) só com os demais.
- **Teste final:** usado uma única vez, para o modelo escolhido de cada tarefa.
- **Métricas:** F1 macro, acurácia balanceada, precisão e recall por classe. O **recall de `bebida`** é a métrica mais importante: deixar passar quem bebeu é o erro mais grave.

## Limitações

- Com poucos participantes, as métricas variam muito; não exagere as conclusões.
- A classe `bebida` depende de um simulador de hálito ou de coleta com pessoas que beberam (aprovação do Comitê de Ética). Um simulador não reproduz CO₂ nem a variação entre pessoas.
- `mouthwash` (enxaguante) produz álcool real na boca e tende a ser confundido com `bebida`.
- O DHT11 é lento e pouco preciso; a subida de umidade pode demorar alguns segundos depois do sopro.
- Os sensores MQ variam com temperatura, umidade e tempo de aquecimento; registre o aquecimento nas notas.

## Próximos passos

1. Coletar as condições seguras (`clean`, `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash`, `alcohol_cup`) com vários participantes, cadastrando cada sopro em `attempts.csv`.
2. Definir com o professor como obter a classe `bebida`.
3. Análise exploratória em `notebooks/01_eda.ipynb` e revisão das features e dos tempos do protocolo.
4. Registrar os experimentos no MLflow.
5. Quando as leituras chegarem por MQTT e forem gravadas no banco, ler as sessões de lá (no lugar dos CSVs) e orquestrar `prepare` e `train` no Airflow. O formato das leituras continua o mesmo do firmware.

## Segurança

Testes com álcool devem ser controlados, seguros e supervisionados, em local ventilado e longe de chama. Nada de testes com pessoas dirigindo. A equipe de hardware deve confirmar a segurança elétrica antes de ligar os sensores ao ESP32.
