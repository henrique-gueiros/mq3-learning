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

Este repositório cobre apenas ML e dados. Fora do escopo: firmware do ESP32, infraestrutura do dispositivo e o que o carro faz com cada resposta.

## Estado atual

O pipeline está pronto e testado: validação, features por sopro, separação treino/teste por participante, comparação de modelos, experimento por conjunto de sensores, modelo final e previsão. **Não há dados reais ainda**, e o projeto não usa dados sintéticos.

| Item | Situação |
| --- | --- |
| Sensores (MQ-3, MQ-135, DHT11) e ligação no ESP32 | A confirmar com a equipe de hardware |
| Tensão de saída dos MQ e compatibilidade com o ADC do ESP32 | Não verificada |
| Protocolo de sopro (tempos das fases) | Proposta inicial; ajustar após os primeiros testes |
| Primeiras leituras reais | Não coletadas |
| Classe `bebida` (simulador de hálito ou coleta aprovada pelo Comitê de Ética) | A definir com o professor |
| Modelo treinado com dados reais | Não existe |

Nenhuma especificação de hardware, calibração ou valor típico dos sensores está assumida neste repositório.

## Formato dos dados

Os dados reais ficam em dois tipos de arquivo, com modelos em `templates/`.

### Leituras — `data/raw/readings/*.csv`

Uma linha por leitura dos sensores, gravada pelo sistema de aquisição. Pode haver vários arquivos (por exemplo, um por dia de coleta).

| Coluna | Descrição |
| --- | --- |
| `timestamp` | ISO 8601 **com fuso**, ex.: `2026-10-20T14:00:00-03:00` |
| `attempt_id` | Identificador da tentativa de sopro |
| `phase` | `before` (ambiente), `blow` (sopro) ou `after` (recuperação) |
| `mq3_raw` | Leitura bruta do MQ-3 (obrigatória) |
| `mq135_raw` | Leitura bruta do MQ-135 (pode ficar vazia) |
| `temperature_c` | Temperatura do DHT11 (pode ficar vazia) |
| `humidity_pct` | Umidade do DHT11 (pode ficar vazia) |

A fase é marcada pelo sistema de aquisição seguindo o protocolo (por exemplo, um LED ou som indica "sopre agora"). As leituras são brutas: nenhuma conversão para concentração é feita.

### Tentativas — `data/raw/attempts.csv`

Uma linha por tentativa, preenchida por quem conduz o experimento.

| Coluna | Descrição |
| --- | --- |
| `attempt_id` | O mesmo das leituras |
| `participant_id` | Identificador anônimo da pessoa (ex.: `p01`) |
| `session_id` | Identificador da sessão (ex.: `2026-10-25-manha`) |
| `condition` | O que foi feito antes do sopro (tabela abaixo) |
| `reference_mg_l` | Opcional: leitura de um etilômetro de referência |
| `notes` | Opcional: observações |

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
│   │   ├── readings/*.csv
│   │   └── attempts.csv
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
├── templates/                # Cabeçalhos dos CSVs de leituras e tentativas
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

1. Salve as leituras em `data/raw/readings/` e cadastre as tentativas em `data/raw/attempts.csv`.
2. Rode, de dentro de `ml/`:

   ```bash
   python -m src.cli validate   # confere os arquivos e mostra quantas tentativas há por condição
   python -m src.cli all        # prepare + train
   ```

| Comando | O que faz | Gera |
| --- | --- | --- |
| `validate` | Confere leituras e tentativas e lista todos os problemas de uma vez | nada |
| `prepare` | Calcula as features de cada sopro e separa treino/teste por participante | `data/processed/*.csv`, `config/split.json` |
| `train` | Para cada tarefa: compara 4 modelos em 4 conjuntos de sensores e treina o melhor | `reports/experiment_<tarefa>.csv`, `reports/final_<tarefa>.json`, `models/<tarefa>.joblib` |
| `predict` | Classifica tentativas novas | previsões na tela ou em `--output` |

Opções úteis:

- `--group-by session_id`: separa por sessão quando há poucos participantes (são precisos pelo menos 3 grupos no treino);
- `--task etapa2`: treina só uma tarefa;
- `--select-by recall_bebida`: escolhe o modelo final pela métrica de validação cruzada desejada;
- `python -m src.cli predict --readings novas.csv --model models/3classes.joblib`.

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

1. Confirmar o hardware e o protocolo de sopro com a equipe.
2. Coletar as condições seguras (`clean`, `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash`, `alcohol_cup`) com vários participantes.
3. Definir com o professor como obter a classe `bebida`.
4. Análise exploratória em `notebooks/01_eda.ipynb` e revisão das features.
5. Registrar os experimentos no MLflow.

## Segurança

Testes com álcool devem ser controlados, seguros e supervisionados, em local ventilado e longe de chama. Nada de testes com pessoas dirigindo. A equipe de hardware deve confirmar a segurança elétrica antes de ligar os sensores ao ESP32.
