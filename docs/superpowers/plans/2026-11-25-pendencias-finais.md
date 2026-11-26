# Plano: pendências finais dos requisitos

> **Para quem continuar (pessoa ou agente):** leia "Andamento" primeiro e atualize essa
> seção no mesmo commit de cada etapa. A revisão que originou este plano está em
> `docs/revisao-requisitos.md`. Regras do projeto: `AGENTS.md` (TDD, code-review antes de
> cada commit, commits em português **sem linha de coautoria**, dados só da coleta da
> equipe, CSV de sessão sem edição).

## Contexto

Em 25/11/2026 a `main` (`ae7ea25`) tem toda a arquitetura das duas disciplinas. A revisão
achou quatro problemas de código e de dados, mais as entregas da equipe. As entregas são:
- relatório CSBC até **03/12**;
- apresentação em **12/12**.

## Andamento (25/11/2026, noite)

**Decisões do usuário em 25/11:**
- As leituras copiadas nos CSVs de álcool **ficam**: foram orientação do professor. Não registrar no `AGENTS.md`. Os relatórios que testam nas cópias ganharam nota; o índice está em `ml/reports/LEIA-ME.md`.
- O grid search **não precisa** ir para o MLflow: os hiperparâmetros já estão definidos. O grid search aninhado do pipeline já registra no MLflow.
- Inferência ao vivo sem a ponte: **modelo contínuo** (janela deslizante), não regra de umidade.
- Avaliação **por arquivo**, com as cópias junto do arquivo delas.
- Treino **pelo DAG**, cujo contêiner tem scikit-learn 1.6.1.

| Etapa | Estado |
| --- | --- |
| 0. Ambiente local | pendente: `.venv` em Python 3.14 com scikit-learn 1.9.1; cópias do Finder `* 2*` |
| 1. Leituras copiadas | **resolvida por decisão** (ficam); notas nos relatórios |
| 2. Inferência sem a ponte | **feita**: modelo contínuo em `services/mq3mqtt/ao_vivo.py`; alerta só com 3 janelas `sob_efeito` seguidas (tela e Telegram) |
| 3. Resultados com os três sensores | **feita**: DAG por `session_file` em 25/11; `final.json` = Random Forest com `mq3+mq135+dht11`; runs no MLflow |
| 4. Script dos grid searches | **cancelada** (decisão do usuário) |
| 5. Limpezas | pendente |
| 6. Verificação final | parcial (testes e ponta a ponta do contínuo feitos) |
| 7. Equipe | 👥 |

**Desempenho medido em 25/11** (teste com 4 arquivos que o treino não viu; `ml/config/split.json`):
- validação cruzada no treino: F1 macro 0,98 (± 0,24 entre folds);
- teste: F1 macro 0,78, acurácia balanceada 0,89, recall `sob_efeito` 1,00, precisão `sob_efeito` 0,51.

| Arquivo de teste | Resultado |
| --- | --- |
| `drink_4` (com as cópias dele) | 421/421 `sob_efeito` |
| `clean_1` | 152/152 `sem_efeito` |
| `clean_6` | 312/1.627 marcados `sob_efeito` (19% de alarme falso) |
| `perfume_1` | **89/100 marcados `sob_efeito`** (o treino não tem nenhum perfume) |

No ponta a ponta contínuo com `esp32-esp8266/leituras.csv`, o trecho de álcool no ar **sem sopro** (descrito no `decisoes_projeto_ml.pdf`) saiu `sob_efeito`.

**Validação deixando um arquivo de fora** (25/11, `ml/reports/por_arquivo.md`, `python -m src.por_arquivo`):

| Modelo | F1 macro | Recall `sob_efeito` | Perfume de fora |
| --- | ---: | ---: | ---: |
| logística | 0,919 | 0,961 | 100/100 |
| árvore | 0,941 | 0,998 | 17/100 |
| floresta | 0,938 | 0,952 | 17/100 |

Só a logística generaliza para o perfume sem ter visto perfume no treino. O modelo em produção hoje é a floresta, escolhida pelo F1 da validação. **Decisão da equipe:** trocar o modelo final pela logística (`python -m src.cli train --select-by ...` ou fixar o modelo).

**Variações de treino** (25/11, `ml/reports/variacoes.md`):
- **Floresta sem `class_weight`** acerta o perfume (100/100) e o `clean_6` (0,90), com recall de bebida 0,89 e precisão 0,88.
- **Logística com corte por arquivo** tem a melhor média por arquivo (0,967) e o melhor pior caso (0,83).
- Só as features de variação pioram tudo.
- Deixar um dia de fora não serve: todas as bebidas são de 12/11.

**Sem regressão logística** (25/11, decisão do usuário: a disciplina não cobriu). O pipeline compara baseline, KNN, árvore e floresta, e o peso da bebida entra no grid das árvores. Em `ml/reports/variacoes_sem_logistica.md`, a melhor configuração é a **floresta sem peso + limiar escolhido no treino**: recall de bebida 0,933, precisão 1,000, perfume 1,00, média por arquivo 0,975.

**Feito em 26/11:** a floresta sem peso com limiar está no arquivo servido (`models/sob_efeito.joblib`, ignorado pelo Git; métricas em `reports/final.json`).
- `class_weight` nenhum, 100 árvores, profundidade livre, folha mínima 1, limiar **0,51**;
- teste único dos 4 arquivos: F1 macro 0,771, recall de bebida 1,000 (421/421), precisão 0,501; perfume 6/100, `clean_6` 1.302/1.627, `clean_1` 152/152;
- a média 0,975 de `variacoes_sem_logistica.md` continua válida para o teste que deixa um arquivo de fora. Esse número não é o do arquivo servido, porque o treino oficial não vê perfume, `clean_6`, `drink_4` nem `clean_1`;
- repetição de `esp32-esp8266/leituras.csv` sem sopro: `sem_efeito` até 33 s; de 36,8 s em diante, e no álcool no ar (152 s), `sob_efeito`.

**Decisão pendente (antiga, superada):** o modelo final. A configuração no ar é a floresta sem peso com limiar.

**Próximo passo sugerido para a equipe:** o modelo hoje confunde vapor de álcool no ar com hálito. Para corrigir:
- colocar perfume e álcool no ar também no treino (mais coleta de `perfume`/`alcohol70_*`, ou um split que deixe um arquivo de perfume no treino);
- avaliar com validação deixando um arquivo de fora por vez.

## Etapa 0 — ambiente local

1. **Cópias do Finder, fora do Git.** Apagar `* 2.*` e pastas `* 2`:
   - em `esp32-esp8266/` (`src/rede 2.cpp`, `include/config 2.h`, `lib/protocolo 2/`, `test/test_protocolo 2/`…);
   - em `services/mq3mqtt/`, `ml/src`, `ml/tests`, `ml/reports` e `applications/db/migracoes`;
   - em `applications/frontend/src/* 2`.
   - Listar antes com `find . -name '* 2*' -not -path '*/node_modules/*' -not -path '*/.venv/*'` e confirmar com o usuário: são arquivos dele.
   - Elas quebram o `pio run` por símbolos duplicados.
2. **Recriar o `.venv` com Python 3.12.** O 3.14 não tem wheel do scikit-learn 1.6.1 nem do pyarrow.
   - Com o `pyenv` ou o `python3.12` do Homebrew: `rm -rf applications/ml/.venv && python3.12 -m venv applications/ml/.venv`.
   - Depois `pip install -r ml/requirements.txt -r applications/coleta/requirements.txt -r applications/api/requirements.txt`.
   - Conferir `python -c "import sklearn; print(sklearn.__version__)"` → `1.6.1`.
3. **Pronto quando:**
   - os testes de `services/` passam inteiros, inclusive `test_classificar_http`;
   - `pio run` compila e `pio test -e native` passa 15/15.

## Etapa 1 — desfazer as leituras copiadas (regra violada)

O commit `9b49aaf` acrescentou leituras repetidas no fim de:
- `esp32-esp8266/leituras_11_alcool.csv`
- `esp32-esp8266/leituras_11_alcool2.csv`
- `esp32-esp8266/leituras_14_Alcool3.csv`
- `esp32-esp8266/leituras_17_Alcool.csv`

1. Restaurar os quatro arquivos: `git checkout 9b49aaf~1 -- <arquivos>`. Conferir as linhas: 82, 302, 145 e 202, com o cabeçalho.
2. Teste que impede a volta, em `ml/tests/test_dados_reais.py`. Para cada CSV listado no `applications/dados/lote-2026-11.csv`:
   - `t_ms` estritamente crescente;
   - o número de linhas igual ao de combinações distintas de `(mq3_raw, mq135_raw, humidity_pct, temperature_c, tensao_atual_mv)`, com tolerância documentada (leituras paradas podem se repetir). Calibrar a tolerância com os arquivos originais; a de 81 em 1.105 tem que falhar.
3. Relatórios que usam as cópias:
   - apagar `ml/reports/grid_search_balanceado.pdf`;
   - em `grid_search_tres_sensores.*` e `grid_search_dados_novos.*`, remover as seções "Teste nas 1.195 tentativas novas", ou regerar os arquivos pelo script da Etapa 4, sem esse teste.
4. `docs/roadmap.md`: registrar a remoção e o motivo (regra "sem dados sintéticos").
5. **Pronto quando:** `git grep -n "1.195\|cópias\|copiad" ml/reports` não traz mais resultados apresentados como desempenho, e o teste novo passa.

## Etapa 2 — inferência ao vivo sem a ponte

**Hoje:** a placa (`esp32-esp8266/src/rede.cpp`) publica só `rodada`, `leituras` e `status`. O servidor (`services/mq3mqtt/ao_vivo.py`) só classifica em `eventos/sopro_fim`. Com a placa sozinha no Wi-Fi, nenhum resultado aparece.

**A equipe escolhe uma das duas:**
- **A. Botão de volta na placa** (recomendado: é o protocolo da coleta).
  - Restaurar a `tarefaBotao` (`git show bc8e742:esp32-esp8266/src/botao.cpp`) só para publicar `eventos` (`sopro_inicio`/`sopro_fim`).
  - Sem CSV, porque a placa ficou "só ao vivo" em `8866871`.
  - Teste de PC do JSON do evento (`jsonEvento` já existe em `lib/protocolo`).
- **B. O servidor detecta o fim do sopro pela umidade**, só para recortar a janela, nunca para decidir a classe.
  - Portar a lógica de `applications/frontend/src/aovivo/detector.ts` para `services/mq3mqtt/sopro.py`.
  - O `ServidorAoVivo` assina também `leituras`, e quando o detector sai de "sopro" agenda `classificar_sopro` como já faz.
  - Testes com curvas montadas à mão em `services/tests/test_sopro.py`.
  - Explicar no README que o limiar só define a janela.

**Nos dois casos:**
- `ARCHITECTURE.md` e `README.md` atualizados.
- Ponta a ponta com o simulador publicando **sem** eventos (opção B) ou com a placa (A).
- A ponte continua lendo `CSV_EVENTO` (`applications/coleta/serial_proto.py`) só se a opção A também imprimir na serial. Se não, remover esse código morto e o teste.

## Etapa 3 — resultados de ML com os três sensores

Depende da Etapa 1. O pipeline (`ml/src/pipeline.py`, `SENSOR_SET_EXECUCAO`) já treina só com `mq3+mq135+dht11`, mas `ml/reports/{experiment.csv,final.json,folds.csv,figuras/}` e `ml/models/sob_efeito.*` são da execução anterior (`mq3+dht11`).

1. Copiar o lote para `ml/data/raw/sessions/` como descreve o README ("DAG e MLflow"), com os CSVs restaurados.
2. `cd ml && MLFLOW_TRACKING_URI=http://localhost:5050 python -m src.cli all --group-by session_file`. Ou disparar o DAG `dataset_para_treino`.
3. Conferir:
   - `final.json` com `"sensor_set": "mq3+mq135+dht11"`;
   - figuras regeneradas;
   - runs no MLflow (http://localhost:5050).
4. Recarregar o contêiner `model` (`docker compose restart model`) e a aba Modelo.
5. **Pronto quando:** os arquivos de `ml/reports/` batem com a execução e com o MLflow, e o teste de `services` que usa o modelo passa.

## Etapa 4 — script dos grid searches e MLflow

Os relatórios `grid_search_*` foram gerados fora do repositório. O entregável 5 pede a estratégia documentada **e** os experimentos no MLflow.

1. Novo `ml/src/grid_search.py`, que reaproveita `model_specs`, `fit_with_search`, `compute_metrics` e `nested_cv_predict` de `ml/src/train.py`.
2. Os cinco recortes de `grid_search_cinco_testes.md`:
   - sem o ambiente grande;
   - perfume contra álcool;
   - sem `leituras_11_alcool.csv`;
   - sem `leituras_17_Alcool.csv`;
   - últimos 30% de cada arquivo.
3. Gera `ml/reports/grid_search_cinco_testes.{md,csv,json}` e registra um run pai por recorte, com runs filhos por modelo, via `ml/src/rastreio.py`.
4. CLI: `python -m src.cli grid-search`. Teste em `ml/tests/test_grid_search.py` com dados montados à mão (não é desempenho real).
5. Apagar os `grid_search_*` que o script não regenera.
6. **Pronto quando:** rodar o comando reproduz o `.md` e os runs aparecem no MLflow.

## Etapa 5 — limpezas do repositório

1. `schematics/Relatorio de progresso`: dar extensão (`.md` ou `.pdf`, conforme o conteúdo).
2. Commits com `Co-authored-by: Cursor` (`1601b0b`, `8866871`): **não reescrever histórico da `main`**. Registrar no `AGENTS.md` que agentes (Cursor incluído) não adicionam coautoria.
3. A tela e o Airflow escutam em `0.0.0.0` (`FRONTEND_PORT`, `AIRFLOW_PORT`). Documentar no README que o Airflow fica acessível na rede com a senha do `standalone`. Para a Mostra, decidir se volta para `127.0.0.1`.
4. Rever o `README.md` ("Novidades de 24/11", "Como testar cada coisa") depois das Etapas 1–4.

## Etapa 6 — verificação final (Opus faz o code-review)

1. Testes de `ml/`, `applications/` (com `PG_DSN`), `services/` e front; `pio run` e `pio test -e native`.
2. `docker compose down && docker compose up -d --build`. Todos os serviços no ar; tela, API, modelo, Airflow e MLflow respondem.
3. Ponta a ponta:
   - simulador → `mq3/+/resultado` com `status: classificado` (agora há modelo);
   - card na aba Ao vivo;
   - alerta no log.
4. DAG `dataset_para_treino` com sucesso e runs novos no MLflow.
5. Atualizar `docs/revisao-requisitos.md`: cada ⚠️/❌ resolvido vira ✅, com o commit.

## Etapa 7 — da equipe (👥)

- **Testar o firmware na placa:** Wi-Fi, MQTT, IPv6 e, se for a opção A, o botão. Com `mosquitto_sub -h <ip do computador> -t 'mq3/#' -v`.
- **Coleta nova, se der tempo** (sugestões da EDA): sopros sem álcool, `alcohol70_*`, mais participantes, `notes` com gelo e boca aberta. Depois, rodar de novo o `01_eda.ipynb` e a Etapa 3.
- **Ética da coleta com bebida:** registrar no repositório a decisão (Comitê de Ética ou simulador).
- **Interpretação:** escrever as células "[EQUIPE: interpretar]" do notebook e decidir o que fazer com as sessões anteriores a 10/11.
- **Relatório CSBC** `Projeto_Embarcados_GrupoX.pdf` até 03/12, com a declaração de uso de IA. Ele vai em `docs/`.
- **Telegram:** criar o bot e preencher `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` para a demonstração.
- **Apresentação na Mostra** (12/12).

## O notebook de EDA

Não precisa rodar de novo agora: ele usa só os dados originais. **Não rode antes da Etapa 1**, porque leria as cópias. Rode de novo depois de uma coleta nova.
