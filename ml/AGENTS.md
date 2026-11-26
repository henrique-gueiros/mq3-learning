# AGENTS.md — ml/

Pipeline de ML (uso e comandos em `ml/README.md`). Vale junto com o `AGENTS.md` da raiz.

- **Separação por participante** (`participant_id`) ou, com poucos participantes, por arquivo de sessão: a mesma pessoa fica de um lado só, e as leituras de um sopro ficam juntas. Validação cruzada com `GroupKFold`; um k-fold comum infla as métricas.
- A bateria não tem cota fixa. Cada lado usa o que os arquivos têm da classe menor, e o mesmo número da outra, espalhado entre os arquivos. O arquivo não é partido. `--por-classe` ainda impõe um teto. Ficam de fora os três `leituras_bebida*.csv`, `leituras_20_sensor_Instavel.csv`, `leituras_novos_acima_08.csv`, `leituras_conversa1.csv` e os extratos `2026-11-12_equipe_drink_*.csv` (o álcool é o CSV completo `leituras_*alcool*.csv`). Antes da bateria, cada sessão fica com uma tentativa por janela de features (15 s antes e 30 s depois não se misturam). `features_all.csv` guarda essas tentativas, antes do equilíbrio.
- O modelo da execução é a regra das subidas (`subidas`): umidade e MQ-3 subiram em relação ao começo do arquivo (os primeiros 20 s), com os limiares medidos no treino. A subida contra os 15 s de antes zera quando o sensor já está alto. O MQ-135 entra na matriz e não é condição. O patamar (`before`, `peak`) continua no CSV e fica fora dessa decisão.
- Hiperparâmetros escolhidos só dentro do treino (a validação cruzada aninhada por grupo já faz isso); o teste é usado uma única vez.
- Features: `mq3_raw`, `mq135_raw`, `humidity_pct` (temperatura fora: não distingue hálito de ambiente). Revisar `src/features.py` depois da análise exploratória.
- A inferência usa o mesmo `Pipeline` do scikit-learn do treino. O scikit-learn é fixo em 1.6.1 (aqui e em `services/Dockerfile.model`): o `.joblib` só abre na versão que o gravou.
- Métricas: F1 macro, acurácia balanceada, precisão e recall por classe, matriz de confusão; prioridade no recall de `sob_efeito`.
- Lógica reutilizável em `src/`; notebooks em `notebooks/` só chamam essa lógica. Caminhos via `src/paths.py`.
- O DAG em `dags/` só chama `src/pipeline.py` (ingestão, preparação, disponibilização). A ingestão não reescreve CSV de sessão; o dataset de treino sai em `data/processed/`.
- Arquivo de bebida (nome ou origem no lote com "alcool"): o `prepare` monta um sopro a cada 3 amostras e descarta o trio se algum PPM fica abaixo de 0,6. O PPM não é rótulo nem feature.
- Arquivo sem álcool: umidade >= 60% (hipótese desta coleta) agrupa 3 amostras; abaixo disso, uma amostra por linha. Perfume, ar limpo e enxaguante entram como `sem_efeito`. No `attempts.csv` do `prepare` só existem `sem_efeito` e `sob_efeito`. A umidade não decide quem bebeu.
- Testes: `python -m pytest` (de `ml/`, com o `.venv` ativo).
