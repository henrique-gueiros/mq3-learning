// Pinos, tempos e tamanhos do firmware. Os segredos (Wi-Fi e broker)
// ficam em segredos.h; veja segredos.exemplo.h.
#pragma once

#include <stddef.h>
#include <stdint.h>

#if __has_include("segredos.h")
#include "segredos.h"
#else
#warning "include/segredos.h nao existe: usando segredos.exemplo.h (sem rede de verdade)"
#include "segredos.exemplo.h"
#endif

// ---- Pinos ----------------------------------------------------------
// MQ-3: AOUT no GPIO 34. No Wokwi a peca e o sensor de gas (mesmos pinos).
const int PINO_MQ3 = 34;
// MQ-135: VCC no 5 V, AOUT no GPIO 35, DOUT solto. O ADC da ESP32 satura
// perto de 3,1 V, entao leituras altas ficam achatadas (vale para o MQ-3).
const int PINO_MQ135 = 35;
// DHT11: VCC no 3V3, DATA no GPIO 4. Sensor solto precisa de 10 k entre
// DATA e 3V3; o modulo de 3 pinos ja tem.
const int PINO_DHT = 4;
// LED da placa: acende quando o MQ-3 passa da referencia + MARGEM.
const int PINO_LED = 2;
// Botao BOOT da placa esp32dev (GPIO 0, ja tem pull-up). Depois que o
// firmware ligou ele e um botao comum. Segurar o BOOT durante o reset
// entra no modo de gravacao, como sempre.
const int PINO_BOTAO = 0;

// ---- Tempos ---------------------------------------------------------
const uint32_t INTERVALO_LEITURA_MS = 1000;
const uint32_t INTERVALO_DHT_MS = 2000;  // o DHT11 nao responde mais rapido que isso
const uint32_t DEBOUNCE_BOTAO_MS = 40;
const uint32_t APERTO_LONGO_MS = 2000;  // segurar 2 s encerra a rodada
const uint32_t ESPERA_WIFI_MS = 30000;   // sem Wi-Fi por 30 s: recomeca a conexao
const uint32_t ESPERA_MQTT_MS = 5000;    // intervalo entre tentativas no broker
const uint32_t TIMEOUT_TCP_MS = 5000;

// ---- Leitura --------------------------------------------------------
// Margem em contagens do ADC sobre a referencia de ar limpo para acender o
// LED e marcar "alcool". So indicacao local: nunca rotulo nem decisao.
const int MARGEM_ALCOOL = 80;

// ---- Armazenamento --------------------------------------------------
// Abaixo disto o LittleFS desta placa nao devolve "disco cheio": reinicia
// com IntegerDivideByZero ao alocar um bloco. A reserva fica livre
// apagando os CSVs mais antigos.
const size_t RESERVA_CSV_BYTES = 12 * 1024;

// ---- Filas e tarefas ------------------------------------------------
const size_t TAMANHO_FILA_REGISTROS = 10;  // sensores e botao -> armazenamento
const size_t TAMANHO_FILA_REDE = 10;       // armazenamento -> rede
// Leituras e eventos guardados enquanto o broker esta fora (~2 min de
// leituras). Cheio, a mensagem mais antiga e descartada.
const size_t MAX_PENDENTES_REDE = 120;
const size_t TAMANHO_JSON = 320;

const uint32_t PILHA_SENSORES = 4096;
const uint32_t PILHA_ARMAZENAMENTO = 6144;
const uint32_t PILHA_REDE = 8192;
const uint32_t PILHA_BOTAO = 3072;
