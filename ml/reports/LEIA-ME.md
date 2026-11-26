# Relatórios de ML

| Arquivo | O que é | Mede generalização? |
| --- | --- | --- |
| `final.json`, `experiment.csv`, `folds.csv`, `figuras/` | Saída do pipeline (DAG `dataset_para_treino`, 25/11/2026), com os três sensores e teste por arquivo (`ml/config/split.json`) | sim: o teste tem 4 arquivos que o treino não viu |
| `por_arquivo.*` | Validação deixando um arquivo de fora, 12 arquivos, 3 modelos (`python -m src.por_arquivo`) | sim: cada arquivo é testado sem ser visto |
| `variacoes.*` | Arquivo de fora com balanceamento (peso, sem peso, corte por arquivo) e features (todas, só variação) | sim |
| `grid_search_cinco_testes.*` | Cinco recortes só com tentativas originais | sim |
| `grid_search_tres_sensores.*`, `grid_search_dados_novos.*` | Validação cruzada por arquivo; teste nas cópias | a validação sim; o teste nas cópias não (ver a nota em cada arquivo) |
| `grid_search_balanceado.pdf` | Classes equilibradas; 1.195 das 1.389 tentativas `sob_efeito` são cópias, e uma cópia cai no mesmo fold que o original | não |
| `figuras_eda/` | Figuras do `notebooks/01_eda.ipynb` | — |

As leituras copiadas no fim dos quatro CSVs de álcool foram acrescentadas por orientação do professor.
