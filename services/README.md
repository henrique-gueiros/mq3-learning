# MQTT e servidor do modelo

> Esta pilha usa as mesmas portas (1883, 5432) da coleta em `applications/` e ainda 3000 e 9001 (Grafana local). Não suba as duas ao mesmo tempo. A unificação está planejada para depois da coleta.

O fluxo completo, da coleta ao resultado, está no [README do repositório](../README.md). Aqui ficam o Compose, os tópicos e os comandos.

A ESP32 publica no broker. O servidor do modelo é outro processo, no mesmo Docker Compose, no computador que estiver na mesma rede da placa. Hoje esse computador é o de vocês. A placa não abre conexão com ele.

```text
ESP32 (ou o simulador)
        |  mq3/<placa>/leituras
        |  mq3/<placa>/eventos          sopro_inicio, sopro_fim
        |  mq3/<placa>/status
        v
   Mosquitto (porta 1883)
        |
        +----> worker (ingest) ----> PostgreSQL
        |              |
        |              +---- mq3/<placa>/sopro_pronto   (só depois de gravar)
        |
        +----> servidor do modelo
                      |
                      +---- lê o sopro no Postgres
                      +---- mq3/<placa>/resultado
```

`sopro_pronto` é um aviso interno. Quem publica é o worker, depois que a linha do `sopro_fim` e as leituras já estão no banco. O servidor do modelo usa o mesmo código de `ml/src/inference.py`. O arquivo que ele espera é `ml/models/sob_efeito.joblib`. Esse arquivo ainda não existe, porque o modelo não foi treinado. Até lá a resposta publicada é `status: sem_modelo` e nenhuma classe é inventada. As leituras ficam no Postgres para o treino.

A publicação pela ESP32 continua com quem mexe no firmware. Para testar sem a placa, o simulador reenvia um CSV que o firmware já gravou.

## Subir

Na pasta `services/`:

```bash
docker compose up --build
```

Sobe o Mosquitto na porta 1883, o Postgres na 5432 (usuário `mq3`, senha `mq3`, banco `mq3`), o worker e o servidor do modelo. Essa senha é só da bancada local.

Em outro terminal, com as dependências instaladas no `ml/.venv`:

```bash
source ../ml/.venv/bin/activate
pip install -r requirements.txt
python -m mq3mqtt.simulator \
  --csv ../esp32-esp8266/leituras.csv \
  --placa bancada \
  --sessao leituras_1.csv \
  --blow-start-s 40 \
  --blow-end-s 45 \
  --interval 0
```

`--blow-start-s` e `--blow-end-s` são os segundos da sessão em que o sopro começou e terminou, os mesmos do `attempts.csv`. O exemplo acima não afirma nada sobre o conteúdo de `esp32-esp8266/leituras.csv`; troque os segundos pelos do sopro que vocês anotaram.

O simulador precisa enxergar o broker em `localhost:1883`. Os containers usam o nome `mosquitto`.

## O que cada tópico carrega

Leitura (`mq3/bancada/leituras`), com as mesmas colunas do CSV:

```json
{"sessao":"leituras_1.csv","amostra":12,"t_ms":11000,"mq3_raw":400,"ppm":0.0,"mq135_raw":380,"mq135_mv":300,"temperature_c":null,"humidity_pct":null,"alcool":0}
```

Evento (`mq3/bancada/eventos`):

```json
{"sessao":"leituras_1.csv","evento":"sopro_fim","t_ms":45000}
```

Resultado (`mq3/bancada/resultado`), enquanto não houver modelo:

```json
{"sessao":"leituras_1.csv","attempt_id":"leituras_1@40s","status":"sem_modelo","prediction":null,"prob_sem_efeito":null,"prob_sob_efeito":null,"detalhe":"as leituras deste sopro ficaram no banco; ainda não existe modelo treinado em sob_efeito.joblib"}
```

Quando o `train` gerar `ml/models/sob_efeito.joblib`, o mesmo serviço passa a preencher `prediction` com `sob_efeito` ou `sem_efeito` e as duas probabilidades. Não é preciso mudar o worker.

O processo também abre `POST /modelo/classificar` na porta 8010 (a aba Modelo da tela). O corpo é o recorte do sopro; a resposta é este mesmo JSON. Essa chamada não grava no Postgres. No Compose de `services/` a porta fica em `127.0.0.1:8010`.

`ppm` e `alcool` são gravados porque estão no CSV. O modelo continua sem usá-los.

Uma leitura repetida (mesma placa, mesma sessão, mesma `amostra`) não entra de novo.

## Testes

Os testes abaixo não sobem o Docker e não medem o sensor:

```bash
cd services
python -m pytest
```
