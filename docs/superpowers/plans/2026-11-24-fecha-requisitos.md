# Plano: fechar as lacunas de requisitos (Embarcados + ML)

> **Para quem continuar este plano (pessoa ou agente):** leia primeiro "Andamento".
> Ele diz o que já está no código, em qual branch e o que falta, no detalhe.
> Atualize "Andamento" no mesmo commit de cada etapa.

## Andamento (atualizado em 24/11/2026)

### Organização do trabalho

- **Branch de integração:** `fecha-requisitos`, criada a partir da `main` (`d61e301`). As etapas que mexem no `docker-compose.yml` e em `services/` são feitas nela, uma de cada vez: 1, 6, 7 e 8.
- **Etapas em paralelo**, cada uma em worktree própria a partir da `main`. As sessões rodam no Sonnet 5.5; o Opus revisa cada branch (skill `code-review`) antes do merge em `fecha-requisitos`.

| Etapa | Branch | Arquivos que a branch pode tocar |
| --- | --- | --- |
| 2. Firmware | `firmware-freertos-mqtt` (nome final da worktree pode ter prefixo) | só `esp32-esp8266/` |
| 3–4. MLflow e avaliação | `ml-mlflow-avaliacao` | só `ml/` e `airflow/` (o serviço `mlflow` do compose fica para a Etapa 8) |
| 5. Notebook de EDA | branch da sessão "Notebook de EDA" | `ml/notebooks/01_eda.ipynb` (e `docs/roadmap.md`) |

- **Para achar as branches:** `git branch -a | grep -iE 'firmware|mlflow|eda'`.
- **Ao juntar:** `git merge --no-ff <branch>` em `fecha-requisitos`, depois rodar todos os testes.
- **Conflitos esperados no merge:**
  - `docs/roadmap.md`: todas as branches mexem.
  - `ml/README.md`, linha ~197: a branch de ML mexe. Na integração, trocar o texto do "worker em `services/`" pelo servidor `services/mq3mqtt/ao_vivo.py` (o achado do review da Etapa 1 ficou para esse momento).

### Etapa 1 — contrato MQTT único: **feita** (commit `ce16cff` em `fecha-requisitos`)

- Contrato único é o da coleta (`applications/coleta/mensagens.py`). Saíram:
  - `services/mq3mqtt/{messages,ingest,store,simulator,model_server}.py`;
  - `services/docker-compose.yml`, `services/db`, `services/grafana`, `services/mosquitto`, `services/Dockerfile.ingest`.
- **Servidor ao vivo** `services/mq3mqtt/ao_vivo.py`:
  - assina `mq3/+/eventos`; a cada `sopro_fim`, espera 35 s (`ESPERA_APOS_SOPRO_S`);
  - confere se já chegaram leituras até fim + 30 s; se não, espera mais 15 s até 4 vezes e depois classifica com aviso no `detalhe`;
  - lê a rodada no banco da coleta, grava em `resultados` e publica `mq3/<placa>/resultado`;
  - reconecta ao banco e ignora `sopro_fim` repetido;
  - o mesmo processo serve o HTTP da aba Modelo (8010).
- **Banco** (`applications/db/01-schema.sql` + migração `applications/db/migracoes/2026-11-24-resultados-e-origem-placa.sql`): nova tabela `resultados`, e `rodadas.origem` aceita `'placa'`, usado pelo firmware.
- **Simulador da coleta:** publica `sopro_fim` `--duracao` s (padrão 5) depois de cada início.
- **CI:** roda `services/` (`pythonpath = . ../ml`).
- **Verificado de ponta a ponta** no compose local: simulador → ingestor → banco → `mq3/teste-e2e/resultado` com `sem_modelo`. A `main` não tem `.joblib`, então ainda não foi verificado com um modelo treinado.

### Etapa 6 — resultado ao vivo e alerta: **feita** (commit "Mostra a classe do modelo ao vivo e alerta por Telegram")

- **Front:**
  - `aovivo/mensagens.ts` lê `mq3/+/resultado`.
  - `aovivo/estado.ts` guarda `resultadosPorRodada` e avisa com `alerta` (`sob_efeito`) ou `resultado`.
  - `aovivo/componentes/ResultadoAoVivo.tsx` é o card "Modelo de ML" em `PainelAoVivo`: classe, probabilidades e "Alerta de detecção.".
  - 205 testes passam, e o build também. Conferido no navegador com um `resultado` publicado à mão para a rodada do simulador.
- **Bônus de alerta:**
  - `services/mq3mqtt/alerta.py`: Telegram via Bot API, uma vez por sopro, e só registra no log sem `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID`.
  - Serviço `alerta` no compose; variáveis no `.env.example`.
  - Testado com um cliente HTTP falso e no compose local, mas só pelo log: **o envio real ao Telegram não foi testado**, porque falta um bot da equipe.

### Etapa 7 — remover o Grafana: **feita** (commit "Remove o Grafana e o túnel do Grafana Cloud")

- **Removidos:** `applications/grafana/`, `applications/pdc/` e `applications/coleta/tests/test_dashboard.py`; no compose, os serviços `grafana` e `pdc` e o volume `grafana-dados`; no `.env.example`, as variáveis do Grafana e do PDC.
- **Usuário só leitura renomeado de `grafana_leitor` para `leitor`:**
  - `02-leitor.sh` usa `LEITOR_PG_SENHA`;
  - migração `applications/db/migracoes/2026-11-24-leitor.sql` faz o rename;
  - o compose aceita o `.env` antigo: `${LEITOR_PG_SENHA:-${GRAFANA_PG_SENHA:-}}`.
- Aplicado no banco local; a API responde 200 com `leitor`. Testes: `applications` 115, front 205 e o build passam.
- **Quem tem banco antigo:** rodar as duas migrações de 24/11 (`resultados-e-origem-placa` e `leitor`) e, no `.env`, renomear `GRAFANA_PG_SENHA` para `LEITOR_PG_SENHA`. Sem renomear também funciona.

### Etapa 8 — compose único, MLflow e IPv6: **feita na parte do compose** (commit "Sobe tudo com um comando, com MLflow e rede IPv6")

- `docker compose up -d --build` sobe os 9 serviços, sem perfis: mosquitto, postgres, ingestor, api, frontend, model, alerta, airflow e mlflow.
- **MLflow:**
  - `ghcr.io/mlflow/mlflow:v2.17.2` (o cliente na branch de ML é `mlflow>=2.17,<3`);
  - SQLite e artefatos no volume `mlflow-dados`;
  - host **127.0.0.1:5050**, porque a 5000 do macOS é do AirPlay e responde 403. Dentro da rede é `http://mlflow:5000`.
- **Airflow:** com `MLFLOW_TRACKING_URI=http://mlflow:5000`.
- **IPv6:**
  - rede padrão com `enable_ipv6` e `fd00:5050:5a::/64`;
  - o Mosquitto abre sockets IPv4 e IPv6 nas portas 1883 e 9001;
  - testado com pub/sub em `::1` e conexão TCP por IPv6 de outro contêiner.
- **Servidor do modelo:** sobe o HTTP antes de esperar o banco e tenta conectar até conseguir (`connect_with_retry(attempts=0)`).
- **Verificado:** `docker compose down && up -d --build` deixa os 9 serviços no ar; a tela, a API, o modelo, o MLflow e o Airflow respondem 200; o ponta a ponta com o simulador publica o `resultado`, assinado por IPv6.
- **Cuidado:** ao trocar a configuração da rede com o compose no ar, os contêineres antigos perdem o DNS (`failed to resolve host 'postgres'`). A solução é `docker compose down` e `up`.
- **Falta, depende do merge da branch de ML:**
  1. Disparar o DAG e ver os runs e as figuras no MLflow.
  2. Corrigir `ml/README.md` (linha ~164 ainda manda `--profile airflow`; linha ~197 fala do worker antigo de `services/`).

### Etapas 2, 3–4 e 5: **em andamento nas worktrees** (ver tabela acima)

## Contexto

Comparei os três documentos de requisitos com a `main` (`d61e301`). Faltam peças que valem nota:

**Embarcados**
- A ESP32 não usa Wi-Fi nem MQTT: hoje um PC lê a serial e faz a ponte (`applications/coleta/ponte.py`).
- **FreeRTOS:** o firmware só tem `setup()`/`loop()` com `delay(1000)`, sem nenhuma task própria (`esp32-esp8266/src/main.cpp:277-377`). O Arduino-ESP32 roda sobre o FreeRTOS, mas o requisito pede firmware com FreeRTOS, então é preciso criar tasks e filas explícitas.
- Bônus: IPv6 e alerta por mensageiro.

**ML**
- O MLflow é citado mas nunca usado: não há serviço, `import` nem dependência.
- Não existe notebook de EDA.
- Não há figuras (matriz de confusão, ROC). A ROC nem é calculada.
- Faltam a análise de estabilidade por fold e a análise de over/underfitting.
- Não sobe tudo com um comando, porque o Airflow fica num profile à parte.

**Inferência**
- A aba Ao vivo não mostra o resultado do modelo.
- Há dois contratos MQTT incompatíveis: `coleta/mensagens.py` usa `tipo`/`rodada_id`, e `services/mq3mqtt/messages.py` usa `evento`/`sessao`.

**Decisões já tomadas pelo usuário**
- Implementar o firmware nesta branch. O integrante responsável revisa antes do merge.
- Criar uma branch nova.
- Incluir IPv6, o alerta e a remoção do Grafana.

## Branch

Criar `fecha-requisitos` a partir da `main`, com os caminhos atuais (`ml/`, `services/`).

A `reorganiza-estrutura` não tem PR, está 5 commits atrás e não tem o Airflow. Ela fica para depois desta, com rebase. Avisar a equipe para não mexer nas duas estruturas ao mesmo tempo.

Higiene antes de começar (apagar só depois de conferir com o usuário):
- `applications/ml/`, sobra não rastreada da outra branch;
- os diretórios `* 2` duplicados em `applications/frontend/src/`.

Cada etapa abaixo segue o mesmo fluxo:
1. TDD onde o comportamento é testável.
2. `code-review` sobre o diff.
3. Atualizar `docs/roadmap.md` no mesmo commit.
4. Um commit por etapa.

## Etapa 1: contrato MQTT único

O firmware vai falar com o backend, então o contrato precisa ser decidido antes.

- Adotar o contrato da coleta (`applications/coleta/mensagens.py`):
  - tópicos `mq3/<placa>/{rodada,leituras,eventos,status}`, QoS 1;
  - `status` retido com last will.
  - Motivo: é o que o ingestor e o banco já gravam.
- Adaptar `services/mq3mqtt/messages.py`, `simulator.py` e `model_server.py` para esse formato:
  - `tipo` no lugar de `evento`;
  - `rodada_id` com `sessao`;
  - `estado` no lugar de `status`.
- Manter `sopro_pronto` e `resultado` como extensões do modelo.
- Testes:
  - `services/tests` e `applications/coleta/tests` com as mensagens novas;
  - um teste que faz parse de uma mensagem do simulador com a função da coleta.
- Atualizar o `ARCHITECTURE.md` (seção de contratos, linhas 86-109) e apagar o `services/docker-compose.yml`, que duplica a stack e choca portas com a da raiz.

## Etapa 2: firmware com FreeRTOS, Wi-Fi e MQTT

Arquivos: `esp32-esp8266/src/main.cpp`, `platformio.ini`, e `include/segredos.h` novo, no `.gitignore`, acompanhado de um `segredos.exemplo.h` versionado.

- **Bibliotecas:** acrescentar `knolleary/PubSubClient` e `bblanchon/ArduinoJson` em `lib_deps`.
- **Tasks do FreeRTOS**, cada uma criada com `xTaskCreatePinnedToCore`:
  - `tarefaSensores`: lê o MQ-3, o MQ-135 e o DHT a cada 1 s com `vTaskDelayUntil`. Monta a struct `Leitura` (mesmas 13 colunas de hoje) e põe na `QueueHandle_t filaLeituras`.
  - `tarefaArmazenamento`: consome uma cópia da fila e grava o CSV no LittleFS, como já faz hoje. O CSV continua sendo a fonte do treino.
  - `tarefaRede`: Wi-Fi com reconexão; MQTT com last will em `status=offline`; publica `rodada` (retida) ao iniciar a sessão, depois `leituras` e `eventos`. Se a rede cair, mantém uma fila de leituras pendentes, com limite.
  - `tarefaBotao` (opcional): um botão do kit marca `sopro_inicio`/`sopro_fim` por interrupção + semáforo, substituindo o Enter da ponte serial. Sem botão, os eventos continuam vindo do operador pelo front ou pela ponte.
- **Rodada:** `rodada_id` = MAC + número da sessão. `placa` configurável em `segredos.h`.
- **Compatibilidade:** a saída serial `CSV_LINHA` continua funcionando, para a ponte serial servir de alternativa.
- **Verificação:** compilar com `pio run`; gravar na placa; `mosquitto_sub -t 'mq3/#' -v`; ver as linhas chegarem no Postgres pelo ingestor.

## Etapa 3: MLflow

- Acrescentar `mlflow` ao `ml/requirements.txt` e ao `airflow/requirements.txt`, compatível com o `scikit-learn==1.6.1`.
- Novo serviço `mlflow` no `docker-compose.yml`:
  - backend store no Postgres (schema/banco próprio criado por migração em `applications/db/migracoes`);
  - artifacts num volume;
  - porta `127.0.0.1:5000`.
- Novo módulo `ml/src/rastreio.py`, ligado quando houver `MLFLOW_TRACKING_URI` e sem efeito nenhum se a variável não existir, para os testes rodarem offline.
  - `registrar_experimento(df, ...)` cria um run por linha de `run_experiment` (`train.py:137`), com params `sensor_set`, `model` e `chosen_params`, e as métricas.
  - `registrar_final(metadata, modelo, figuras)` registra o modelo final de `train_final_model` (`train.py:183`) e as figuras como artifacts.
- Chamar essas funções em `pipeline.treinar_modelos` (360) e `pipeline.avaliar_teste` (406).
- Em `cli.run_train` (91-125), trocar o fluxo duplicado por chamadas a `pipeline`.
- O DAG ganha `MLFLOW_TRACKING_URI` no ambiente do Airflow.
- Teste: com `MLFLOW_TRACKING_URI=file:<tmp>`, rodar o treino em dados de fixture e conferir os runs criados.

## Etapa 4: avaliação completa

- Em `nested_cv_predict` (`train.py:115`): guardar a métrica de cada fold externo e devolver média e desvio padrão. O `experiment.csv` ganha colunas `*_std`.
- Medir **treino vs validação** em cada fold: o F1 no treino ao lado do F1 na validação. A diferença entre os dois é a evidência de overfitting ou underfitting.
- Calcular ROC e AUC com `predict_proba`, só nos modelos que oferecem esse método.
- Novo módulo `ml/src/figuras.py` com:
  - matriz de confusão;
  - curva ROC;
  - barras com o F1 de cada modelo e sensor_set, com barras de erro;
  - curva de aprendizado.
  - Os PNG vão para `ml/reports/figuras/` e para o MLflow.
- Testes que conferem as métricas por fold e que cada figura gera um arquivo.
- Revisar a contagem de 11.289 tentativas: confirmar se `amostras_sem_efeito.py` cria janelas sobrepostas do mesmo sopro. Se criar, os grupos do `GroupKFold` precisam manter essas janelas juntas, e a explicação vai para o README.

## Etapa 5: notebook de EDA

`ml/notebooks/01_eda.ipynb`, só com os dados da equipe, importando funções de `ml/src` em vez de copiar código.

**Roteiro:** o documento "Relatório progressão projeto" (Google Docs da equipe, de 15/10 a 24/11). O notebook segue a linha do tempo do diário e testa nos dados cada observação dele. Cada seção cita a data da entrada no diário e termina com "confirmado", "não confirmado" ou "dados insuficientes".

1. **Visão geral:** volume por condição, participante e dia; valores ausentes; leituras de ambiente do fim de semana de 13 e 14/11.
2. **Mudança de alimentação em 10/11** (de cerca de 3,8 V para cerca de 4,8 V; o diário cita leituras de 0,9–2 antes e até 12 depois). Comparar a distribuição do MQ-3 antes e depois de 10/11.
   - **Decisão importante:** as sessões anteriores entram no treino, ficam de fora ou recebem uma marca de "alimentação antiga"?
   - Até a equipe decidir, tratar como hipótese a confirmar.
3. **Hipóteses de 29/10, as três regras esperadas.** Curvas antes, durante e depois do sopro por condição:
   - só o MQ-3 sobe;
   - sobem o MQ-3 e o MQ-135;
   - sobem o MQ-3, o MQ-135 e a umidade.
4. **20/10 e 05/11:** a umidade sobe com o sopro e fica parada com o copo ou com o gel. Testar se a umidade separa sozinha as duas classes. Isso dá base à ideia do diário de uma "árvore com a umidade no primeiro nó": comparar com a árvore treinada e ver a importância das features.
5. **12/11:**
   - Perfume: o diário diz que o MQ-3 fica abaixo de 0,8 e o MQ-135 vai a 1200–1500. Medir esses valores.
   - Bebida com gelo dá sinal menor que sem gelo.
   - Expirar de boca aberta dá sinal maior que soprar. Verificar se a coleta registra o tipo de sopro; se não registrar, anotar como limitação.
6. **12/11, temperatura sem diferença entre as classes:** testar e justificar se ela entra ou não nas features.
7. **Distribuição das features e correlação.**
8. **Decisões de preparação** e a justificativa de cada uma: limpeza, normalização (`StandardScaler` no pipeline), encoding, ausentes e a decisão do item 2.

**Conflito com as regras do projeto:** o diário fala em "embriaguez", "não embriagados" e "escala de detecção". Conforme o `AGENTS.md`, o notebook usa `sob_efeito` = "bebeu nas condições do experimento", sem afirmar embriaguez nem mg/L. Avisar a equipe para ajustar esse vocabulário no relatório.

Como verificar: `jupyter nbconvert --execute` roda o notebook do começo ao fim sem erro.

**O texto interpretativo é da equipe.** O agente monta o notebook, as células de código e as figuras, e deixa marcados os lugares do texto.

## Etapa 6: inferência ao vivo na tela e alerta

- **Situação hoje, confirmada:** o card da aba Ao vivo usa a heurística de `aovivo/detector.ts`. O próprio card avisa que "não é o modelo de ML" (`CartaoEstado.tsx:58`), e `aovivo/mensagens.ts` descarta o tópico `resultado`. O modelo só aparece na aba Modelo, com sopros de exemplo.
- **Front:** a aba Ao vivo passa a parsear `resultado` em `mensagens.ts`, assinando `mq3/+/resultado` pelo websocket 9001 e mostra a classe e a probabilidade. Quando o resultado for `sob_efeito`, aparece o aviso de alerta, reaproveitando `componentes/Aviso.tsx` e o estilo de `PainelModelo.tsx`. Teste em `src/aovivo`.
- **Bônus de alerta:** novo módulo `services/mq3mqtt/alerta.py`, assinando `resultado`. Quando a classe for `sob_efeito`, envia uma mensagem pela Bot API do Telegram, com token e chat em `.env` (adicionar no `.env.example`). Sem token, não faz nada. Sobe como serviço `alerta` no compose. Teste com cliente HTTP falso.

## Etapa 7: remover o Grafana

Segue a etapa 7 de `docs/superpowers/plans/2026-11-17-frontend-react.md` (linhas 577-579):
- apagar `applications/grafana/`, `applications/pdc/`, os serviços correspondentes no compose e as variáveis de ambiente;
- migração renomeando `grafana_leitor` para `leitor`;
- atualizar a documentação e marcar a etapa como concluída no plano.

## Etapa 8: compose com um único comando e IPv6

- Tirar os profiles do `airflow`/`airflow-init`, para que `docker compose up -d --build` suba tudo: mosquitto, postgres, ingestor, api, frontend, model, mlflow, airflow e alerta. Atualizar o README (linha 88 em diante).
- **IPv6:**
  - rede do compose com `enable_ipv6: true` e uma subnet ULA `fd00:...`;
  - `listener 1883 ::` e `socket_domain` ajustado em `applications/mosquitto/mosquitto.conf`;
  - firmware com IPv6 habilitado no Wi-Fi (`WiFi.enableIPv6()`, conforme a versão do core) e conexão do MQTT ao broker por endereço IPv6.
  - Verificação: `mosquitto_sub -h ::1`; a placa conectando por IPv6, aparecendo no log do broker.
  - Hipótese a confirmar: depende de a rede da faculdade ou do roteador entregar IPv6.

## Fora do escopo do agente

- O **relatório CSBC** é escrito pela equipe. O agente fornece as figuras e tabelas das etapas 4 e 5.
- A **coleta de `drink`** depende de uma decisão sobre o Comitê de Ética ou o simulador.

## Verificação final

1. `cd ml && python -m pytest`, `cd services && python -m pytest` e os testes de `applications/` passam. O front passa em `npm test` e `npm run build`.
2. Teste ponta a ponta: com `docker compose up -d --build` e a placa ligada, fazer um sopro. Conferir:
   - as linhas chegam ao Postgres;
   - o `resultado` aparece na aba Ao vivo;
   - com `sob_efeito`, chega o alerta no Telegram.
3. Disparar o DAG no Airflow (http://localhost:8088) e ver os runs e as figuras no MLflow (http://localhost:5000).
4. Atualizar o `docs/roadmap.md`: cada requisito da planilha e do PDF ligado ao arquivo que o atende.
