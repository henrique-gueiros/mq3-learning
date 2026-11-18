# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

É só um protótipo acadêmico, confirmado pela equipe em 17/11/2026. Quem usa a tela é a equipe do projeto e quem avalia (checkpoint, Mostra TechDesign). O trabalho deles é ver a coleta ao vivo e a análise das sessões.

O motorista no carro é o cenário que o protótipo representa, não um produto à parte.

## Product Purpose

Protótipo acadêmico de detector de álcool para carro, com a placa (MQ-3, MQ-135 e DHT11) e machine learning. A tela mostra as leituras que chegam e o que as coletas já gravadas dizem.

Sucesso: quem avalia entende, na tela, se a sessão foi de quem bebeu ou de quem não bebeu, nas condições do experimento, e vê um alerta quando há detecção.

## Positioning

A tela junta a coleta ao vivo e a análise das sessões da própria equipe, e avisa quando detecta um sopro. É o protótipo das duas disciplinas, não um detector para vender ou instalar num carro.

## Operating Context

A placa (ou a ponte serial, ou o simulador) publica no MQTT. A tela no navegador mostra o ao vivo por WebSocket e a análise pela API. A demonstração acontece com o Compose de pé, em geral num notebook, para a equipe e para a banca.

## Capabilities and Constraints

Confirmado pela equipe em 17/11/2026:

- A tela não mostra mg/L. Mostra três leituras: o PPM do MQ-3, o MQ-135 e a umidade.
- O treino do modelo usa só os dados que a equipe coletou.
- O PPM calculado pelo firmware pode aparecer na tela. Quem decide se a pessoa bebeu, no machine learning que ainda vai ser implementado, é o conjunto das três variáveis: PPM, MQ-135 e umidade.
- Quando há uma detecção, a tela mostra o resultado e dá um alerta. Bloqueio do carro não foi pedido.

A forma exata do alerta além do aviso visível na tela (som ou outro) não foi detalhada.

O detector que a tela usa hoje é uma heurística provisória, não esse modelo. O modelo de machine learning ainda não existe.

## Brand Commitments

O nome é Sopro Seguro. Os textos da tela ficam em português.

## Evidence on Hand

Há coleta real da equipe (sessões importadas em 17/11/2026, ainda sem sopro marcado nos arquivos). Não inventar depoimento, cliente, preço nem laudo.

## Product Principles

- É um protótipo acadêmico. A tela existe para a disciplina, não para ir para um carro de verdade.
- A tela mostra a medição e avisa. Não finge um resultado que a coleta não sustenta.
- Quem avalia precisa entender o resultado sem ler o código.
- Detecção vem com alerta na tela. Bloquear o carro não faz parte do que foi decidido.
- A decisão de ter bebido, quando o modelo existir, sai das três leituras juntas: PPM, MQ-135 e umidade. Nenhuma delas sozinha é o laudo.

## Accessibility & Inclusion

Quem avalia olha a tela de passagem. O resultado e o alerta têm de ser legíveis sem ficar estudando a página.
