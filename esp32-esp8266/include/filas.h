// O que as tarefas trocam entre si. Sensores e rede so se falam por esta
// fila; nao ha variavel global compartilhada.
//
//   tarefaSensores ─ leituras (fila) ─> tarefaRede ─> MQTT
#pragma once

#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

#include "protocolo.h"

// Handles criados no setup() e passados para cada tarefa como parametro.
struct Filas {
  QueueHandle_t leituras;
};
