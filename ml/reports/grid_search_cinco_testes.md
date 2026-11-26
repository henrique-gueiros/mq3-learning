# Cinco grid searches com recortes diferentes

Sempre MQ-3, MQ-135 e DHT11. A grade interna escolhe os hiperparâmetros por `GroupKFold`: a árvore testa profundidade 2, 3, 5 ou livre e folha mínima 1 ou 3; a floresta testa profundidade 3 ou livre e folha mínima 1 ou 3. O laço externo também separa por arquivo, exceto no teste do perfume.

Os cinco testes usam só as tentativas originais: 11.325 no total, 194 sob efeito e 11.131 sem efeito. As 1.195 tentativas copiadas no fim dos quatro CSVs de álcool ficam de fora. A tabela completa está em `grid_search_cinco_testes.csv` e as matrizes em `grid_search_cinco_testes.json`.

| Teste | O que muda | Melhor na validação | F1 macro | No teste separado |
|---|---|---|---:|---|
| Sem o ambiente grande | tira `leituras_28_ambiente.csv` do treino | floresta | 0,758 | 7.724/7.724 sem efeito |
| Perfume contra álcool | 100 de perfume e 194 sopros originais | floresta | 0,952 | não há teste separado |
| Sem `leituras_11_alcool.csv` | 23 sopros originais desse arquivo no teste | árvore | 0,730 | árvore 22/23 |
| Sem `leituras_17_Alcool.csv` | 65 sopros originais desse arquivo no teste | árvore | 0,591 | floresta 48/65 |
| Últimos 30% de cada arquivo | corte no tempo, dentro do mesmo CSV | floresta | 0,739 | árvore 54/60 sob efeito e 3.344/3.344 sem efeito |

## 1. Originais sem o ambiente grande

Treino com 3.601 tentativas (194 sob efeito e 3.407 sem efeito) em 11 arquivos. O teste é `leituras_28_ambiente.csv`: 7.724 tentativas, todas sem efeito.

Validação cruzada:

| Modelo | F1 macro | Acurácia balanceada | Recall sob efeito | Precisão sob efeito | Recall sem efeito | ROC AUC |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0,486 | 0,500 | 0,000 | 0,000 | 1,000 | 0,500 |
| árvore | 0,721 | 0,875 | 0,840 | 0,349 | 0,911 | 0,880 |
| floresta | 0,758 | 0,909 | 0,892 | 0,405 | 0,925 | 0,972 |

No arquivo 28, os três modelos marcaram as 7.724 tentativas como sem efeito. A árvore saiu com profundidade 2 e folha 1, a floresta com profundidade livre e folha 1.

## 2. Perfume contra álcool original

194 sopros originais de álcool e 100 tentativas de `leituras_25_perfume.csv`. Cada arquivo foi cortado em quatro fatias de tempo, e a fatia de mesmo número junta perfume e álcool, para cada grupo ter as duas classes. Não há teste separado.

| Modelo | F1 macro | Acurácia balanceada | Recall sob efeito | Precisão sob efeito | Recall sem efeito | ROC AUC |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0,398 | 0,500 | 1,000 | 0,660 | 0,000 | 0,500 |
| árvore | 0,850 | 0,863 | 0,856 | 0,927 | 0,870 | 0,863 |
| floresta | 0,952 | 0,966 | 0,933 | 1,000 | 1,000 | 1,000 |

O F1 de treino da árvore e da floresta ficou em 1,000, acima do F1 da validação. O conjunto tem 294 tentativas.

## 3. Arquivo inédito: leituras_11_alcool.csv

Treino com os outros originais: 11.302 tentativas, 171 sob efeito e 11.131 sem efeito. Teste: 23 sopros originais desse arquivo.

Validação cruzada no treino:

| Modelo | F1 macro | Acurácia balanceada | Recall sob efeito | Precisão sob efeito | ROC AUC |
|---|---:|---:|---:|---:|---:|
| baseline | 0,496 | 0,500 | 0,000 | 0,000 | 0,500 |
| árvore | 0,730 | 0,933 | 0,895 | 0,324 | 0,894 |
| floresta | 0,629 | 0,663 | 0,345 | 0,224 | 0,949 |

No arquivo deixado de fora:

| Modelo | Parâmetros | Acertos |
|---|---|---:|
| baseline | — | 0/23 |
| árvore | profundidade 5, folha 3 | 22/23 |
| floresta | profundidade livre, folha 3 | 20/23 |

## 4. Arquivo inédito: leituras_17_Alcool.csv

Treino com 11.260 tentativas, 129 sob efeito e 11.131 sem efeito. Teste: 65 sopros originais desse arquivo.

Validação cruzada no treino:

| Modelo | F1 macro | Acurácia balanceada | Recall sob efeito | Precisão sob efeito | ROC AUC |
|---|---:|---:|---:|---:|---:|
| baseline | 0,497 | 0,500 | 0,000 | 0,000 | 0,500 |
| árvore | 0,591 | 0,679 | 0,388 | 0,136 | 0,676 |
| floresta | 0,591 | 0,630 | 0,279 | 0,149 | 0,946 |

No arquivo deixado de fora:

| Modelo | Parâmetros | Acertos |
|---|---|---:|
| baseline | — | 0/65 |
| árvore | profundidade 5, folha 1 | 43/65 |
| floresta | profundidade livre, folha 3 | 48/65 |

## 5. Últimos 30% de cada arquivo

Em cada CSV original, os primeiros 70% treinam e os últimos 30% testam. Treino: 7.921 tentativas (134 sob efeito e 7.787 sem efeito). Teste: 3.404 tentativas (60 sob efeito e 3.344 sem efeito).

Validação cruzada no treino, ainda separando por arquivo:

| Modelo | F1 macro | Acurácia balanceada | Recall sob efeito | Precisão sob efeito | ROC AUC |
|---|---:|---:|---:|---:|---:|
| baseline | 0,496 | 0,500 | 0,000 | 0,000 | 0,500 |
| árvore | 0,697 | 0,920 | 0,881 | 0,273 | 0,872 |
| floresta | 0,739 | 0,919 | 0,866 | 0,345 | 0,982 |

No corte final de cada arquivo, a árvore acertou 54/60 sob efeito e 3.344/3.344 sem efeito. A floresta acertou 53/60 sob efeito e também as 3.344 tentativas sem efeito. As janelas vizinhas do mesmo CSV compartilham leituras, então esse corte não é uma sessão nova.
