# AGENTS.md — ml/

Pipeline de ML (uso e comandos em `ml/README.md`). Vale junto com o `AGENTS.md` da raiz.

- **Separação por participante** (`participant_id`) ou, com poucos participantes, por arquivo de sessão: a mesma pessoa fica de um lado só, e as leituras de um sopro ficam juntas. Validação cruzada com `GroupKFold`; um k-fold comum infla as métricas.
- Hiperparâmetros escolhidos só dentro do treino (a validação cruzada aninhada por grupo já faz isso); o teste é usado uma única vez.
- Features: `mq3_raw`, `mq135_raw`, `humidity_pct` (temperatura fora: não distingue hálito de ambiente). Revisar `src/features.py` depois da análise exploratória.
- A inferência usa o mesmo `Pipeline` do scikit-learn do treino. O scikit-learn é fixo em 1.6.1 (aqui e em `../services/Dockerfile.model`): o `.joblib` só abre na versão que o gravou.
- Métricas: F1 macro, acurácia balanceada, precisão e recall por classe, matriz de confusão; prioridade no recall de `sob_efeito`.
- Lógica reutilizável em `src/`; notebooks em `notebooks/` só chamam essa lógica. Caminhos via `src/paths.py`.
- Testes: `python -m pytest` (de `ml/`, com o `.venv` ativo).
