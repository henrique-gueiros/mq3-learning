// As duas tarefas do FreeRTOS. Cada uma recebe um ponteiro para Filas
// (include/filas.h) como parametro.
#pragma once

void tarefaSensores(void *parametro);  // le os sensores a cada 1 s
void tarefaRede(void *parametro);      // Wi-Fi, MQTT, rodada e pendentes
