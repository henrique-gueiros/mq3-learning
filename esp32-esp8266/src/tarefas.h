// As quatro tarefas do FreeRTOS. Cada uma recebe um ponteiro para Filas
// (include/filas.h) como parametro.
#pragma once

void tarefaSensores(void *parametro);       // le os sensores a cada 1 s
void tarefaArmazenamento(void *parametro);  // CSV no LittleFS + serial
void tarefaRede(void *parametro);           // Wi-Fi, MQTT e pendentes
void tarefaBotao(void *parametro);          // marca sopros e fim de rodada
