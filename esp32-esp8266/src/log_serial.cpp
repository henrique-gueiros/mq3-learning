#include "log_serial.h"

#include <Arduino.h>
#include <freertos/semphr.h>
#include <stdarg.h>

namespace {
SemaphoreHandle_t mutexSerial = nullptr;
}

void iniciarLogSerial() {
  Serial.begin(115200);
  mutexSerial = xSemaphoreCreateMutex();
}

void escreverLinhaSerial(const char *linha) {
  if (mutexSerial != nullptr) {
    xSemaphoreTake(mutexSerial, portMAX_DELAY);
  }
  Serial.println(linha);
  if (mutexSerial != nullptr) {
    xSemaphoreGive(mutexSerial);
  }
}

void logf(const char *formato, ...) {
  char linha[256];
  va_list args;
  va_start(args, formato);
  vsnprintf(linha, sizeof(linha), formato, args);
  va_end(args);
  escreverLinhaSerial(linha);
}
