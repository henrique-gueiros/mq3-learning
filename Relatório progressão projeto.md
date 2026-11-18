Relatório datado de progressão e análise

Material nesse momento: 2 Protoboards, ESP32, 2 MQ3(sensor de álcool) e DHT11  
15/10 \- Iniciamos a montagem do circuito, analisando a disposição dos sensores para projetar o rascunho inicial do projeto.

20/10 \- Começamos os testes. Com um copo, com um papel encharcado de álcool em gel, testamos a sensibilidade do sensor de álcool. Inicialmente, apontamos que as ppm (Partes por milhão) de álcool no ar aumentavam drasticamente ao aproximar o copo do MQ3, no entanto, a temperatura e umidade mantinham-se constantes. Verificamos também que o DHT11 sofria variação súbita de umidade quando sopramos nele e a temperatura sofria leve variação. Essa conclusão, além de verificar o funcionamento do sensor, nos levou a tratar o caso de álcool em gel próximo do sensor, pois as ppm subiriam, no entanto, com o DHT11 quase inalterado, poderia se afirmar, com respaldo do teste inicial que essa variação do MQ3 não vinha do hálito de alguém, portanto, apontando negativo para embriaguez (Nesse caso de teste em ambiente controlado)

22/10 \- Com outra bateria de testes, iniciamos o que seria o nosso modelo de análise default. Delimitando 60 segundos de leitura com 1 leitura por segundo, fazíamos várias alterações de ambiente no sensor, soprando, aproximando o copo com álcool e afastando para analisar as variações de leitura. 

27/10 \- Ao seguir com os testes, percebemos uma necessidade de expandir a paramentação sensorial comprando um MQ135 (Sensor de uma composição de gases maior, entre eles CO2 e Álcool) para aumentar a precisão e não amparar a análise de verificação se o gás vinha do hálito apenas na humidade, percebendo o aumento da concentração de CO2 e álcool no ar.

Material nesse momento: 2 Protoboards, ESP32, 2 MQ3(sensor de álcool), DHT11 e MQ135

29/10 \- Com o aparato completo, iniciamos testes de comparação entre ambiente fechado e ambiente aberto. Não percebemos uma alteração grande nas leituras além da alteração de temperatura (subiu consideravelmente, como esperado).

 **O comportamento esperado nesse momento do projeto era:** 

- Álcool sobe, temperatura, umidade e MQ135 se mantém constantes (NÃO ÁLCOOL)  
- Álcool e MQ135 sobem, umidade e temperatura constantes (NÃO ÁLCOOL)  
- Álcool, MQ135 e umidade sobem e temperatura constante (MUITO PROVAVELMENTE ÁLCOOL)

03/11 \- Iniciamos o armazenamento e a rotulação dos dados para treinamento do modelo. A rotulação foi baseada na criação de arquivos CSV, seguindo o modelo de captação estabelecido no dia 22/10. Desta vez, porém, mantivemos constante o tipo de dado captado, por exemplo, mantendo constante a exposição ao álcool, sem variações de umidade, para criar uma média das leituras e permitir que o modelo não classifique automaticamente uma alta concentração de álcool no ar como embriaguez, mas tenha uma base de dados para reconhecer o padrão desse caso específico.

05/11 \- (Dia de teste prático) Pela manhã alinhamos o MQTT para adiantar a configuração de funcionamento do software do projeto, já nos antecipando para um teste prático mais próximo da realidade pela noite. Quando iniciamos os testes, percebemos que o sensor estava tendo uma sensibilidade abaixo do esperado, necessitando uma aproximação maior ou esforço de sopro à distância para que as leituras de álcool fossem atualizadas. Depois de um tempo, fizemos a alternância de sopro para exposição contínua de álcool e notamos um grande aumento nas leituras do MQ135 e do MQ3.  
Seguindo a análise, chegamos a conclusão que o melhor modelo para análise e classificação seria uma árvore de decisão com o primeiro nó sendo o de verificação de umidade, pois em todo o caso em que a fonte do álcool é o hálito, a umidade sobe subitamente.

10/11 \- Depois dos testes práticos, tivemos a impressão de que o sensor estava recebendo uma voltagem menor do que o esperado, tornando a leitura do sensor mais dificultada e menos confiável. Pomos em teste essa hipótese experimentando um multímetro no nosso circuito. Aferimos que a voltagem recebida pelo sensor estava girando em torno de 3,8 na protoboard. No entanto, conseguimos resolver o problema de contato e concentramos nosso circuito em apenas uma protoboard menor, agora registrando aproximadamente 4,8 na voltagem. As leituras de álcool foram completamente diferentes e fora da nossa escala anterior, que devido aos testes mais recentes, percebemos estar desregulada. Nos testes com a escala anterior, as leituras acentuadas de álcool giravam entre 0,9 e 2\. Depois do ajuste, as leituras atingiram até 12 (testando com álcool 70). Sendo assim, percebemos a necessidade de uma nova bateria de testes e análise de casos, assim como nova alimentação do nosso dataset.

Material nesse momento: Protoboard, ESP32, 2 MQ3(sensor de álcool), DHT11 e MQ135

12/11 \- (Dia de teste prático) Não tivemos aula nesse dia, mas estávamos com o circuito conosco, portanto, decidimos realizar outra bateria de testes para já ajustar nosso dataset, seguindo as conclusões que tiramos na terça feira de que nosso sensor MQ3 estava mal adaptado. Nas leituras iniciais, percebemos que o consumo de álcool misturado com gelo, comparado com o consumo de álcool sem gelo, era menos expressivo nas leituras. Acreditamos que isso se dê por conta da concentração reduzida do álcool quando misturado com gelo, além de os indivíduos testados não estarem embriagados, mesmo que sob efeito de álcool. Para aumentar a exposição, alteramos a forma de teste. Estávamos soprando na direção do sensor, no entanto, percebemos que expirar com a boca aberta apresentava uma variação de leitura muito mais significativa, corroborando com a preparação do nosso banco de dados, cultivando dados bem estabelecidos e mais distintos entre os casos de teste. Percebemos também que ao borrifar perfume, o sensor de álcool não ultrapassou 0.8ppm, mesmo que borrifando o perfume muito próximo do sensor. O MQ135 reagiu variando as leituras entre 1200 e 1500, no ápice, no entanto, como pretendemos utilizar uma árvore de decisão como modelo, essas leituras tornam-se irrelevantes, pois o primeiro nó de decisão será a umidade.

**Atualizações no comportamento esperado do projeto:**

- Análise de variações semelhante à estabelecida anteriormente  
- Começamos a desconsiderar temperatura, visto que ela não apresentava variação clara entre leitura ambiente e leitura de hálito alcoolizado  
- Alteramos a escala de detecção de álcool para nos adaptarmos às novas leituras do sensor

