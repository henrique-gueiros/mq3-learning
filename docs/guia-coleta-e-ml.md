# Guia de coleta, treino e MQTT

Passo a passo da coleta rotulada, do treino e do servidor do modelo (fluxo de `applications/services/`). Para o fluxo da tela e do dashboard, veja o [README do repositório](../README.md) e `applications/README.md`.

## 1. Captar os dados

A ESP32 já grava uma linha por segundo num CSV da sessão (`leituras_N.csv`), do ligar até o reiniciar. Cada linha tem o tempo `t_ms` e as leituras dos três sensores. A placa não descobre sozinha quando alguém soprou. Quem conduz o teste anota isso.

Para cada bateria (30 s ou 60 s, por exemplo):

1. Ligue a placa e deixe gravando.
2. Faça um cenário só.
3. Se alguém soprar, anote o segundo de início e o de fim. Numa sessão de 60 s em que o sopro foi do 30 ao 50, a marcação é 30 e 50.
4. Anote a condição, uma destas: `clean`, `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash`, `drink`.
5. Copie o CSV para `applications/ml/data/raw/sessions/` sem editar. Como a numeração recomeça em cada placa, use um nome único, por exemplo `2026-11-05_p01_leituras_3.csv`.
6. Acrescente uma linha em `applications/ml/data/raw/attempts.csv` (o cabeçalho está em `applications/ml/templates/attempts_template.csv`).

Exemplo de três cenários:

| O que aconteceu | `condition` | Classe | Intervalo |
| --- | --- | --- | --- |
| A pessoa bebeu e soprou | `drink` | `sob_efeito` | do segundo em que começou ao segundo em que parou |
| A pessoa soprou sem ter bebido | `clean` | `sem_efeito` | o mesmo |
| Só o ambiente do carro, sem sopro | `clean` | `sem_efeito` | a sessão inteira, para o modelo ver o carro parado |

`participant_id` é um código anônimo (`p01`), nunca o nome da pessoa.

Uma linha do `attempts.csv`:

```text
attempt_id,session_file,participant_id,condition,blow_start_s,blow_end_s,reference_mg_l,notes
p01-drink-1,2026-11-05_p01_leituras_3.csv,p01,drink,30,50,,bebeu e soprou do 30 ao 50
```

Perfume, gel, borrifo e enxaguante também são `sem_efeito`. Eles entram na coleta para o modelo aprender a não tratar esse vapor como motorista que bebeu.

As colunas `ppm` e `alcool` do CSV ficam no arquivo e não entram no treino. As duas são calculadas pelo próprio firmware a partir do MQ-3.

## 2. O que fazer com esses dados

Dentro de `applications/ml/`, com o ambiente ligado (`python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`):

```bash
python -m src.cli validate
python -m src.cli all
```

`validate` confere os CSVs e as linhas do `attempts.csv`. `all` faz o resto:

1. Recorta cada sopro: 15 s antes, o intervalo anotado e 30 s depois.
2. Resume esse recorte numa linha de features (valor de antes, pico, subida, tempo até o pico, recuperação, e o que a umidade fez junto).
3. Separa treino e teste por pessoa. A mesma pessoa não fica dos dois lados.
4. Compara os modelos e grava `applications/ml/models/sob_efeito.joblib`.

Esse arquivo é o modelo. Ele ainda não existe: falta coleta das duas classes, com várias pessoas. Três sessões de uma pessoa só não fecham o treino. Os detalhes dos comandos estão em `applications/ml/README.md`.

## 3. Rodar o modelo

Há dois jeitos, e os dois usam o mesmo `.joblib`.

**Num CSV já gravado**, de dentro de `applications/ml/`:

```bash
python -m src.cli predict --session data/raw/sessions/2026-11-05_p01_leituras_3.csv --blow-start-s 30 --blow-end-s 50
```

A resposta sai no terminal: `sob_efeito` ou `sem_efeito`.

**Ao vivo**, o servidor do modelo é o container `model` do Docker. O código está em `applications/services/mq3mqtt/model_server.py`. Ele lê `applications/ml/models/sob_efeito.joblib`. Enquanto esse arquivo não existir, a resposta publicada é `sem_modelo` e a classe fica vazia.

## 4. Como o MQTT funciona

MQTT é o protocolo. Mosquitto é o programa que recebe e entrega essas mensagens. Sobe junto com o banco, o worker e o servidor do modelo:

```bash
cd applications/services
docker compose up --build
```

Num teste novo, com a placa ligada na mesma rede:

1. Cada segundo a ESP32 publica uma leitura em `mq3/<placa>/leituras`, com as mesmas colunas do CSV.
2. No começo do sopro publica `sopro_inicio` em `mq3/<placa>/eventos`. No fim, `sopro_fim`.
3. O worker recebe essas mensagens e grava no PostgreSQL. A mesma amostra, da mesma placa e da mesma sessão, não entra duas vezes.
4. Gravado o fim do sopro, o worker avisa o servidor em `mq3/<placa>/sopro_pronto`.
5. O servidor lê as linhas daquela sessão no banco, recorta o sopro como no treino e publica em `mq3/<placa>/resultado`.

Os CSVs usados no treino não passam de novo pelo MQTT. O MQTT leva o teste que está acontecendo agora.

A ESP32 ainda não publica. Até o firmware fazer isso, o simulador republica um CSV que a placa já gravou. Os segundos do sopro são os que você passar no comando, os mesmos do `attempts.csv`:

```bash
cd applications/services
source ../ml/.venv/bin/activate
pip install -r requirements.txt
python -m mq3mqtt.simulator \
  --csv ../../esp32-esp8266/leituras/leituras.csv \
  --placa bancada \
  --sessao leituras_1.csv \
  --blow-start-s 30 \
  --blow-end-s 50 \
  --interval 0
```

Troque o CSV e os segundos pelos do teste de vocês. O passo a passo do broker, dos tópicos e da senha local do banco está em `applications/services/README.md`.
