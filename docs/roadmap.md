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
4. **Três modelos ou mais** comparados no MLflow, com matriz de confusão, ROC/AUC e análise crítica. Hoje: regressão logística, árvore e Random Forest além do baseline; KNN é candidato.
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
- Pipeline de ML em `ml/src/` (validação, recorte, features, separação por participante, 4 modelos × 4 conjuntos de sensores, Grid Search aninhado por grupo, modelo final e previsão), testado com curvas montadas à mão.
- Coleta em `applications/`: ponte serial, ingestor, simulador, importador, lote dos 12 CSVs válidos, Compose com Mosquitto, Postgres e API.
- Tela React no Compose (http://localhost:8080): ao vivo, detector ambiente × sopro e as quatro seções de análise, com os números conferidos contra o Grafana local. O acabamento visual da etapa 5 está feito; o Lighthouse de acessibilidade ainda não rodou. Plano em `docs/superpowers/plans/2026-11-17-frontend-react.md`.
- `services/`: worker e servidor do modelo (responde `sem_modelo` até haver modelo).

Ainda não existe:
- [ ] Coleta rotulada suficiente (`attempts.csv` com sopros marcados), com as duas classes.
- [ ] Análise exploratória e revisão das features com dados reais.
- [ ] Modelo treinado e avaliado com dados reais (métricas dos testes automatizados **não** dizem nada sobre o sensor).
- [ ] Wi-Fi/MQTT na ESP32 (hoje a ponte publica no lugar da placa).
- [ ] MLflow, Airflow e um Compose único.

## Próximas tarefas, em ordem

1. Tirar o Grafana, só com o aval da equipe (apaga pastas e serviços) — o que falta está na Etapa 7 de `docs/superpowers/plans/2026-11-17-frontend-react.md`. Rodar o Lighthouse de acessibilidade da tela (meta ≥ 95) antes da mostra.
2. Coleta com a ponte (`applications/README.md`, "Dia de coleta"), com sopros marcados, e conferência com `python -m src.cli validate`.
3. Análise exploratória, revisão das features, dos tempos do protocolo e dos limiares do detector da tela.
4. Experimento com dados reais no MLflow, com k-fold e overfitting. Aí `ml/models/sob_efeito.joblib` passa a existir.
5. A equipe escolhe um contrato MQTT e a ESP32 passa a publicar (quem mantém o firmware).
6. Airflow, resultado do modelo na tela e um Compose único.
