// Sopro Seguro: firmware da ESP32 (MQ-3, MQ-135 e DHT11), so ao vivo.
//
// O setup() cria a fila e as tarefas do FreeRTOS:
//
//   sensores.cpp  tarefaSensores  le os sensores a cada 1 s
//   rede.cpp      tarefaRede      Wi-Fi + MQTT (rodada na partida, leituras)
//
// Nao grava CSV e nao le botao. O sopro, quando houver, e marcado fora da
// placa. Como configurar e testar: README.md desta pasta.
#include <Arduino.h>

#include "config.h"
#include "filas.h"
#include "log_serial.h"
#include "tarefas.h"

static Filas filas;  // vive para sempre: as tarefas guardam o ponteiro

static void criarTarefa(TaskFunction_t funcao, const char *nome, uint32_t pilha, UBaseType_t prioridade,
                        BaseType_t nucleo) {
  if (xTaskCreatePinnedToCore(funcao, nome, pilha, &filas, prioridade, nullptr, nucleo) != pdPASS) {
    logf("ERRO: nao foi possivel criar a tarefa %s", nome);
  }
}

void setup() {
  iniciarLogSerial();

  filas.leituras = xQueueCreate(TAMANHO_FILA_LEITURAS, sizeof(Leitura));
  if (filas.leituras == nullptr) {
    logf("ERRO: sem memoria para a fila; reiniciando");
    delay(1000);
    ESP.restart();
  }

  // Nucleo 1 (o do loop() do Arduino) para a leitura periodica; nucleo 0
  // (o do Wi-Fi) para a rede. Prioridade maior = mais urgente: a leitura
  // nao pode atrasar por causa da rede.
  criarTarefa(tarefaSensores, "sensores", PILHA_SENSORES, 2, 1);
  criarTarefa(tarefaRede, "rede", PILHA_REDE, 1, 0);
}

// Tudo acontece nas tarefas; o loop() do Arduino so cede o processador.
void loop() { vTaskDelay(portMAX_DELAY); }
