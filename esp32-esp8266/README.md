# Firmware ESP32 — Sopro Seguro

Firmware PlatformIO (Arduino + FreeRTOS) do detector de álcool: lê o MQ-3, o MQ-135
e o DHT11 a cada 1 s, grava o CSV de sessão no LittleFS, escreve as linhas na serial
(para a ponte `applications/coleta/ponte.py`) e publica no MQTT, no mesmo contrato da
coleta. A parte de machine learning fica em `ml/`.

Placa: `esp32dev`. Plataforma `espressif32@7.0.1` (core arduino-esp32 **2.0.17**).

## Tarefas (FreeRTOS)

| Tarefa | Arquivo | Núcleo / prio. | O que faz |
| --- | --- | --- | --- |
| `tarefaSensores` | `src/sensores.cpp` | 1 / 3 | `vTaskDelayUntil` de 1 s; lê MQ-3, MQ-135, DHT11; calcula ppm; acende o LED; manda um `Registro` (leitura) para a fila |
| `tarefaBotao` | `src/botao.cpp` | 1 / 3 | Espera o semáforo que a interrupção do botão libera; filtra repique; decide o evento e manda um `Registro` (evento) |
| `tarefaArmazenamento` | `src/armazenamento.cpp` | 1 / 2 | Dona do CSV: numera a amostra, grava no LittleFS, escreve `CSV_LINHA,...` na serial e passa a mensagem para a rede. Abre a rodada (UUID v4, CSV novo) |
| `tarefaRede` | `src/rede.cpp` | 0 / 1 | Wi-Fi com reconexão, MQTT (last will), fila de pendentes limitada (120), NTP |

```
tarefaSensores ─┐                                ┌─ CSV (LittleFS)
                ├─ fila "registros" ─> tarefaArmazenamento ─┼─ serial: CSV_LINHA
tarefaBotao ────┘                                └─ fila "rede" ─> tarefaRede ─> MQTT
     ▲
     └── semáforo, liberado pela interrupção do botão
```

As tarefas só se falam pelas filas e pelo semáforo (`include/filas.h`). O estado do CSV
é privado da `tarefaArmazenamento` e a lista de pendentes é privada da `tarefaRede`:
não há variável global compartilhada. A serial tem um mutex (`src/log_serial.cpp`) para
que uma linha `CSV_LINHA` nunca saia misturada com outra mensagem.

O formato (CSV, JSON, UUID, ppm) fica em `lib/protocolo/` e não depende do Arduino:
é testado no PC.

## Como configurar

1. Segredos (Wi-Fi e broker):
   ```bash
   cd esp32-esp8266
   cp include/segredos.exemplo.h include/segredos.h   # o git ignora este arquivo
   ```
   Edite `WIFI_SSID`, `WIFI_SENHA`, `MQTT_HOST` (IPv4, IPv6 ou nome do PC que roda o
   Mosquitto do `docker-compose.yml`) e `PLACA`. Sem `segredos.h` o firmware compila
   com os valores de exemplo, não conecta em rede nenhuma e segue gravando CSV e serial.
2. Compilar e gravar:
   ```bash
   pio run
   pio run -t upload
   pio device monitor
   ```
3. Botão (o **BOOT** da placa, GPIO 0): aperto curto alterna `sopro_inicio` / `sopro_fim`;
   segurar 2 s envia `rodada_fim` e abre uma rodada nova (CSV e `rodada_id` novos).
   Os sopros marcados no botão são os mesmos que o Enter e o `f` da ponte marcam.

## Como testar

Testes do protocolo no PC (sem placa): `pio test -e native` (14 testes: linha do CSV,
JSON de cada tópico, UUID, ppm, buffer curto).

Com a placa e o broker no ar:

```bash
mosquitto_sub -t 'mq3/#' -v
```

Esperado, na ordem: `mq3/<placa>/status {"estado":"online"}`, `mq3/<placa>/rodada {...}`
(retida), uma `mq3/<placa>/leituras` por segundo e, ao apertar o botão,
`mq3/<placa>/eventos {"tipo":"sopro_inicio",...}`. Desligar a placa deve publicar
`{"estado":"offline"}` (last will). Para testar a reconexão, derrube o broker por 1 min e
suba de novo: as leituras do intervalo chegam em seguida (até 120; as mais antigas
são descartadas e o aviso aparece na serial).

## Contrato MQTT (`applications/coleta/mensagens.py`)

| Tópico | Retida | Mensagem |
| --- | --- | --- |
| `mq3/<placa>/rodada` | sim | `rodada_id` (UUID v4 gerado na placa), `placa`, `caso: null`, `participante: null`, `inicio` (ISO em UTC se o NTP já acertou o relógio, senão `null`), `arquivo_sessao` (nome do CSV), `origem: "placa"` |
| `mq3/<placa>/leituras` | não | `rodada_id`, `amostra`, `t_ms`, `mq3_raw`, `ppm`, `mq135_raw`, `mq135_mv`, `temperature_c`, `humidity_pct`, `alcool` (`null` quando o DHT11 não leu) |
| `mq3/<placa>/eventos` | não | `rodada_id`, `tipo` (`sopro_inicio`, `sopro_fim`, `rodada_fim`), `t_ms` |
| `mq3/<placa>/status` | sim | `{"estado":"online"}`; last will `{"estado":"offline"}` (QoS 1) |

### Pendências de integração

- **`origem = 'placa'` ainda não passa no banco.** O `CHECK` de `rodadas.origem` em
  `applications/db/01-schema.sql` só aceita `'ponte'`, `'importador'` e `'simulador'`: é
  preciso acrescentar `'placa'` (migração que fica com a sessão integradora). Até lá o
  ingestor rejeita a mensagem `rodada` da placa. `mensagens.py` também só lista
  `ponte` e `simulador` em `ORIGENS_MQTT`.
- `caso` e `participante` saem `null` por padrão: a placa não sabe quem sopra nem o que foi
  usado. Para rotular a coleta, defina `CASO_PADRAO` e `PARTICIPANTE_PADRAO` em
  `segredos.h` (vazio = `null`); vale para todas as rodadas até regravar o firmware.
  **Rodada que ficou `null` precisa de rótulo antes do DAG do Airflow**
  (`dataset_para_treino` usa o caso para o rótulo): atualize no banco, por exemplo
  `UPDATE rodadas SET caso = 'drink', participante = 'p01' WHERE id = '<rodada_id>';`
  (o `rodada_id` aparece na serial, em `Rodada <uuid>`, e na mensagem `rodada`).
  Cuidado: a placa republica a mensagem `rodada` ao reconectar, e o ingestor sobrescreve
  `caso` com o valor da mensagem; rotule depois que a rodada terminar.
- O `rodada_fim` da placa não leva `sha256` (a ponte leva o do CSV que ela gravou).
- Se a ponte serial e a placa publicarem ao mesmo tempo, use `PLACA` diferente de
  `placa01` (padrão da ponte), senão as duas gravam nos mesmos tópicos.

## Eventos do botão: serial e arquivo (não dependem do MQTT)

Cada evento (`sopro_inicio`, `sopro_fim`, `rodada_fim`) sai por três caminhos: MQTT, serial
e arquivo na placa. Na serial:

```
CSV_EVENTO,<arquivo>,<tipo>,<t_ms>
CSV_EVENTO,leituras_3.csv,sopro_inicio,41230
```

e no LittleFS, `/leituras_N.eventos.csv` ao lado de `/leituras_N.csv`, com cabeçalho
`tipo,t_ms`. O `t_ms` é o mesmo da coluna `t_ms` do CSV de leituras (ms desde a partida da
placa), então cada par `sopro_inicio` / `sopro_fim` vira uma linha do `attempts.csv`:
`blow_start_s` = (`t_ms` do início − `t_ms` da primeira leitura) / 1000, e `blow_end_s` o
mesmo com o fim; `session_file` é o `<arquivo>` e `condition` vem do caso da rodada. A
**ponte lê `CSV_EVENTO`** se o firmware emitir (mesmo papel do Enter/`f` no `t_ms` da
placa). Na coleta da equipe o sopro é marcado na ponte (Enter / `f`), sem usar o
botão BOOT; o suporte ao botão fica no firmware para quem quiser testar.

**Risco do QoS 0:** se o `sopro_fim` (ou o `sopro_inicio`) se perder no MQTT, o banco fica sem
a janela do sopro e o modelo ao vivo não roda para aquela tentativa. A serial e o arquivo
de eventos guardam o que o MQTT pode perder.

## Decisões e limites

- **QoS 0 nas publicações.** O `PubSubClient` só publica com QoS 0 (sem confirmação do
  broker), embora o contrato peça QoS 1. O last will vai com QoS 1. A perda é coberta
  pelo CSV na placa e pelo CSV da ponte; para QoS 1 de verdade, trocar a biblioteca por
  `256dpi/MQTT` (mudança só em `src/rede.cpp`).
- **Fila de pendentes limitada** (`MAX_PENDENTES_REDE`, 120 mensagens, ~2 min de leituras).
  Cheia, descarta a leitura mais antiga e, sem leituras, o evento mais antigo; a mensagem `rodada` nunca é descartada.
- **Wi-Fi:** `setAutoReconnect` e, se ficar 30 s sem conexão, recomeça com `WiFi.begin`.
- O CSV (13 colunas) e a linha `CSV_LINHA` são idênticos aos do firmware anterior; o
  filtro `monitor/filter_leituras.py` e a ponte continuam funcionando.
- O ppm continua vindo da curva do datasheet e o campo `alcool` (leitura acima da
  referência + 80) segue como indicação local: nem rótulo, nem feature, nem decisão.

### IPv6 (hipótese, não testado)

O core 2.0.17 tem IPv6 no lwIP e `WiFi.enableIpV6()`, que o firmware chama ao associar ao
Wi-Fi. Mas o `WiFiClient` desse core só abre socket IPv4, então o firmware usa um
cliente próprio (`src/cliente_tcp.cpp`, sockets do lwIP com `getaddrinfo`) que aceita
broker por endereço IPv6 (`MQTT_HOST "2804:abcd::10"`, detectado pelo `:`) ou por nome com
`MQTT_USAR_IPV6 1` (procura o registro AAAA). Isso **compila, mas não foi testado**: depende
de o roteador anunciar um prefixo IPv6 (SLAAC) para a placa ter endereço global; só o
endereço local de link (`fe80::`) não alcança o broker sem identificar a interface. O
log do Wi-Fi imprime só o IPv4; o IPv6 não é impresso.

## Estado de teste

| Item | Situação |
| --- | --- |
| `pio run` (compila para `esp32dev`) | testado |
| `pio test -e native` (protocolo no PC) | testado |
| Wi-Fi, MQTT, last will, reconexão, fila de pendentes | **não testado em hardware** |
| Botão (interrupção, repique, aperto longo) | **não testado em hardware** |
| Pilhas das tarefas (`PILHA_*` em `include/config.h`) | dimensionadas sem medição; conferir com `uxTaskGetStackHighWaterMark` |
| IPv6 | **não testado** (hipótese acima) |
| Ingestão no Postgres com `origem = 'placa'` | depende da migração acima |
