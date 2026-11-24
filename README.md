# Sopro Seguro

Detector de álcool para carros com machine learning. O mapa do sistema está em [`ARCHITECTURE.md`](ARCHITECTURE.md) e o estado do projeto em [`docs/roadmap.md`](docs/roadmap.md).

Projeto acadêmico para dizer se a pessoa **bebeu** ou **não bebeu**, a partir do MQ-3, do MQ-135 e do DHT11 numa ESP32.

Cada sopro recebe uma classe:

| Classe | Quando |
| --- | --- |
| `sob_efeito` | A pessoa bebeu (`drink`) |
| `sem_efeito` | A pessoa não bebeu: ar do carro, perfume, álcool em gel, borrifo ou enxaguante |

A classe vem do que foi feito no teste, anotado pela equipe. O modelo não mede mg/L e não é um etilômetro. `sob_efeito` significa "bebeu nas condições do experimento".

Há dois momentos. Primeiro a equipe junta CSVs e treina. Depois, com o arquivo do modelo na mão, um teste novo pode entrar ao vivo pelo MQTT.

```text
1. Coleta (CSV na placa)
        |
        v
2. Anotar o sopro e treinar no computador
        |
        v
   ml/models/sob_efeito.joblib
        |
        v
3. Docker no computador da bancada
   ESP32 --MQTT--> Mosquitto --> worker --> Postgres
                                    |
                                    +--> servidor do modelo --> mq3/<placa>/resultado
```

A placa só conversa com o Mosquitto. O Mosquitto é o programa que entrega as mensagens MQTT (porta 1883). O worker e o servidor do modelo também falam com ele. Os três ficam no Docker, no computador que está na mesma rede da ESP32.

## 1. Captar os dados

A ESP32 já grava uma linha por segundo num CSV da sessão (`leituras_N.csv`), do ligar até o reiniciar. Cada linha tem o tempo `t_ms` e as leituras dos três sensores. A placa não descobre sozinha quando alguém soprou. Quem conduz o teste anota isso.

Para cada bateria (30 s ou 60 s, por exemplo):

1. Ligue a placa e deixe gravando.
2. Faça um cenário só.
3. Se alguém soprar, anote o segundo de início e o de fim. Numa sessão de 60 s em que o sopro foi do 30 ao 50, a marcação é 30 e 50.
4. Anote a condição, uma destas: `clean`, `perfume`, `alcohol70_spray`, `alcohol70_hands`, `mouthwash`, `drink`.
5. Copie o CSV para `ml/data/raw/sessions/` sem editar. Como a numeração recomeça em cada placa, use um nome único, por exemplo `2026-11-05_p01_leituras_3.csv`.
6. Acrescente uma linha em `ml/data/raw/attempts.csv` (o cabeçalho está em `ml/templates/attempts_template.csv`).

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

Dentro de `ml/`, com o ambiente ligado (`python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`):

```bash
python -m src.cli validate
python -m src.cli all
```

`validate` confere os CSVs e as linhas do `attempts.csv`. `all` faz o resto:

1. Recorta cada sopro: 15 s antes, o intervalo anotado e 30 s depois.
2. Resume esse recorte numa linha de features (valor de antes, pico, subida, tempo até o pico, recuperação, e o que a umidade fez junto).
3. Separa treino e teste por pessoa. A mesma pessoa não fica dos dois lados.
4. Compara os modelos e grava `ml/models/sob_efeito.joblib`.

Esse arquivo é o modelo. Ele ainda não existe: falta coleta das duas classes, com várias pessoas. Três sessões de uma pessoa só não fecham o treino. Os detalhes dos comandos estão em `ml/README.md`.

Quando a rodada já está no Postgres, o mesmo fluxo roda no Airflow. O `docker compose up` não sobe esse serviço.

Na raiz do repositório:

```bash
docker compose --profile airflow up -d --build
```

A interface fica em http://localhost:8088. O usuário é `admin`. A senha:

```bash
docker compose exec airflow cat /opt/airflow/standalone_admin_password.txt
```

Abra o DAG `dataset_para_treino` e aperte o play. Ele não tem horário: cada execução é manual. As cinco tarefas, nesta ordem:

1. **ingerir** copia do Postgres as rodadas encerradas que ainda não estão em `ml/data/raw/`. Um CSV de sessão que já existe não é reescrito.
2. **preparar** recorta os sopros, calcula as features e separa treino e teste.
3. **disponibilizar** grava `ml/data/processed/disponivel.json`.
4. **treinar** compara os modelos só com o treino.
5. **testar** avalia o modelo escolhido uma vez no teste.

O número de cada etapa está na aba **XCom** da caixa, na chave `return_value`. O treino também fica em `ml/reports/experiment.csv`; o teste, em `ml/reports/final.json` e em `ml/models/sob_efeito.joblib`.

Outro play, com os mesmos CSVs e o mesmo `ml/config/split.json`, repete o resultado. Para sortear de novo quem fica no teste, apague esse arquivo e dispare o DAG com outra semente, por exemplo `{"seed": 7}` na configuração do disparo. Com a semente 42 o sorteio volta a ser o mesmo.

## 3. Rodar o modelo

Há dois jeitos, e os dois usam o mesmo `.joblib`.

**Num CSV já gravado**, de dentro de `ml/`:

```bash
python -m src.cli predict --session data/raw/sessions/2026-11-05_p01_leituras_3.csv --blow-start-s 30 --blow-end-s 50
```

A resposta sai no terminal: `sob_efeito` ou `sem_efeito`.

**Ao vivo**, o servidor do modelo é o container `model` do Docker. O código está em `services/mq3mqtt/ao_vivo.py`. Ele lê `ml/models/sob_efeito.joblib`. Enquanto esse arquivo não existir, a resposta publicada é `sem_modelo` e a classe fica vazia.

## 4. Como o MQTT funciona

MQTT é o protocolo. Mosquitto é o programa que recebe e entrega essas mensagens. Ele sobe junto com o resto, na raiz do repositório:

```bash
docker compose up -d --build
```

Num teste, com a placa ligada na mesma rede:

1. Cada segundo a ESP32 (ou a ponte serial, ou o simulador) publica uma leitura em `mq3/<placa>/leituras`, com as mesmas colunas do CSV.
2. No começo do sopro publica `sopro_inicio` em `mq3/<placa>/eventos`. No fim, `sopro_fim`.
3. O ingestor recebe essas mensagens e grava no PostgreSQL. A mesma amostra da mesma rodada não entra duas vezes.
4. A cada `sopro_fim`, o servidor do modelo espera 35 s (a janela depois do sopro usada no treino), lê a rodada no banco, recorta o sopro como no treino, grava em `resultados` e publica em `mq3/<placa>/resultado`.

A aba Ao vivo da tela mostra essa classe no card "Modelo de ML", com um alerta quando é `sob_efeito`. Com `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` no `.env`, o serviço `alerta` manda a mesma detecção pelo Telegram.

Os CSVs usados no treino não passam de novo pelo MQTT. O MQTT leva o teste que está acontecendo agora.

Sem a placa, o simulador republica um CSV que ela já gravou. `--sopros` são os segundos em que cada sopro começou, os mesmos do `attempts.csv`; o fim sai `--duracao` segundos depois (padrão 5). De dentro de `applications/`:

```bash
source ../ml/.venv/bin/activate
python -m coleta.simulador ../esp32-esp8266/leituras.csv --caso clean --participante p00 --sopros 30 --intervalo 0.2
```

Troque o CSV e os segundos pelos do teste de vocês. Os tópicos estão em `ARCHITECTURE.md`.

## Onde está cada coisa

| Pasta | Função |
| --- | --- |
| `esp32-esp8266/` | ESP32. Grava o CSV. Ainda não publica MQTT. |
| `ml/` | Validação, recorte, treino e previsão nos arquivos. |
| `services/` | Servidor do modelo: ao vivo (MQTT + banco) e HTTP da aba Modelo. |
| `docs/` | Requisitos das disciplinas e o PDF de decisões. |
| `AGENTS.md` | Regras para quem continua o projeto. |

O PDF em `docs/decisoes_projeto_ml.pdf` está velho nas classes. Vale a tabela do começo deste arquivo.
