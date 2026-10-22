#include <Arduino.h>
#include <math.h>
#include <DHT.h>

// Detector de alcool: modulo MQ-3 na ESP32.
// No Wokwi a peca disponivel e o sensor de gas (mesmos pinos do MQ-3:
// VCC, GND, AOUT e DOUT). O LED acende quando a leitura sobe em relacao
// ao ar limpo medido na partida.
//
// O ppm usa a curva do datasheet Hanwei. Ro e a resistencia em 0,4 mg/L
// de alcool, e nesse ponto o datasheet indica cerca de 200 ppm. No ar
// limpo, Rs/Ro fica em torno de 60. A partida e tratada como ar limpo
// para achar Ro. A tensao do circuito de teste do datasheet e 5 V; o
// resistor de carga se cancela na razao Rs/Ro. O ADC da ESP32 (11 dB)
// so mede ate cerca de 3,1 V, entao uma saida analogica alimentada em
// 5 V satura antes do fim da escala do sensor.

const int PINO_SENSOR = 34;
const int PINO_LED = 2;
// DHT11: VCC no 3V3, DATA no GPIO 4, GND no GND.
// No sensor de 4 pinos a ordem e VCC, DATA, NC, GND; o NC fica solto.
// Sensor solto precisa de 10 k entre DATA e 3V3. Modulo de 3 pinos ja tem.
const int PINO_DHT = 4;
const unsigned long INTERVALO_DHT_MS = 2000;
const int MARGEM = 80;

const float TENSAO_CIRCUITO_MV = 5000.0f;
const float RAZAO_AR_LIMPO = 60.0f;
const float CURVA_A = 0.3934f;
const float CURVA_B = -1.504f;
const float PPM_POR_MG_L = 200.0f / 0.4f;

int referencia = 0;
float tensaoArLimpoMv = 0.0f;
float temperaturaC = NAN;
float umidadePct = NAN;
unsigned long ultimaLeituraDhtMs = 0;

DHT dht(PINO_DHT, DHT11);

float estimarPpm(float tensaoMv, float tensaoReferenciaMv) {
  if (tensaoMv <= 0.0f || tensaoReferenciaMv <= 0.0f ||
      tensaoMv >= TENSAO_CIRCUITO_MV || tensaoReferenciaMv >= TENSAO_CIRCUITO_MV) {
    return 0.0f;
  }

  float rs = (TENSAO_CIRCUITO_MV / tensaoMv) - 1.0f;
  float rsAr = (TENSAO_CIRCUITO_MV / tensaoReferenciaMv) - 1.0f;
  if (rs <= 0.0f || rsAr <= 0.0f) {
    return 0.0f;
  }

  float razao = RAZAO_AR_LIMPO * (rs / rsAr);
  float mgPorL = CURVA_A * powf(razao, CURVA_B);
  if (isnan(mgPorL) || isinf(mgPorL) || mgPorL < 0.0f) {
    return 0.0f;
  }
  return mgPorL * PPM_POR_MG_L;
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, LOW);

  delay(300);
  long soma = 0;
  long somaMv = 0;
  for (int i = 0; i < 10; i++) {
    soma += analogRead(PINO_SENSOR);
    somaMv += analogReadMilliVolts(PINO_SENSOR);
    delay(40);
  }
  referencia = soma / 10;
  tensaoArLimpoMv = somaMv / 10.0f;
}

void loop() {
  unsigned long agora = millis();
  if (agora - ultimaLeituraDhtMs >= INTERVALO_DHT_MS) {
    ultimaLeituraDhtMs = agora;
    float novaTemperatura = dht.readTemperature();
    float novaUmidade = dht.readHumidity();
    if (!isnan(novaTemperatura) && !isnan(novaUmidade)) {
      temperaturaC = novaTemperatura;
      umidadePct = novaUmidade;
    }
  }

  int leitura = analogRead(PINO_SENSOR);
  float ppm = estimarPpm(analogReadMilliVolts(PINO_SENSOR), tensaoArLimpoMv);
  bool alcool = leitura > (referencia + MARGEM);

  digitalWrite(PINO_LED, alcool ? HIGH : LOW);

  Serial.print("Leitura: ");
  Serial.print(leitura);
  Serial.print("  ppm: ");
  Serial.print(ppm, 1);
  Serial.print("  temp: ");
  if (isnan(temperaturaC)) {
    Serial.print("--");
  } else {
    Serial.print(temperaturaC, 1);
    Serial.print(" C");
  }
  Serial.print("  umidade: ");
  if (isnan(umidadePct)) {
    Serial.print("--");
  } else {
    Serial.print(umidadePct, 1);
    Serial.print(" %");
  }
  if (alcool) {
    Serial.println("  ALCOOL - LED aceso");
  } else {
    Serial.println("  ar limpo - LED apagado");
  }

  delay(400);
}
