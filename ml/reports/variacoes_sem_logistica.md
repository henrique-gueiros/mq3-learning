# Variações sem regressão logística

25/11/2026. A regressão logística saiu do pipeline porque a disciplina não a cobriu. Agora comparamos baseline, KNN, árvore e floresta. São 12 arquivos, com MQ-3, MQ-135 e DHT11; cada arquivo é testado por um modelo ajustado só com os outros 11, e o teste nunca é reamostrado. Tabelas completas em `variacoes_sem_logistica.csv` e `variacoes_sem_logistica_por_arquivo.csv`. Código em `src/por_arquivo.py`.

## Variantes do treino

- `grid`: o grid escolhe o peso da bebida (nenhum, 2x, 4x ou balanceado), junto com os outros hiperparâmetros.
- `sem_peso`: peso fixo em nenhum.
- `corte`: no máximo 300 tentativas `sem_efeito` por arquivo, espaçadas no tempo, depois o grid.
- `limiar`: o grid e, depois, o limiar de `P(sob_efeito)` escolhido no próprio treino (validação cruzada por arquivo). É o limiar de maior recall de bebida que mantém pelo menos 95% de acerto em `sem_efeito`.
- `sem_peso_limiar`: sem peso e com o limiar escolhido no treino.

## Resultado (acerto no arquivo de fora)

| Variante | Modelo | Recall bebida | Precisão bebida | Perfume | `clean_6` | `drink_1` | `drink_2` | Média por arquivo | Pior arquivo |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **sem_peso_limiar** | **floresta** | **0,933** | **1,000** | **1,00** | **1,00** | 0,79 | 0,92 | **0,975** | 0,79 (`drink_1`) |
| sem_peso | floresta | 0,886 | 0,884 | 1,00 | 0,90 | 0,67 | 0,82 | 0,949 | 0,67 |
| limiar | floresta | 0,974 | 0,938 | 0,17 | 1,00 | 0,96 | 0,92 | 0,920 | 0,17 (perfume) |
| grid | floresta | 0,905 | 0,834 | 0,17 | 0,90 | 0,75 | 0,82 | 0,886 | 0,17 |
| corte | floresta | 0,947 | 0,820 | 0,17 | 0,87 | 0,92 | 0,83 | 0,899 | 0,17 |
| grid | árvore | 0,853 | 0,826 | 0,87 | 0,85 | 0,63 | 0,70 | 0,921 | 0,63 |
| sem_peso_limiar | árvore | 0,696 | 0,987 | 0,87 | 1,00 | 0,63 | 0,00 | 0,869 | 0,00 |
| limiar | KNN | 0,873 | 0,822 | 0,79 | 0,85 | 0,79 | 0,70 | 0,922 | 0,70 |
| grid | KNN | 0,830 | 0,751 | 0,82 | 0,78 | 0,55 | 0,71 | 0,902 | 0,55 |

`clean_7` e os cinco arquivos de 14/11 ficam em 0,98–1,00 em todas as linhas. `drink_3` e `drink_4` ficam em 0,93–1,00, exceto onde a tabela completa mostra outra coisa.

## Por que essa combinação funciona

- **O peso da bebida é o que joga o perfume para `sob_efeito`.** Sempre que o grid pode escolher peso, ele escolhe um peso alto: a validação interna quase não tem perfume, então o grid não vê o custo. Por isso `grid`, `corte` e `limiar` erram o perfume.
- **Sem peso, a floresta separa bem o perfume**, mas fica conservadora com a bebida: o limiar de 0,5 deixa passar sopros mais fracos (`drink_1`, `drink_2`).
- **O limiar escolhido no treino devolve o recall sem o peso.** A floresta continua sem viés para a bebida; só o corte de decisão desce o suficiente para pegar os sopros fracos, mantendo 95% de acerto em `sem_efeito` no treino. O limiar fica entre 0,2 e 0,4 conforme o arquivo de fora.
- **A árvore única não aguenta o limiar.** As probabilidades dela são quase só 0 ou 1 (folhas puras), então o limiar vira tudo ou nada (`drink_2` = 0,00). Na floresta, as probabilidades são médias de 100 árvores e variam aos poucos.

## Limites

- Um único arquivo de perfume, um participante, dois dias: é a melhor configuração **nestes dados**, não um desempenho garantido.
- O limiar exige que a produção use `predict_proba` e esse corte, e não o `predict` padrão. Hoje `train_final_model` e o servidor ao vivo usam o `predict`.
