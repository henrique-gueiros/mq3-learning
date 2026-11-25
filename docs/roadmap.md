# Roadmap — Sopro Seguro

Estado do projeto, entregáveis das disciplinas e próximos passos. Atualize quando
uma tarefa terminar. O mapa do sistema está em `ARCHITECTURE.md`.

## Datas e avaliação — Sistemas Embarcados

Fonte: `docs/Projeto-Embarcados_CesarSchool-CSBC.pdf`.

- **17/11** checkpoint (protótipo, código-fonte, arquitetura, dashboard e protótipo do front-end).
- **03/12** relatório (modelo CSBC/ABNT2) e repositório.
- **12/12** apresentação na Mostra TechDesign.
- Avaliação: funcionamento com MQTT, dashboard em tempo real, relatório, organização do GitHub (README detalhado, commits de todos) e apresentação. Bônus: alertas por e-mail ou mensageiro e comunicação em IPv6.

## Entregáveis — Machine Learning

Fonte: coluna CC de `docs/Entregáveis 6ºP - Projeto 2026.2.xlsx`.

1. **Infraestrutura e dataset inicial:** coleta própria (CSVs + `attempts.csv`), publicação por MQTT e gravação em banco.
2. **Pipeline no Airflow** (ingestão, preparação, disponibilização) e **notebook de EDA** em `ml/notebooks/`, justificando limpeza, normalização e ausentes. Lógica reutilizável em `ml/src/`.
3. **Baseline** justificado, com métricas de validação, no **MLflow**.
4. **Três modelos ou mais** comparados no MLflow, com matriz de confusão, ROC/AUC e análise crítica. Hoje: árvore e Random Forest além do baseline; KNN é candidato.
5. **Otimização de hiperparâmetros** (Grid Search pronto; Random Search ou Optuna são alternativas), documentada e no MLflow.
6. **Validação cruzada k-fold** com estabilidade entre folds, overfitting/underfitting (treino × validação) e generalização. O k-fold é `GroupKFold` por participante.
7. **Integração:** o pipeline consome dados novos da ESP32 (ou do simulador), processa e infere.
8. **Docker Compose** com broker, banco, Airflow, MLflow, API e dashboard, subindo com um comando.
9. **Dashboard** consumindo MQTT e/ou API, com indicadores, inferências e monitoramento (a tela React).
10. **Apresentação** da arquitetura, com decisões técnicas e limitações.

Métricas: F1 macro, acurácia balanceada, precisão e recall por classe, matriz de
confusão. Prioridade: **recall de `sob_efeito`**.

## Estado (17/11/2026)

Pronto e testado:
- Firmware lendo os três sensores e gravando CSV por sessão.
- Pipeline de ML em `ml/src/` (validação, recorte, features, separação por participante, 3 modelos × 4 conjuntos de sensores, Grid Search aninhado por grupo, modelo final e previsão), testado com curvas montadas à mão.
- Coleta em `applications/`: ponte serial, ingestor, simulador, importador, lote dos 12 CSVs válidos, Compose com Mosquitto, Postgres e API.
- Tela React no Compose (http://localhost:8080): ao vivo, detector ambiente × sopro e as quatro seções de análise, com os números conferidos contra o Grafana local (removido em 24/11). O acabamento visual da etapa 5 está feito. O Lighthouse de acessibilidade deu 100 em 17/11. Plano em `docs/superpowers/plans/2026-11-17-frontend-react.md`.
- Contrato MQTT único (o da coleta, 24/11): o servidor do modelo (`services/mq3mqtt/ao_vivo.py`) assina `eventos`, lê a rodada no banco da coleta, grava em `resultados` e publica `mq3/<placa>/resultado` (`sem_modelo` até haver modelo). O simulador publica início e fim de sopro. A stack paralela de `services/` foi removida. A aba Ao vivo mostra a classe do modelo e o alerta; o serviço `alerta` envia pelo Telegram (bônus).
- DAG do Airflow `dataset_para_treino`: lê rodadas encerradas no Postgres, grava o que ainda não está em `ml/data/raw/` e disponibiliza `ml/data/processed/disponivel.json`. Sobe com o Compose único (`docker compose up -d --build`; interface em http://localhost:8088, MLflow em http://localhost:5050).

Ainda não existe:
- [ ] Coleta rotulada suficiente (`attempts.csv` com sopros marcados), com as duas classes.
- [ ] Revisão das features com dados reais. A análise exploratória existe em `ml/notebooks/01_eda.ipynb` (figuras em `ml/reports/figuras_eda/`), com as seções do diário e o veredito de cada uma; falta a equipe interpretar (células "[EQUIPE: interpretar]") e decidir as sessões anteriores a 10/11, o aquecimento do MQ-3 e os trios de bebida.
- [ ] Modelo treinado e avaliado com dados reais (métricas dos testes automatizados **não** dizem nada sobre o sensor).
- [ ] Testar na placa o firmware FreeRTOS ao vivo (Wi-Fi, MQTT, IPv6). A placa não grava CSV nem marca sopro.
- [x] MLflow e um Compose único com todos os serviços (24/11): `docker compose up -d --build` sobe broker, banco, ingestor, API, tela, modelo, alerta, Airflow e MLflow; rede com IPv6.
- [x] Registro no MLflow (`ml/src/rastreio.py`), métricas por fold, F1 treino × validação, ROC/AUC e figuras (`ml/src/figuras.py`).
- [x] Firmware com FreeRTOS (sensores + rede), Wi-Fi e MQTT no contrato da coleta — sem CSV e sem botão; **falta testar na placa**.

## Próximas tarefas, em ordem

1. Rodar o Lighthouse de acessibilidade da tela (meta ≥ 95) antes da mostra.
2. Coleta com a ponte (`applications/README.md`, "Dia de coleta"), com sopros marcados, e conferência com `python -m src.cli validate`.
3. Equipe: ler o `01_eda.ipynb`, interpretar e decidir as pendências marcadas. A EDA aponta o que coletar: sopros sem álcool (`clean` e `mouthwash` com sopro), `alcohol70_hands`/`alcohol70_spray`, mais de um participante e anotar gelo e boca aberta em `notes`.
4. Rodar o experimento com dados reais pelo DAG; o registro no MLflow, o desvio entre folds e a comparação treino × validação já existem.
5. Testar o firmware na placa (Wi-Fi, MQTT, IPv6) com quem mantém o firmware.
