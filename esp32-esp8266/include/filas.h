// O que as tarefas trocam entre si. Cada tarefa so conversa com as outras
// por estas filas e pelo semaforo do botao; nao ha variavel global
// compartilhada.
//
//   tarefaSensores ─┐                         ┌─> CSV no LittleFS
//                   ├─ registros ─> tarefaArmazenamento ─┼─> serial (CSV_LINHA)
//   tarefaBotao ────┘   (fila)                └─ rede (fila) ─> tarefaRede ─> MQTT
//        ^
//        └─ semaforo, liberado pela interrupcao do botao
#pragma once

#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>

#include "protocolo.h"

enum class TipoEvento : uint8_t { SOPRO_INICIO, SOPRO_FIM, RODADA_FIM };

// Nome do evento no contrato MQTT (sopro_inicio, sopro_fim, rodada_fim).
inline const char *nomeEvento(TipoEvento evento) {
  switch (evento) {
    case TipoEvento::SOPRO_INICIO:
      return "sopro_inicio";
    case TipoEvento::SOPRO_FIM:
      return "sopro_fim";
    default:
      return "rodada_fim";
  }
}

// Sensores e botao -> armazenamento. Uma fila so para os dois manter a
// ordem: o evento fica entre as leituras em que aconteceu.
enum class TipoRegistro : uint8_t { LEITURA, EVENTO };
struct Registro {
  TipoRegistro tipo;
  Leitura leitura;     // quando tipo == LEITURA
  TipoEvento evento;   // quando tipo == EVENTO
  uint32_t tMs;        // instante do evento (millis)
};

// Armazenamento -> rede. A tarefa de rede monta o JSON na hora de publicar.
enum class TipoMensagem : uint8_t { RODADA, LEITURA, EVENTO };
struct MensagemRede {
  TipoMensagem tipo;
  char rodadaId[TAMANHO_UUID];
  Leitura leitura;       // LEITURA
  TipoEvento evento;     // EVENTO
  uint32_t tMs;          // EVENTO: instante; RODADA: millis da abertura
  char arquivo[24];      // RODADA: nome do CSV
};

// Handles criados no setup() e passados para cada tarefa como parametro.
struct Filas {
  QueueHandle_t registros;
  QueueHandle_t rede;
  SemaphoreHandle_t botao;
};
