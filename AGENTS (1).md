# AGENTS.md — Projeto de Machine Learning: Detector de Álcool com MQ-3

## 1. Papel deste arquivo

Este arquivo orienta o Cursor e outros agentes de programação a construir **exclusivamente a parte de Machine Learning e dados** do projeto acadêmico de detector de álcool com sensor MQ-3.

Trabalhe incrementalmente, explique decisões importantes e não implemente premissas experimentais como se fossem fatos comprovados. O usuário está aprendendo ML; prefira código claro, modular e didático a abstrações desnecessárias.

**Importante:** antes de fazer mudanças grandes, inspecione a estrutura existente e preserve arquivos e decisões já tomadas. Não sobrescreva trabalho existente sem necessidade.

## 2. Contexto do projeto

- Projeto acadêmico de um detector de álcool que ficará no carro.
- Sensor previsto: **MQ-3**, sensível a vapor de álcool.
- Microcontrolador provável: **ESP32**, mas o modelo exato da placa e a forma de leitura ainda precisam ser confirmados.
- A equipe ainda não fez a primeira leitura do sensor.
- Ainda não existe dataset; vamos começar do zero.
- A responsabilidade coberta por este repositório é a **parte de ML**, não o firmware completo nem a lógica final do veículo.
- Ainda não foi decidido o que o sistema fará após uma detecção.
- O objetivo inicial de ML é classificar uma observação como:
  - `0`: álcool não detectado nas condições do experimento;
  - `1`: álcool detectado nas condições do experimento.
- Esta classificação representa **detecção de álcool nas condições avaliadas**, não comprova que o motorista consumiu álcool, está intoxicado ou está inapto a dirigir.

## 3. Estado atual e incertezas

Não assumir que os itens abaixo já foram concluídos:

- [ ] Modelo exato do ESP32 confirmado.
- [ ] Tipo de saída do módulo MQ-3 confirmado (analógica/digital).
- [ ] Tensão de saída e compatibilidade elétrica com o ADC do ESP32 verificadas.
- [ ] Método e frequência de aquisição definidos.
- [ ] Primeiras leituras reais coletadas.
- [ ] Procedimento experimental e fonte confiável dos rótulos definidos.
- [ ] Dataset público relevante encontrado ou descartado após busca.
- [ ] Dataset sintético criado.
- [ ] Modelo treinado ou validado com dados reais.

O agente deve registrar estas incertezas no README e não inventar especificações do hardware, calibração, limites de detecção ou valores típicos do sensor.

## 4. Entregáveis acadêmicos de ML

A solução deverá evoluir para cobrir:

1. Dataset inicial e estratégia de aquisição/armazenamento.
2. Análise exploratória dos dados (EDA).
3. Pipeline reprodutível de limpeza e preparação.
4. Modelo baseline com métricas documentadas.
5. Comparação de pelo menos três algoritmos.
6. Otimização de hiperparâmetros com Grid Search, Random Search ou abordagem equivalente.
7. Validação cruzada e avaliação de generalização/overfitting.
8. Registro de experimentos e métricas com MLflow.
9. Preparação de uma interface de inferência para classificar novas leituras.
10. Integração futura com o sistema de aquisição/MQTT/Airflow, se exigida pelo escopo completo da disciplina. A implementação do firmware e infraestrutura do dispositivo não faz parte deste escopo de ML.

Não alegar que todos os entregáveis estão completos até que estejam realmente implementados e testados.

## 5. Estratégia de dados

### 5.1 Dados reais

A prioridade para validar o comportamento real é coletar leituras do próprio MQ-3 em sessões experimentais controladas e com rótulos confiáveis.

- `label=0` deve representar uma condição experimental de ausência de álcool confirmada pelo procedimento de referência.
- `label=1` deve representar uma condição experimental de presença de álcool confirmada pelo procedimento de referência.
- **Nunca atribuir o rótulo simplesmente com base no próprio valor do MQ-3** e depois usar esse rótulo para afirmar que o modelo aprendeu a detectar álcool.
- Registrar as condições de coleta, a sessão e informações necessárias para rastrear a origem.
- A segurança elétrica deve ser confirmada pela equipe de hardware antes de conectar saídas ao ESP32.
- Não recomendar experiências perigosas com álcool, vapores concentrados, chama, pessoas ou dentro de um veículo. Os testes devem ser controlados, seguros e supervisionados.

### 5.2 Dados sintéticos

Dados sintéticos são permitidos para desenvolver e testar código, pipeline, integração, visualizações e experimentos preliminares.

- Identificar cada registro/dataset sintético de forma explícita (`source="synthetic"` ou metadado equivalente).
- Documentar os pressupostos e os parâmetros utilizados para gerar os valores.
- Não apresentar parâmetros inventados como propriedades reais ou calibração do MQ-3.
- Não usar métricas obtidas exclusivamente em dados sintéticos como evidência de desempenho em situações reais.
- Evitar separação artificialmente perfeita entre classes.
- Não misturar dados sintéticos e reais silenciosamente.
- Manter a geração determinística quando houver seed configurável.
- Deixar claro que o primeiro gerador é didático e provisório, até existirem medições que possam fundamentá-lo.
- Se a geração usar classes criadas diretamente pelo cenário simulado, documentar que o modelo aprende a regra do simulador, não necessariamente a resposta física do sensor.

### 5.3 Dados públicos

Pode-se pesquisar futuramente datasets de sensores de gás/etanol, mas verificar:
- qual sensor foi usado;
- qual grandeza é medida e sua unidade/escala;
- quais são os rótulos e como foram obtidos;
- as condições experimentais;
- licença, origem e adequação ao MQ-3.

Dados de outro sensor podem ajudar a experimentar o pipeline, mas não devem ser tratados como numericamente equivalentes às leituras do MQ-3 sem validação.

## 6. Esquema inicial do dataset

Começar com um esquema explícito, documentado e fácil de ampliar. Campos propostos:

- `timestamp`: data/hora da observação, com fuso ou formato ISO 8601 documentado;
- `session_id`: identificador da sessão experimental;
- `sensor_raw`: leitura bruta fornecida pelo sistema de aquisição, sem supor unidade física;
- `label`: rótulo binário experimental (`0`/`1`), ausente para dados sem rótulo confiável;
- `source`: origem (`real`, `synthetic` ou identificador de dataset público);
- `temperature_c`: opcional, somente se medida por sensor ou fonte identificada;
- `humidity_pct`: opcional, somente se medida;
- `notes` ou metadados de sessão: condições experimentais e observações relevantes.

Regras:
- Não inventar temperatura, umidade ou horário como se fossem medições reais.
- Não interpretar `sensor_raw` como concentração de álcool sem calibração e método de conversão válidos.
- Registrar a taxa de amostragem e o método de leitura quando conhecidos.
- Não incluir horário/dia da semana como preditor inicial por padrão: podem criar correlações espúrias e não demonstram presença de álcool. Só testar variáveis contextuais com justificativa e avaliação apropriada.
- Considerar agregar janelas temporais (por exemplo, média, desvio-padrão, máximo) somente após observar a taxa de amostragem e o comportamento das leituras.

## 7. Requisitos técnicos e estilo de implementação

Preferir Python e ferramentas comuns de ciência de dados:

- NumPy
- pandas
- scikit-learn
- Matplotlib
- Seaborn, quando útil
- Jupyter
- MLflow em uma etapa posterior

Usar versões compatíveis e registrá-las em `requirements.txt`. Não adicionar dependências pesadas sem justificativa. Se já existir ambiente ou gerenciador de dependências no repositório, respeitá-lo em vez de criar outro automaticamente.

Princípios:
- Código simples, modular, tipado quando isso melhorar a clareza e com docstrings nas funções públicas.
- Separar geração, validação, preparação, treino e avaliação.
- Tornar a geração reproduzível com `random_state`/seed.
- Evitar duplicação e abstrações prematuras.
- Tratar erros de dados com mensagens claras.
- Não usar caminhos absolutos dependentes da máquina do desenvolvedor.
- Não salvar dados derivados por cima dos dados brutos.
- Evitar notebooks como único local da lógica reutilizável; manter funções de produção em `src/`.
- Incluir testes para funções de geração, validação de esquema e preparação quando houver código correspondente.
- Não versionar `.venv/`, credenciais, dados pessoais ou grandes dados brutos sem autorização explícita.
- Criar ou atualizar `.gitignore` de acordo com a estrutura real do projeto.

## 8. Estrutura inicial sugerida

Se não houver uma estrutura já existente, começar com:

```text
ml/
├── data/
│   ├── raw/          # Leituras reais originais
│   ├── synthetic/    # Dados simulados, identificados como sintéticos
│   └── processed/    # Dados preparados
├── notebooks/
│   └── 01_eda.ipynb
├── src/
│   ├── data_generation.py
│   ├── data_validation.py
│   ├── preprocessing.py
│   ├── train.py
│   └── inference.py
├── models/           # Artefatos treinados; não preencher com modelos fictícios
├── tests/
├── requirements.txt
├── .gitignore
└── README.md
```

Esta é uma sugestão, não uma exigência de criar todos os arquivos imediatamente. Inspecionar a estrutura existente primeiro e implementar em etapas pequenas.

## 9. Processo recomendado

### Fase 1 — Base do projeto
1. Inspecionar a estrutura e criar/ajustar pastas.
2. Escrever README com objetivo, escopo, limitações e estado atual.
3. Preparar ambiente e dependências.
4. Definir schema e validação de dados.
5. Criar um gerador sintético didático, isolado dos dados reais, apenas se necessário para testar o pipeline.

### Fase 2 — Aquisição e EDA
1. Importar leituras reais sem alterar os arquivos originais.
2. Verificar valores ausentes, duplicados, faixas, distribuição e equilíbrio das classes.
3. Plotar leituras ao longo do tempo e comparar condições experimentais.
4. Documentar qualidade, limitações e possíveis vieses.

### Fase 3 — Modelagem
1. Separar treino e teste antes de ajustar transformações ou hiperparâmetros.
2. Quando houver múltiplas observações por sessão, usar separação por grupos/sessões para reduzir vazamento de dados; não dividir aleatoriamente leituras correlacionadas entre treino e teste.
3. Estabelecer baseline simples.
4. Comparar pelo menos três modelos adequados, por exemplo regressão logística, árvore de decisão e Random Forest, ajustando a escolha à quantidade e qualidade dos dados.
5. Escolher métricas adequadas, incluindo precision, recall, F1 e matriz de confusão; considerar especialmente falsos negativos e falsos positivos conforme o uso pretendido.
6. Usar validação cruzada apropriada, preferencialmente respeitando sessões/grupos quando necessário.
7. Otimizar hiperparâmetros somente dentro dos dados de treino/validação; manter o teste final reservado.
8. Registrar parâmetros, métricas, versões e artefatos no MLflow.
9. Explicitar limitações e não exagerar conclusões se o dataset for pequeno ou sintético.

### Fase 4 — Inferência e integração
1. Criar uma interface clara que receba features no formato documentado e devolva classe e, se apropriado, probabilidades.
2. Garantir que o pré-processamento usado na inferência seja o mesmo do treinamento, preferencialmente encapsulado em um `scikit-learn Pipeline`.
3. Testar a interface com exemplos e dados novos.
4. Integrar depois à fonte de dados real, MQTT/Airflow ou outros componentes conforme o escopo acadêmico.

## 10. Regras para o agente Cursor

- Trabalhar em etapas pequenas e verificáveis; explicar brevemente o que será criado e por quê.
- Não construir a solução inteira de uma só vez.
- Antes de começar, inspecionar o repositório e informar o que já existe.
- Não assumir que o sensor, ESP32, MQTT ou Airflow já estão funcionando.
- Não criar um dataset sintético enorme sem primeiro justificar as hipóteses.
- Não treinar ou reportar métricas como se demonstrassem capacidade real usando somente dados inventados.
- Não adicionar features como horário/dia apenas porque parecem plausíveis; justificar e testar.
- Não inventar resultados, medições, calibração, benchmarks ou fontes.
- Se uma decisão depender de hardware ainda não confirmado, criar uma interface/contrato provisório e documentar a pendência.
- Ao concluir cada etapa, informar arquivos alterados, comandos para executar e testes realizados.
- Manter foco na responsabilidade de ML e dados.
- Priorizar aprendizado do estudante: explicar conceitos de forma direta, com exemplos concretos e sem excesso de abstração.

## 11. Próxima tarefa recomendada

Começar apenas por:
1. inspecionar o repositório;
2. criar/ajustar a estrutura de diretórios inicial;
3. preparar um `README.md` que descreva objetivo, escopo, estado atual, limitações e plano;
4. preparar `.gitignore` e `requirements.txt` mínimos, respeitando o ambiente já existente;
5. apresentar um resumo do que foi feito e aguardar confirmação antes de implementar gerador sintético ou modelos.

Não implementar ainda treinamento de modelos, uma calibração fictícia do MQ-3, integração de hardware, MQTT ou Airflow.
