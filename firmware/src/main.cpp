#include <Arduino.h>

// Detector de alcool: modulo MQ-3 na ESP32.
// No Wokwi a peca disponivel e o sensor de gas (mesmos pinos do MQ-3:
// VCC, GND, AOUT e DOUT). O LED acende quando a leitura sobe em relacao
// ao ar limpo medido na partida.

const int PINO_SENSOR = 34;
const int PINO_LED = 2;
const int MARGEM = 80;

int referencia = 0;

void setup() {
  Serial.begin(115200);
  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, LOW);

  delay(300);
  long soma = 0;
  for (int i = 0; i < 10; i++) {
    soma += analogRead(PINO_SENSOR);
    delay(40);
  }
  referencia = soma / 10;

}

void loop() {
  int leitura = analogRead(PINO_SENSOR);
  bool alcool = leitura > (referencia + MARGEM);

  digitalWrite(PINO_LED, alcool ? HIGH : LOW);

  Serial.print("Leitura: ");
  Serial.print(leitura);
  if (alcool) {
    Serial.println("  ALCOOL - LED aceso");
  } else {
    Serial.println("  ar limpo - LED apagado");
  }

  delay(400);
}
