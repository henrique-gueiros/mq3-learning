# Validação deixando um arquivo de fora

Gerado em 25/11/2026 por `python -m src.por_arquivo` (de `ml/`, depois do `prepare`), com MQ-3, MQ-135 e DHT11. São 12 arquivos, 12.520 tentativas; as leituras copiadas ficam no mesmo arquivo dos originais.

Para cada arquivo, o modelo foi ajustado com os outros 11. O grid search escolheu os hiperparâmetros só neles, por `GroupKFold` por arquivo. Depois o modelo testou no arquivo que ficou de fora. Nenhuma leitura do arquivo testado, nem cópia dela, entra no ajuste.

Tabelas completas em `por_arquivo.csv` (por arquivo e hiperparâmetros) e `por_arquivo_resumo.csv` (por modelo).

## Juntando as previsões de todos os arquivos

| Modelo | F1 macro | Acurácia balanceada | Recall sob efeito | Precisão sob efeito | Recall sem efeito |
| --- | ---: | ---: | ---: | ---: | ---: |
| regressão logística | 0,919 | 0,963 | 0,961 | 0,776 | 0,965 |
| árvore | 0,941 | 0,985 | 0,998 | 0,813 | 0,971 |
| floresta | 0,938 | 0,965 | 0,952 | 0,836 | 0,977 |

## Por arquivo (acertos no arquivo de fora)

| Arquivo | Classe | n | Logística | Árvore | Floresta |
| --- | --- | ---: | ---: | ---: | ---: |
| `drink_1` | sob efeito | 326 | 0,914 | 0,997 | 0,920 |
| `drink_2` | sob efeito | 273 | 0,908 | 1,000 | 0,861 |
| `drink_3` | sob efeito | 369 | 0,997 | 0,995 | 0,995 |
| `drink_4` | sob efeito | 421 | 1,000 | 1,000 | 1,000 |
| `perfume_1` | sem efeito | 100 | **1,000** | 0,170 | 0,170 |
| `clean_6` (12/11) | sem efeito | 1.627 | 0,763 | 0,855 | 0,891 |
| `clean_7` (12/11) | sem efeito | 1.330 | 1,000 | 1,000 | 1,000 |
| `clean_1` a `clean_5` (14/11) | sem efeito | 8.074 | 1,000 | 1,000 | 1,000 |

## Limites

- Há um só arquivo de perfume. Quando ele fica de fora, o treino não tem nenhum perfume. As árvores marcam 83% do perfume como `sob_efeito`; a logística acerta tudo. Com um arquivo só, esse número não pode ser generalizado.
- `clean_6` é o arquivo de ar limpo do mesmo dia das bebidas (12/11). É nele que todos os modelos mais erram.
- Todos os arquivos são de um participante (`equipe`) em dois dias. As métricas são de protótipo e não valem como laudo.
- Em alguns folds internos do grid search só sobra `sem_efeito`, e a logística não ajusta. O scikit-learn avisa e descarta esse candidato.
