// Sopro Seguro: firmware da ESP32 (MQ-3, MQ-135 e DHT11).
//
// O setup() so cria as filas e as tarefas do FreeRTOS; o trabalho esta em
// cada arquivo de tarefa:
//
//   sensores.cpp       tarefaSensores       le os sensores a cada 1 s
//   armazenamento.cpp  tarefaArmazenamento  CSV no LittleFS + serial (CSV_LINHA)
//   rede.cpp           tarefaRede           Wi-Fi + MQTT, fila de pendentes
//   botao.cpp          tarefaBotao          sopro_inicio / sopro_fim / rodada_fim
//
// Como configurar e testar: README.md desta pasta.
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

  filas.registros = xQueueCreate(TAMANHO_FILA_REGISTROS, sizeof(Registro));
  filas.rede = xQueueCreate(TAMANHO_FILA_REDE, sizeof(MensagemRede));
  filas.botao = xSemaphoreCreateBinary();
  if (filas.registros == nullptr || filas.rede == nullptr || filas.botao == nullptr) {
    logf("ERRO: sem memoria para as filas; reiniciando");
    delay(1000);
    ESP.restart();
  }

  // Nucleo 1 (o do loop() do Arduino) para o que mede e grava; nucleo 0
  // (o do Wi-Fi) para a rede. Prioridade maior = mais urgente: a leitura
  // periodica nao pode atrasar por causa de CSV ou rede.
  criarTarefa(tarefaSensores, "sensores", PILHA_SENSORES, 3, 1);
  criarTarefa(tarefaBotao, "botao", PILHA_BOTAO, 3, 1);
  criarTarefa(tarefaArmazenamento, "armazenamento", PILHA_ARMAZENAMENTO, 2, 1);
  criarTarefa(tarefaRede, "rede", PILHA_REDE, 1, 0);
}

// Tudo acontece nas tarefas; o loop() do Arduino so cede o processador.
void loop() { vTaskDelay(portMAX_DELAY); }
