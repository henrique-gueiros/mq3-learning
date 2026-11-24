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

### Etapas 2, 3–4 e 5 — nas worktrees: **revisadas pelo Opus, aguardando merge** (24/11, atualizado às 14h20)

| Etapa | Branch (`refs/heads/…`) | Commits | Revisão |
| --- | --- | --- | --- |
| 2. Firmware | `claude/firmware-freertos-mqtt-8086e4` | `5eeeae1`, `bc8e742` | **Pronta.** `pio run` compila e `pio test -e native` passa 14 testes. Os 2 importantes já corrigidos: eventos do botão em `CSV_EVENTO` na serial e em `/leituras_N.eventos.csv`; `CASO_PADRAO`/`PARTICIPANTE_PADRAO`. Pendentes não perdem a `rodada`. |
| 3–4. ML | `claude/ml-mlflow-avaliacao-1962b8` | `1b305f4`, `7d5a3c4`, `bad5604` | **Pronta.** Correções do review em `bad5604`; 81 testes passam; a imagem do Airflow monta e importa mlflow 2.22.5 e scikit-learn 1.6.1 (servidor MLflow 2.17.2, mesma série). |
| 5. EDA | `claude/kind-noyce-bc936c` | `5655cc6`, `4bb0014`, `d744de9` | Sem bug. Os vereditos ficaram só com rótulo e números (`d744de9`); a interpretação é da equipe. **Pronta.** |

**Integração, quando o usuário autorizar o merge** (`git merge --no-ff refs/heads/<branch>` em `fecha-requisitos`, nesta ordem: EDA, firmware, ML):
1. **Conflitos esperados:** `docs/roadmap.md` (juntar os itens) e `ml/README.md` (linha ~164: tirar `--profile airflow`; linha ~197: o worker antigo de `services/` vira `services/mq3mqtt/ao_vivo.py`).
2. **Ponte serial** (`applications/coleta/serial_proto.py` e `ponte.py`): ler a linha nova do firmware `CSV_EVENTO,<arquivo>,<tipo>,<t_ms>` e publicar o evento e marcar o sopro no `attempts.csv` como o Enter faz. Teste em `applications/coleta/tests/test_serial_proto.py`.
3. **ML:** `src/data_io.py` (`sessions_dir.glob("*.csv")`) e `amostras_sem_efeito.py`/`sopros_bebida.py` precisam ignorar `*.eventos.csv` se alguém copiar a pasta inteira da placa. Teste.
4. **Verificar:**
   - testes de `ml/`, `applications/`, `services/` e do front;
   - `docker compose up -d --build`; disparar o DAG `dataset_para_treino` e ver os runs e as figuras em http://localhost:5050;
   - `pio run` do firmware.
   - O firmware com a placa de verdade (Wi-Fi, MQTT, botão, IPv6) **não foi testado em hardware**. Isso fica para a equipe, com `mosquitto_sub -h <ip do computador> -t 'mq3/#' -v`.

### Integração (24/11, 14h20): **merge feito; falta verificar o DAG com dados e o README**

- Merge das 3 branches em `fecha-requisitos` (`5f0b429`, `ab7948b`, `38295d8`); o conflito do roadmap foi resolvido.
- A ponte lê `CSV_EVENTO` (`EventoPlaca` em `serial_proto.py`; `Rodada.marcar_*_sopro(t_ms)`), e o ML ignora `*.eventos.csv` (`data_io.arquivos_de_sessao`). O `ml/README.md` foi corrigido.
- `ml/requirements.txt` passou a usar `mlflow-skinny` (o `mlflow` completo não instala no Python 3.14 por causa do pyarrow).
- **Testes:** ml 82, applications 118, services 28, front 205, `pio run` OK e `pio test -e native` 14.
- **O DAG falhou em `preparar` por falta de dados:** `ml/data/raw/sessions` está vazio neste checkout e o banco não tem rodada real encerrada. É ambiente, não bug.

**Falta:**
1. Verificar o MLflow com dados. Numa pasta temporária, copiar o lote (`applications/dados/lote-2026-11.csv` → `esp32-esp8266/*.csv`) como na célula 6 do `01_eda.ipynb`, rodar `preparar_dataset`, `treinar_modelos` e `avaliar_teste` (`ml/src/pipeline.py`) com `MLFLOW_TRACKING_URI=http://localhost:5050` e conferir os runs na interface. Ou importar o lote no banco (`applications/README.md`, "CSVs já coletados") e disparar o DAG.
2. No README da raiz, escrever a seção "Novidades de 24/11" (contrato único, card do modelo, alerta, Grafana removido, compose único, MLflow 5050, IPv6, firmware FreeRTOS, EDA) e o guia "Como testar cada coisa":
   - testes de ml/, applications/, services/ e do front;
   - `pio run` e `pio test -e native`;
   - simulador → resultado (`mosquitto_sub -h ::1 -t 'mq3/+/resultado'`);
   - tela em 8080;
   - alerta (`docker compose logs alerta`);
   - DAG e MLflow;
   - IPv6;
   - placa (`segredos.h`, botão BOOT, `CSV_EVENTO`).
3. Code-review do diff da integração e o commit.
