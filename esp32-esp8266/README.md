# Firmware ESP32 — Sopro Seguro

Firmware PlatformIO (Arduino + FreeRTOS) do detector de álcool, no modo ao vivo:
lê o MQ-3, o MQ-135 e o DHT11 a cada 1 s e publica no MQTT, no mesmo contrato da
coleta. Não grava CSV e não lê botão. A coleta rotulada continua nos CSVs que a
equipe já tem (e na ponte, quando o firmware antigo escrevia `CSV_LINHA`). A parte
de machine learning fica em `ml/`.

Placa: `esp32dev`. Plataforma `espressif32@7.0.1` (core arduino-esp32 **2.0.17**).

## Tarefas (FreeRTOS)

| Tarefa | Arquivo | Núcleo / prio. | O que faz |
| --- | --- | --- | --- |
| `tarefaSensores` | `src/sensores.cpp` | 1 / 2 | `vTaskDelayUntil` de 1 s; lê MQ-3, MQ-135, DHT11; calcula ppm; acende o LED; manda uma `Leitura` para a fila |
| `tarefaRede` | `src/rede.cpp` | 0 / 1 | Abre a rodada (UUID v4, `arquivo_sessao` `ao_vivo`), numera a amostra, Wi-Fi, MQTT (last will), fila de pendentes (120), NTP |

```
tarefaSensores ─ fila "leituras" ─> tarefaRede ─> MQTT
```

As tarefas só se falam pela fila (`include/filas.h`). A lista de pendentes é privada
da `tarefaRede`. A serial tem um mutex (`src/log_serial.cpp`) para o log não sair misturado.

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
   com os valores de exemplo e não conecta em rede nenhuma.
2. Compilar e gravar:
   ```bash
   pio run
   pio run -t upload
   pio device monitor
   ```
3. Sopro: a placa não tem botão e não publica `eventos`. Quem marca o sopro é a ponte
   (Enter / `f`) quando a coleta passa pela USB, ou o simulador. Neste firmware a placa
   só publica `rodada`, `leituras` e `status`.

## Como testar

Testes do protocolo no PC (sem placa): `pio test -e native` (14 testes: linha do CSV,
JSON de cada tópico, UUID, ppm, buffer curto).

Com a placa e o broker no ar:

```bash
mosquitto_sub -t 'mq3/#' -v
```

Esperado, na ordem: `mq3/<placa>/status {"estado":"online"}`, `mq3/<placa>/rodada {...}`
(retida, `arquivo_sessao` `ao_vivo`) e uma `mq3/<placa>/leituras` por segundo.
Não há `eventos` desta placa. Desligar a placa deve publicar
`{"estado":"offline"}` (last will). Para testar a reconexão, derrube o broker por 1 min e
suba de novo: as leituras do intervalo chegam em seguida (até 120; as mais antigas
são descartadas e o aviso aparece na serial).

## Contrato MQTT (`applications/coleta/mensagens.py`)

| Tópico | Retida | Mensagem |
| --- | --- | --- |
| `mq3/<placa>/rodada` | sim | `rodada_id` (UUID v4 gerado na placa), `placa`, `caso: null`, `participante: null`, `inicio` (ISO em UTC se o NTP já acertou o relógio, senão `null`), `arquivo_sessao: "ao_vivo"`, `origem: "placa"` |
| `mq3/<placa>/leituras` | não | `rodada_id`, `amostra`, `t_ms`, `mq3_raw`, `ppm`, `mq135_raw`, `mq135_mv`, `temperature_c`, `humidity_pct`, `alcool` (`null` quando o DHT11 não leu) |
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

## Decisões e limites

- **Sem CSV e sem botão.** A placa não grava LittleFS e não publica `eventos`. Uma leitura
  que a fila de pendentes descarta (broker fora por mais de ~2 min) se perde. O sopro, para
  o modelo ao vivo, precisa chegar por outro publicador (`sopro_inicio` / `sopro_fim` no
  contrato); este firmware não o envia.
- **QoS 0 nas publicações.** O `PubSubClient` só publica com QoS 0 (sem confirmação do
  broker), embora o contrato peça QoS 1. O last will vai com QoS 1. Para QoS 1 de verdade,
  trocar a biblioteca por `256dpi/MQTT` (mudança só em `src/rede.cpp`).
- **Fila de pendentes limitada** (`MAX_PENDENTES_REDE`, 120 mensagens, ~2 min de leituras).
  Cheia, descarta a leitura mais antiga; a mensagem `rodada` nunca é descartada.
- **Wi-Fi:** `setAutoReconnect` e, se ficar 30 s sem conexão, recomeça com `WiFi.begin`.
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
| Pilhas das tarefas (`PILHA_*` em `include/config.h`) | dimensionadas sem medição; conferir com `uxTaskGetStackHighWaterMark` |
| IPv6 | **não testado** (hipótese acima) |
| Ingestão no Postgres com `origem = 'placa'` | depende da migração acima |
