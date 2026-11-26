# Grid search com os três sensores

MQ-3, MQ-135 e DHT11 juntos (`mq3+mq135+dht11`). O treino e o teste do pipeline passam a usar só esse conjunto.

Treino com 11.325 tentativas (11.131 sem efeito e 194 sopros originais de álcool), em 12 arquivos. As 1.195 tentativas do bloco novo ficaram fora do ajuste e da validação cruzada. São as 4.280 leituras copiadas no fim dos quatro CSVs de álcool; outras 38 tentativas novas não têm feature de MQ-3 e não entram na conta.

A grade usa `GroupKFold` por arquivo de sessão. A árvore testa profundidade 2, 3, 5 ou livre e folha mínima 1 ou 3; a floresta testa profundidade 3 ou livre e folha mínima 1 ou 3. Em parte dos folds internos só restou a classe sem efeito, porque o sob efeito está em quatro arquivos.

## Validação cruzada no treino

Métrica de escolha: F1 macro. A tabela completa está em `grid_search_tres_sensores_cv.csv`.

| Modelo | F1 macro | Acurácia balanceada | Recall sob efeito | Precisão sob efeito | Recall sem efeito |
|---|---:|---:|---:|---:|---:|
| baseline | 0,496 | 0,500 | 0,000 | 0,000 | 1,000 |
| árvore | 0,735 | 0,911 | 0,851 | 0,341 | 0,971 |
| floresta | 0,758 | 0,913 | 0,851 | 0,385 | 0,976 |

A melhor combinação na validação é a floresta: F1 macro 0,758, recall de sob efeito 0,851, precisão de sob efeito 0,385.

## Teste nas 1.195 tentativas novas

> **Nota (25/11/2026):** as 1.195 tentativas deste teste são cópias de leituras de sopros que estão no próprio treino. Por isso o recall perto de 1,00 aqui mostra que o modelo reconhece o que já viu, e não que generaliza. Para generalização, veja `grid_search_cinco_testes.md` (arquivo de bebida inédito) e o teste por arquivo em `final.json`.

Cada modelo foi reajustado no treino inteiro, com a grade escolhida por arquivo. O teste só tem sob efeito, então o número que vale é o recall.

| Modelo | Parâmetros | Acertos | Recall sob efeito |
|---|---|---:|---:|
| baseline | — | 0/1195 | 0,000 |
| árvore | profundidade 2, folha 1 | 1195/1195 | 1,000 |
| floresta | profundidade 3, folha 1 | 1195/1195 | 1,000 |

A árvore e a floresta acertaram as 1.195 tentativas. As matrizes estão em `grid_search_tres_sensores.json`. As leituras novas são cópia das leituras originais do mesmo arquivo, e esses originais continuam no treino.
