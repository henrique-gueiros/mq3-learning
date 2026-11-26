# Variações de treino: balanceamento e features

Gerado em 25/11/2026 por `python -m src.por_arquivo` (de `ml/`, depois do `prepare`), com MQ-3, MQ-135 e DHT11, 12 arquivos e 12.520 tentativas. Tabelas completas em `variacoes.csv` e `variacoes_por_arquivo.csv`.

## Como foi medido

- **Arquivo de fora**: cada um dos 12 arquivos é testado por um modelo ajustado só com os outros 11. O grid search escolhe os hiperparâmetros dentro desses 11, com `GroupKFold` por arquivo. O arquivo testado e as cópias dele nunca entram no ajuste.
- **O teste nunca é reamostrado.** Cada arquivo entra inteiro, com a proporção real de classes. Só o treino muda entre as variações.
- **Balanceamento do treino:**
  - `peso`: `class_weight="balanced"`, o padrão do pipeline;
  - `sem_peso`: sem peso por classe;
  - `corte`: no máximo 300 tentativas `sem_efeito` por arquivo, espaçadas do começo ao fim, mais o peso.
- **Features:**
  - `todas`: níveis e variações;
  - `variacao`: sem os níveis absolutos `*_before` e `*_peak`.
- **Critério de escolha:** a média do acerto por arquivo (cada arquivo pesa igual) e o pior arquivo. O F1 que junta tudo é dominado pelas 7.724 tentativas de `clean_5`.

## Acerto por arquivo de fora (features `todas`)

| Balanceamento | Modelo | Perfume | `clean_6` | `drink_1` | `drink_2` | `drink_3` | `drink_4` | Média por arquivo | Pior | Recall sob efeito | Precisão sob efeito |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| peso | árvore | 0,17 | 0,85 | 1,00 | 1,00 | 0,99 | 1,00 | 0,918 | 0,17 | 0,998 | 0,813 |
| peso | floresta | 0,17 | 0,89 | 0,92 | 0,86 | 0,99 | 1,00 | 0,903 | 0,17 | 0,952 | 0,836 |
| peso | logística | 1,00 | 0,76 | 0,91 | 0,91 | 1,00 | 1,00 | 0,965 | 0,76 | 0,961 | 0,776 |
| **sem_peso** | **floresta** | **1,00** | **0,90** | 0,67 | 0,82 | 1,00 | 1,00 | 0,949 | 0,67 | 0,886 | **0,884** |
| sem_peso | árvore | 0,87 | 0,85 | 0,63 | 0,70 | 0,93 | 1,00 | 0,915 | 0,63 | 0,834 | 0,823 |
| sem_peso | logística | 1,00 | 0,86 | 0,79 | 0,87 | 1,00 | 1,00 | 0,959 | 0,79 | 0,923 | 0,846 |
| corte | árvore | 0,17 | 0,89 | 0,83 | 0,79 | 1,00 | 0,69 | 0,864 | 0,17 | 0,824 | 0,812 |
| corte | floresta | 0,17 | 0,90 | 0,75 | 0,87 | 0,99 | 1,00 | 0,890 | 0,17 | 0,914 | 0,837 |
| **corte** | **logística** | 1,00 | 0,85 | 0,83 | 0,92 | 1,00 | 1,00 | **0,967** | **0,83** | 0,944 | 0,847 |

`clean_7` e os cinco arquivos de 14/11 ficam em 1,00 em todas as linhas acima.

## O que os números dizem

1. **O peso por classe é o que faz as árvores errarem o perfume.** Com `class_weight="balanced"`, cada tentativa de bebida pesa cerca de 9 vezes mais que uma de ar parado. Um caso no meio do caminho, como o perfume (gás alto, umidade parecida), cai do lado da bebida. Sem o peso, a floresta acerta 100/100 do perfume e erra menos no `clean_6` (0,90). O custo é o recall de bebida, que cai de 0,95 para 0,89, sobretudo em `drink_1` e `drink_2`.
2. **Cortar o ambiente por arquivo não resolve o perfume nas árvores** (continua 0,17), porque o corte vem junto com o peso. Na logística, o corte dá a melhor média por arquivo (0,967) e o melhor pior caso (0,83).
3. **Só as features de variação pioram tudo.** A bebida cai para 0,09–0,88 por arquivo. Os níveis absolutos (o MQ-3 de antes e de pico) carregam boa parte do sinal da bebida nesta coleta. A hipótese de que tirar os níveis ajudaria no perfume **não se confirmou**.
4. **Deixar um dia de fora não serve com estes dados.** Todos os arquivos de bebida são de 12/11. Quando 12/11 fica de fora, o treino não tem nenhuma bebida e não dá para ajustar. Sobra só o teste de 14/11, que é todo `sem_efeito` (100% de acerto, sem informação sobre bebida). As linhas estão em `variacoes.csv` só para registro.

## Limites

- Há um único arquivo de perfume. Quando ele é testado, o treino não tem perfume, então o "1,00" ou o "0,17" vale para esse arquivo e esse dia.
- Um participante (`equipe`), dois dias, e as quatro bebidas no mesmo dia: os números são de protótipo.
- A diferença entre as variações nos arquivos de bebida (por exemplo, 0,67 contra 0,92 em `drink_1`) mostra que o resultado varia muito de um arquivo para outro. Mais coleta é o que reduz essa incerteza.
