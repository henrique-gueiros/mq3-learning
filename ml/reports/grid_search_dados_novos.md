# Grid search nos dados novos de sob efeito

Treino com 11.325 tentativas (11.131 sem efeito e 194 sopros originais de álcool), em 12 arquivos. As 1.195 tentativas do bloco novo ficaram fora do ajuste e da validação cruzada. São as 4.280 leituras copiadas no fim dos quatro CSVs de álcool; outras 38 tentativas novas não têm feature de MQ-3 e não entram na conta.

A grade usa `GroupKFold` por arquivo de sessão. No laço de dentro, a regressão logística testa `C` em 0,1, 1 e 10; a árvore testa profundidade 2, 3, 5 ou livre e folha mínima 1 ou 3; a floresta testa profundidade 3 ou livre e folha mínima 1 ou 3. Em parte dos folds internos só restou a classe sem efeito, porque o sob efeito está em quatro arquivos. Nesses folds a logística não ajusta e a nota da grade fica vazia.

## Validação cruzada no treino

Métrica de escolha: F1 macro. A tabela completa está em `grid_search_dados_novos_cv.csv`.

| Sensores | Modelo | F1 macro | Acurácia balanceada | Recall sob efeito | Precisão sob efeito |
|---|---|---:|---:|---:|---:|
| MQ-3 | baseline | 0,496 | 0,500 | 0,000 | 0,000 |
| MQ-3 | regressão logística | 0,607 | 0,912 | 0,912 | 0,153 |
| MQ-3 | árvore | 0,641 | 0,819 | 0,686 | 0,200 |
| MQ-3 | floresta | 0,635 | 0,780 | 0,603 | 0,196 |
| MQ-3 + MQ-135 | regressão logística | 0,579 | 0,779 | 0,639 | 0,121 |
| MQ-3 + MQ-135 | árvore | 0,524 | 0,574 | 0,211 | 0,055 |
| MQ-3 + MQ-135 | floresta | 0,488 | 0,490 | 0,046 | 0,012 |
| MQ-3 + umidade | regressão logística | 0,756 | 0,930 | 0,887 | 0,373 |
| MQ-3 + umidade | árvore | 0,735 | 0,911 | 0,851 | 0,341 |
| MQ-3 + umidade | floresta | 0,738 | 0,911 | 0,851 | 0,346 |
| MQ-3 + MQ-135 + umidade | regressão logística | 0,749 | 0,917 | 0,861 | 0,365 |
| MQ-3 + MQ-135 + umidade | árvore | 0,735 | 0,911 | 0,851 | 0,341 |
| MQ-3 + MQ-135 + umidade | floresta | 0,758 | 0,913 | 0,851 | 0,385 |

A melhor combinação na validação é a floresta com MQ-3, MQ-135 e umidade: F1 macro 0,758, recall de sob efeito 0,851, precisão de sob efeito 0,385.

## Teste nas 1.195 tentativas novas

> **Nota (25/11/2026):** as 1.195 tentativas deste teste são cópias de leituras de sopros que estão no próprio treino. Por isso o recall perto de 1,00 aqui mostra que o modelo reconhece o que já viu, e não que generaliza. Para generalização, veja `grid_search_cinco_testes.md` (arquivo de bebida inédito) e o teste por arquivo em `final.json`.

Cada modelo foi reajustado no treino inteiro, com a grade escolhida por arquivo. O teste só tem sob efeito, então a precisão de sob efeito fica em 1 quando o modelo acerta algum, e o F1 macro não serve para comparar. O número que vale é o recall.

| Sensores | Modelo | Parâmetros | Acertos | Recall sob efeito |
|---|---|---|---:|---:|
| MQ-3 | baseline | — | 0/1195 | 0,000 |
| MQ-3 | regressão logística | C = 0,1 | 1171/1195 | 0,980 |
| MQ-3 | árvore | profundidade 2, folha 1 | 1195/1195 | 1,000 |
| MQ-3 | floresta | profundidade livre, folha 3 | 1134/1195 | 0,949 |
| MQ-3 + MQ-135 | regressão logística | C = 0,1 | 1178/1195 | 0,986 |
| MQ-3 + MQ-135 | árvore | profundidade 2, folha 1 | 1195/1195 | 1,000 |
| MQ-3 + MQ-135 | floresta | profundidade 3, folha 1 | 1195/1195 | 1,000 |
| MQ-3 + umidade | regressão logística | C = 0,1 | 1190/1195 | 0,996 |
| MQ-3 + umidade | árvore | profundidade livre, folha 1 | 1147/1195 | 0,960 |
| MQ-3 + umidade | floresta | profundidade livre, folha 3 | 1149/1195 | 0,962 |
| MQ-3 + MQ-135 + umidade | regressão logística | C = 10 | 1185/1195 | 0,992 |
| MQ-3 + MQ-135 + umidade | árvore | profundidade 2, folha 1 | 1195/1195 | 1,000 |
| MQ-3 + MQ-135 + umidade | floresta | profundidade 3, folha 1 | 1195/1195 | 1,000 |

As matrizes e o recorte por arquivo estão em `grid_search_dados_novos.json`. As leituras novas são cópia das leituras originais do mesmo arquivo, e esses originais continuam no treino.
