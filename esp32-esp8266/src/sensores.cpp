// tarefaSensores: le MQ-3, MQ-135 e DHT11 a cada INTERVALO_LEITURA_MS e
// manda cada Leitura para a fila de registros.
//
// vTaskDelayUntil (e nao vTaskDelay) mantem o periodo de 1 s mesmo que a
// leitura demore: ele acorda a tarefa em instantes fixos, contados a
// partir da ultima vez, em vez de "1 s depois de terminar".
#include <Arduino.h>
#include <DHT.h>
#include <math.h>

#include "config.h"
#include "filas.h"
#include "log_serial.h"
#include "tarefas.h"

namespace {

struct ArLimpo {
  int contagem;      // media do ADC na partida (referencia do LED)
  float tensaoMv;    // media em mV (referencia do ppm)
};

// A partida e tratada como ar limpo: 10 leituras do MQ-3 em ~0,4 s.
ArLimpo medirArLimpo() {
  vTaskDelay(pdMS_TO_TICKS(300));
  long soma = 0;
  long somaMv = 0;
  for (int i = 0; i < 10; i++) {
    soma += analogRead(PINO_MQ3);
    somaMv += analogReadMilliVolts(PINO_MQ3);
    vTaskDelay(pdMS_TO_TICKS(40));
  }
  return ArLimpo{static_cast<int>(soma / 10), somaMv / 10.0f};
}

}  // namespace

void tarefaSensores(void *parametro) {
  Filas *filas = static_cast<Filas *>(parametro);

  // O objeto do DHT so existe dentro desta tarefa.
  DHT dht(PINO_DHT, DHT11);
  dht.begin();
  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, LOW);

  const ArLimpo arLimpo = medirArLimpo();
  logf("Ar limpo na partida: %d (%.1f mV)", arLimpo.contagem, arLimpo.tensaoMv);

  float temperatura = NAN;
  float umidade = NAN;
  uint32_t ultimoDhtMs = millis();
  TickType_t ultimoAcordar = xTaskGetTickCount();

  for (;;) {
    vTaskDelayUntil(&ultimoAcordar, pdMS_TO_TICKS(INTERVALO_LEITURA_MS));
    uint32_t agora = millis();

    if (agora - ultimoDhtMs >= INTERVALO_DHT_MS) {
      ultimoDhtMs = agora;
      float novaTemperatura = dht.readTemperature();
      float novaUmidade = dht.readHumidity();
      if (!isnan(novaTemperatura) && !isnan(novaUmidade)) {
        temperatura = novaTemperatura;
        umidade = novaUmidade;
      }
    }

    Registro registro = {};
    registro.tipo = TipoRegistro::LEITURA;
    Leitura &l = registro.leitura;
    l.tMs = agora;
    l.mq3 = analogRead(PINO_MQ3);
    l.tensaoAtualMv = analogReadMilliVolts(PINO_MQ3);
    l.tensaoReferenciaMv = arLimpo.tensaoMv;
    l.ppm = estimarPpm(l.tensaoAtualMv, l.tensaoReferenciaMv, l.rs, l.rsRsAr);
    l.mq135 = analogRead(PINO_MQ135);
    l.mq135Mv = analogReadMilliVolts(PINO_MQ135);
    l.temperatura = temperatura;
    l.umidade = umidade;
    l.alcool = l.mq3 > arLimpo.contagem + MARGEM_ALCOOL;

    digitalWrite(PINO_LED, l.alcool ? HIGH : LOW);

    // Espera ate 100 ms por espaco; a fila cheia indica armazenamento travado.
    if (xQueueSend(filas->registros, &registro, pdMS_TO_TICKS(100)) != pdTRUE) {
      logf("Fila de registros cheia: leitura de %lu ms perdida", static_cast<unsigned long>(agora));
    }
  }
}
