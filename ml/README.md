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

O projeto está no início. Ainda não existem dados, código de ML nem modelos.

| Item | Situação |
| --- | --- |
| Modelo exato do ESP32 | Não confirmado |
| Tipo de saída do módulo MQ-3 (analógica/digital) | Não confirmado |
| Tensão de saída e compatibilidade com o ADC do ESP32 | Não verificada |
| Método e frequência de aquisição | Não definidos |
| Primeiras leituras reais | Não coletadas |
| Procedimento experimental e fonte dos rótulos | Não definidos |
| Dataset público relevante | Não pesquisado |
| Dataset sintético | Não criado |
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
├── data/
│   ├── raw/          # Leituras reais originais (nunca sobrescritas)
│   ├── synthetic/    # Dados simulados, identificados como sintéticos
│   └── processed/    # Dados preparados a partir de raw/ ou synthetic/
├── notebooks/        # Análise exploratória e experimentos
├── src/              # Código reutilizável (geração, validação, preparação, treino, inferência)
├── models/           # Artefatos treinados
├── tests/            # Testes automatizados
├── requirements.txt
├── .gitignore
└── README.md
```

Por padrão, o conteúdo de `data/` e `models/` não é versionado no Git (veja `.gitignore`). Se a equipe decidir versionar leituras reais, ajuste o `.gitignore` explicitamente.

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

## Ambiente

```bash
cd ml
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Plano

1. **Base do projeto:** estrutura, README, dependências, esquema e validação de dados.
2. **Aquisição e EDA:** importar leituras reais sem alterar os originais; analisar qualidade, distribuição e equilíbrio das classes.
3. **Modelagem:** separação treino/teste por sessão, baseline, comparação de pelo menos três modelos, validação cruzada, otimização de hiperparâmetros e registro no MLflow.
4. **Inferência e integração:** interface que recebe leituras e devolve classe/probabilidade, usando o mesmo `Pipeline` do treino.

## Segurança

Testes com álcool devem ser controlados, seguros e supervisionados. Não fazer testes com chama, vapores concentrados, pessoas ou dentro de um veículo. A equipe de hardware deve confirmar a segurança elétrica antes de ligar o MQ-3 ao ESP32.
