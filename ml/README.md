# Detector de Álcool com MQ-3 — Machine Learning

Parte de Machine Learning e dados de um projeto acadêmico de detector de álcool para carro, usando o sensor MQ-3.

## Objetivo

Classificar uma observação do sensor como:

- `0`: álcool não detectado nas condições do experimento;
- `1`: álcool detectado nas condições do experimento.

Essa classificação indica **detecção de álcool nas condições avaliadas**. Ela não comprova que o motorista consumiu álcool, está intoxicado ou está inapto a dirigir.

## Escopo

Este repositório cobre apenas ML e dados: aquisição e armazenamento do dataset, análise exploratória, preparação, treino, avaliação, registro de experimentos e interface de inferência.

Fora do escopo: firmware do ESP32, infraestrutura do dispositivo e a lógica final do veículo após uma detecção (que ainda não foi decidida).

## Estado atual

O pipeline de dados está pronto e testado: validação, separação treino/teste por sessão, estimativa do gerador sintético, geração e montagem dos conjuntos finais. Ainda não existem dados reais nem modelos treinados.

| Item | Situação |
| --- | --- |
| Modelo exato do ESP32 | Não confirmado |
| Tipo de saída do módulo MQ-3 (analógica/digital) | Não confirmado |
| Tensão de saída e compatibilidade com o ADC do ESP32 | Não verificada |
| Método e frequência de aquisição | Não definidos |
| Primeiras leituras reais | Não coletadas |
| Procedimento experimental e fonte dos rótulos | Não definidos |
| Dataset público relevante | Não pesquisado |
| Dataset sintético | Gerador pronto; parâmetros reais dependem das primeiras leituras |
| Modelo treinado ou validado com dados reais | Não existe |

Nenhuma especificação de hardware, calibração, limite de detecção ou valor típico do sensor está assumida neste repositório.

## Limitações

- Sem leituras reais, qualquer resultado obtido aqui serve apenas para testar o código.
- Dados sintéticos, quando existirem, serão identificados com `source="synthetic"`. Métricas obtidas só com eles não indicam desempenho real.
- `sensor_raw` é a leitura bruta do sistema de aquisição. Ela não é concentração de álcool, porque não há calibração.
- Os rótulos nunca serão derivados do próprio valor do MQ-3; eles devem vir de um procedimento experimental de referência.

## Estrutura

```text
ml/
├── config/
│   ├── synthetic_didactic.json   # Parâmetros INVENTADOS, só para testar o código
│   ├── synthetic_estimated.json  # Criado pelo 'estimate' a partir do treino real
│   └── split_sessions.json       # Criado pelo 'split': quais sessões são de teste
├── data/
│   ├── raw/          # Leituras reais originais (nunca alteradas pelo código)
│   ├── synthetic/    # Dados simulados, identificados como sintéticos
│   └── processed/    # real_train, real_test, train e test
├── notebooks/        # Análise exploratória e experimentos
├── src/
│   ├── cli.py                   # Linha de comando que executa as etapas
│   ├── data_validation.py       # Esquema e validação das leituras
│   ├── data_io.py               # Leitura e gravação de CSVs
│   ├── splitting.py             # Separação treino/teste por sessão
│   ├── parameter_estimation.py  # Estima o gerador a partir do treino real
│   ├── data_generation.py       # Gerador sintético
│   ├── preprocessing.py         # Conjuntos finais e features (X, y, groups)
│   └── paths.py                 # Caminhos padrão
├── templates/
│   └── leituras_template.csv    # Cabeçalho do CSV de leituras reais
├── models/           # Artefatos treinados
├── tests/            # Testes automatizados (pytest)
├── requirements.txt
├── pytest.ini
├── .gitignore
└── README.md
```

Por padrão, o conteúdo de `data/` e `models/` não é versionado no Git (veja `.gitignore`). Se a equipe decidir versionar leituras reais, ajuste o `.gitignore` explicitamente. A pasta `config/` é versionada: assim toda a equipe usa as mesmas sessões de teste.

## Esquema inicial do dataset (proposto)

| Campo | Descrição |
| --- | --- |
| `timestamp` | Data/hora da observação em ISO 8601, com fuso |
| `session_id` | Identificador da sessão experimental |
| `sensor_raw` | Leitura bruta, sem unidade física assumida |
| `label` | `0`/`1` experimental; vazio se não houver rótulo confiável |
| `source` | `real`, `synthetic` ou identificador de dataset público |
| `temperature_c` | Opcional, somente se medida |
| `humidity_pct` | Opcional, somente se medida |
| `notes` | Condições experimentais e observações |

Regras de formato:

- `timestamp` precisa ter fuso horário, por exemplo `2026-10-20T14:00:00-03:00`. Horários sem fuso são rejeitados porque são ambíguos. Internamente tudo é convertido para UTC.
- Em `data/raw/`, `source` deve ser sempre `real`.
- `label` vazio é permitido (leitura sem rótulo confiável); essas linhas não entram no treino nem no teste.
- Não pode haver duas leituras com a mesma `session_id` e o mesmo `timestamp`.

## Ambiente

```bash
cd ml
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest        # roda os testes
```

## Como usar quando os dados chegarem

1. Salve cada coleta como CSV em `data/raw/`, com as colunas de `templates/leituras_template.csv`. Pode ser um arquivo por sessão ou vários por arquivo.
2. Rode, de dentro de `ml/`:

   ```bash
   python -m src.cli all
   ```

Isso executa cinco etapas, que também podem ser rodadas separadamente:

| Comando | O que faz | Gera |
| --- | --- | --- |
| `validate` | Confere todos os CSVs de `data/raw/` e lista todos os problemas de uma vez | nada |
| `split` | Sorteia sessões de teste por classe (padrão: 25%) | `config/split_sessions.json`, `data/processed/real_train.csv`, `real_test.csv` |
| `estimate` | Mede nível, variação entre sessões, ruído e intervalo nas sessões de **treino** | `config/synthetic_estimated.json` |
| `generate` | Sorteia leituras sintéticas com esses parâmetros | `data/synthetic/synthetic_estimated.csv` |
| `prepare` | Junta treino real + sintético; o teste fica só com dados reais | `data/processed/train.csv`, `test.csv` |

Opções úteis: `--test-size 0.3`, `--seed 7`, `--n-sessions 10` (sessões sintéticas por classe; `0` = mesmo número das reais). Veja todas com `python -m src.cli --help`.

Quando chegarem dados novos, basta rodar `all` de novo. As sessões que já estavam no manifesto continuam do mesmo lado (treino ou teste); só as novas são sorteadas. Para refazer o sorteio do zero, apague `config/split_sessions.json`.

### Antes dos dados reais

Para testar o gerador sem dados reais, use os parâmetros didáticos:

```bash
python -m src.cli generate --config config/synthetic_didactic.json
```

Esses valores são inventados e não representam o MQ-3.

### Como funciona o gerador

Cada leitura sintética é `nível da sessão + ruído`. O nível é sorteado uma vez por sessão; o ruído, a cada leitura. Os parâmetros vêm das sessões de treino: a média e o desvio-padrão das medianas de cada sessão, e a mediana dos desvios-padrão dentro das sessões. Os valores gerados ficam limitados à faixa observada.

Limitações: o gerador não reproduz a dinâmica temporal do sensor (aquecimento, subida e descida da resposta) e gera cada sessão com um único rótulo. Ele deve ser revisto depois da análise exploratória das leituras reais. Um modelo treinado só com dados sintéticos aprende a regra do simulador; o desempenho que vale é o medido em `test.csv`, que só tem dados reais.

## Plano

1. **Base do projeto:** estrutura, README, dependências, esquema e validação de dados.
2. **Aquisição e EDA:** importar leituras reais sem alterar os originais; analisar qualidade, distribuição e equilíbrio das classes.
3. **Modelagem:** separação treino/teste por sessão, baseline, comparação de pelo menos três modelos, validação cruzada, otimização de hiperparâmetros e registro no MLflow.
4. **Inferência e integração:** interface que recebe leituras e devolve classe/probabilidade, usando o mesmo `Pipeline` do treino.

## Segurança

Testes com álcool devem ser controlados, seguros e supervisionados. Não fazer testes com chama, vapores concentrados, pessoas ou dentro de um veículo. A equipe de hardware deve confirmar a segurança elétrica antes de ligar o MQ-3 ao ESP32.
