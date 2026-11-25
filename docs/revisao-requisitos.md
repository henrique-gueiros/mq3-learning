# Revisão dos requisitos

Revisão de 25/11/2026 sobre a `main` em `ae7ea25`. Cada item foi comparado com os três documentos de `docs/`:

- `Projeto-Embarcados_CesarSchool-CSBC.pdf` (Sistemas Embarcados);
- `Entregáveis 6ºP - Projeto 2026.2.xlsx` (Machine Learning);
- `decisoes_projeto_ml.pdf` (decisões de ML; as classes valem as duas do `AGENTS.md`).

Legenda:
- ✅ atende;
- ⚠️ atende em parte (o que falta está no plano `docs/superpowers/plans/2026-11-25-pendencias-finais.md`);
- ❌ não atende;
- 👥 depende da equipe (não é código).

## Estado dos testes na `main`

| Suíte | Resultado | Observação |
| --- | --- | --- |
| `ml/` | 82 passam | |
| `applications/` (com Postgres) | 119 passam | |
| `services/` | 28 passam, 1 falha | `test_recortes_da_aba_recebem_a_classe_do_modelo`: o `.venv` local está em Python 3.14 com scikit-learn **1.9.1**, e o modelo foi gravado com **1.6.1**. No contêiner `model` (1.6.1) o modelo carrega. É ambiente, não código. |
| Front (`npm test`) | 205 passam | |
| Firmware `pio run` | falha **no checkout local** | Cópias do Finder sem versionamento (`src/rede 2.cpp`, `include/config 2.h`, `lib/protocolo 2/`…) duplicam símbolos. A `main` versionada não tem essas cópias. |
| Firmware `pio test -e native` | 14 de 15 | Mesma causa (`test/test_protocolo 2/`). |

## Sistemas Embarcados

| Requisito | Situação | Onde |
| --- | --- | --- |
| ESP32 com sensores | ✅ MQ-3 (GPIO 34), MQ-135 (35), DHT11 (4) | `esp32-esp8266/src/sensores.cpp` |
| Wi-Fi + MQTT saindo da ESP32 | ✅ publica `rodada` (retida), `leituras` e `status` (last will) | `esp32-esp8266/src/rede.cpp` |
| Firmware com FreeRTOS | ✅ tarefas criadas com `xTaskCreatePinnedToCore`, filas entre elas, `vTaskDelayUntil` | `esp32-esp8266/src/main.cpp`, `include/filas.h` |
| Broker MQTT (Mosquitto) | ✅ | `applications/mosquitto/`, `docker-compose.yml` |
| Aplicação web + banco | ✅ API somente leitura, Postgres e tela React | `applications/api`, `applications/db`, `applications/frontend` |
| Dashboard em tempo real (15 pts) | ✅ aba Ao vivo por WebSocket; análise pela API | `applications/frontend/src/aovivo` |
| Funcionamento: MQTT, coleta, dashboard (20 pts) | ⚠️ funciona com a ponte serial ou o simulador; **a placa sozinha no Wi-Fi não gera inferência**, porque não publica `eventos` e o servidor só classifica no `sopro_fim` | `services/mq3mqtt/ao_vivo.py` |
| IPv6 (bônus) | ✅ rede do compose com IPv6 e Mosquitto em `[::]`; a placa chama `WiFi.enableIpV6()` | `docker-compose.yml`, `rede.cpp` |
| Alerta por e-mail ou mensageiro (bônus) | ✅ Telegram, mas o envio real **não foi testado** (falta o bot) | `services/mq3mqtt/alerta.py` |
| Firmware testado na placa | 👥 compila e passa nos testes de PC; **nunca rodou no hardware** com a versão FreeRTOS | |
| Repositório: README, `docs/`, `applications/`, `esp32-esp8266/`, `schematics/` | ✅ estrutura e README com "Como testar cada coisa" | `README.md` |
| GitHub: commits colaborativos | ⚠️ `1601b0b` e `8866871` têm `Co-authored-by: Cursor`, que o `AGENTS.md` proíbe; há cópias do Finder fora do Git na máquina local | |
| `schematics/` | ⚠️ esquemático e foto existem; o arquivo `schematics/Relatorio de progresso` não tem extensão | |
| Relatório CSBC/ABNT2 em PDF (`Projeto_Embarcados_GrupoX.pdf`), até 03/12 | ❌ 👥 não está no repositório; IA só na revisão do texto, com declaração de uso | `docs/` |
| Apresentação na Mostra (12/12) | 👥 | |

## Machine Learning

| Entregável | Situação | Onde |
| --- | --- | --- |
| 1. Bootstrap dataset, aquisição, publicação MQTT e persistência | ✅ 12 sessões no lote; ingestor grava no Postgres | `applications/dados/lote-2026-11.csv`, `applications/coleta` |
| 2. Pipeline no Airflow (ingestão, preparação, disponibilização) | ✅ DAG `dataset_para_treino` | `ml/dags/dataset_para_treino.py` |
| 2. Notebook de EDA com preparação e justificativas | ✅ com dados originais; a interpretação é 👥 (células "[EQUIPE: interpretar]") | `ml/notebooks/01_eda.ipynb` |
| 3. Baseline justificado, métricas de validação, MLflow | ✅ `DummyClassifier`, registro em `ml/src/rastreio.py` | `ml/src/train.py` |
| 4. ≥3 modelos com visualizações e análise crítica | ⚠️ logística, árvore e floresta; matriz de confusão, ROC, F1 por modelo e curva de aprendizado. **Os arquivos de `ml/reports/` são de antes da troca para três sensores** (o modelo salvo é `mq3+dht11`). A análise crítica é 👥 | `ml/reports/figuras`, `final.json` |
| 5. Otimização de hiperparâmetros documentada e registrada no MLflow | ⚠️ `GridSearchCV` aninhado no pipeline (registrado no MLflow). Os relatórios `grid_search_*` não têm o script que os gera e não estão no MLflow; dois deles usam dados copiados (ver abaixo) | `ml/src/train.py`, `ml/reports/grid_search_*` |
| 6. Validação cruzada, estabilidade, over/underfitting e generalização | ✅ `GroupKFold` aninhado, desvio entre folds, F1 treino × validação | `ml/reports/folds.csv` |
| 7. Modelo integrado consumindo dados do embarcado | ⚠️ funciona com a ponte e o simulador; a placa sozinha não dispara inferência (mesmo problema de Embarcados) | `services/mq3mqtt/ao_vivo.py` |
| 8. Docker Compose com um comando | ✅ 9 serviços sem perfis | `docker-compose.yml` |
| 9. Dashboard com inferências e monitoramento | ✅ card "Modelo de ML" e alerta na aba Ao vivo; aba Modelo | `applications/frontend` |
| 10. Apresentação integrada e limitações | 👥 | |

### Regras do `decisoes_projeto_ml.pdf` e do `AGENTS.md`

| Regra | Situação |
| --- | --- |
| Só dados da equipe, sem dados sintéticos | ❌ **`9b49aaf` acrescentou leituras copiadas** no fim dos quatro CSVs de álcool (o `leituras_11_alcool.csv` foi de 81 para 1.105 linhas, com só 81 combinações de valores diferentes). |
| CSV de sessão nunca editado | ❌ mesmo commit. |
| Treino e teste separados por grupo; o teste usado uma vez | ✅ no pipeline (`ml/config/split.json` por `session_file`). ❌ nos relatórios `grid_search_tres_sensores` e `grid_search_dados_novos`, o "teste" são as cópias de sopros que estão no próprio treino (recall de 1,00 sem valor). ❌ no `grid_search_balanceado.pdf`, 1.195 das 1.389 tentativas `sob_efeito` são cópias. |
| Recall de `sob_efeito` como prioridade | ✅ reportado em todas as tabelas. |
| Não afirmar embriaguez nem mg/L | ✅ na tela e no alerta. |
| Rótulo vem da condição anotada, não de limiar | ✅ |
| Um só ambiente com scikit-learn 1.6.1 | ⚠️ o `.venv` local está com 1.9.1 (Python 3.14 não tem wheel do 1.6.1). |
| Ética da coleta com bebida | 👥 o repositório não registra a decisão (Comitê de Ética ou simulador). |

### Relatórios de `ml/reports/` na `main`

| Arquivo | Usa as cópias? | Pode ir para o relatório? |
| --- | --- | --- |
| `grid_search_cinco_testes.*` | não | sim; é o mais sólido |
| `grid_search_tres_sensores.*`, `grid_search_dados_novos.*` | só no "teste" | a validação cruzada sim; as seções "Teste nas 1.195 tentativas novas" não |
| `grid_search_balanceado.pdf` | sim, em 86% da classe `sob_efeito` | não |
| `experiment.csv`, `final.json`, `folds.csv`, `figuras/` | não | defasados; regerar com os três sensores |
| `figuras_eda/` | não | sim |

## Conclusão

A arquitetura pedida pelas duas disciplinas está implementada e testada: ESP32 com FreeRTOS, Wi-Fi e MQTT, broker, banco, ingestor, Airflow, MLflow, modelo servido, dashboard, compose único, IPv6 e alerta.

Para dizer que **tudo** segue os requisitos faltam:
1. tirar os dados copiados e as conclusões que dependem deles;
2. fazer a placa disparar a inferência sem a ponte;
3. regerar os resultados de ML com os três sensores e publicar o script dos grid searches, com os runs no MLflow;
4. arrumar o ambiente local (Python 3.12, cópias do Finder);
5. o que é da equipe: teste na placa, interpretação, relatório CSBC e apresentação.
