// tarefaBotao: o botao BOOT marca os sopros, como o Enter e o "f" da ponte.
//
//   aperto curto  -> sopro_inicio; o proximo aperto curto -> sopro_fim
//   segurar 2 s   -> rodada_fim (fecha um sopro aberto antes) e abre
//                    uma rodada nova, com CSV e rodada_id novos
//
// A interrupcao so libera um semaforo (rapido, sem Serial nem fila
// grande). Quem decide o que o aperto significa e esta tarefa, que
// tambem filtra o repique (bounce) do contato.
#include <Arduino.h>

#include "config.h"
#include "filas.h"
#include "log_serial.h"
#include "tarefas.h"

namespace {

void IRAM_ATTR aoApertarBotao(void *argumento) {
  SemaphoreHandle_t semaforo = static_cast<SemaphoreHandle_t>(argumento);
  BaseType_t acordouTarefaMaisImportante = pdFALSE;
  xSemaphoreGiveFromISR(semaforo, &acordouTarefaMaisImportante);
  if (acordouTarefaMaisImportante == pdTRUE) {
    portYIELD_FROM_ISR();
  }
}

bool apertado() { return digitalRead(PINO_BOTAO) == LOW; }

void enviarEvento(Filas *filas, TipoEvento evento, uint32_t tMs) {
  Registro registro = {};
  registro.tipo = TipoRegistro::EVENTO;
  registro.evento = evento;
  registro.tMs = tMs;
  if (xQueueSend(filas->registros, &registro, pdMS_TO_TICKS(500)) != pdTRUE) {
    logf("Fila de registros cheia: evento %s perdido", nomeEvento(evento));
  }
}

}  // namespace

void tarefaBotao(void *parametro) {
  Filas *filas = static_cast<Filas *>(parametro);
  pinMode(PINO_BOTAO, INPUT_PULLUP);
  attachInterruptArg(digitalPinToInterrupt(PINO_BOTAO), aoApertarBotao, filas->botao, FALLING);

  bool soproAberto = false;  // so esta tarefa le e escreve

  for (;;) {
    xSemaphoreTake(filas->botao, portMAX_DELAY);
    uint32_t inicioAperto = millis();
    vTaskDelay(pdMS_TO_TICKS(DEBOUNCE_BOTAO_MS));
    if (!apertado()) {
      continue;  // ruido: o pino voltou antes do fim do debounce
    }

    while (apertado() && millis() - inicioAperto < APERTO_LONGO_MS) {
      vTaskDelay(pdMS_TO_TICKS(20));
    }
    bool longo = apertado();

    if (longo) {
      uint32_t agora = millis();
      if (soproAberto) {
        enviarEvento(filas, TipoEvento::SOPRO_FIM, agora);
        soproAberto = false;
      }
      enviarEvento(filas, TipoEvento::RODADA_FIM, agora);
      logf("Botao: rodada encerrada; abrindo outra");
    } else if (soproAberto) {
      enviarEvento(filas, TipoEvento::SOPRO_FIM, inicioAperto);
      soproAberto = false;
    } else {
      enviarEvento(filas, TipoEvento::SOPRO_INICIO, inicioAperto);
      soproAberto = true;
    }

    // Espera soltar e descarta as interrupcoes do repique.
    while (apertado()) {
      vTaskDelay(pdMS_TO_TICKS(20));
    }
    vTaskDelay(pdMS_TO_TICKS(DEBOUNCE_BOTAO_MS));
    xSemaphoreTake(filas->botao, 0);
  }
}
