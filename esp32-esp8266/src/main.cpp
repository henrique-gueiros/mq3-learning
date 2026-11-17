#include <Arduino.h>
#include <math.h>
#include <DHT.h>
#include <LittleFS.h>

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
// MQ-135 (qualidade do ar): VCC no 5 V, GND no GND, AOUT no GPIO 35.
// DOUT fica solto. O aquecedor pede 5 V. O ADC satura perto de 3,1 V,
// como no MQ-3, se a saida analogica passar disso.
const int PINO_MQ135 = 35;
// DHT11: VCC no 3V3, DATA no GPIO 4, GND no GND.
// No sensor de 4 pinos a ordem e VCC, DATA, NC, GND; o NC fica solto.
// Sensor solto precisa de 10 k entre DATA e 3V3. Modulo de 3 pinos ja tem.
const int PINO_DHT = 4;
const unsigned long INTERVALO_DHT_MS = 2000;
const unsigned long INTERVALO_LEITURA_MS = 1000;
const int MARGEM = 80;
// Abaixo disto o LittleFS desta placa nao devolve "disco cheio":
// reinicia com IntegerDivideByZero ao alocar um bloco. A reserva
// fica livre apagando os CSVs mais antigos.
const size_t RESERVA_CSV_BYTES = 12 * 1024;

const float TENSAO_CIRCUITO_MV = 5000.0f;
const float RAZAO_AR_LIMPO = 60.0f;
const float CURVA_A = 0.3934f;
const float CURVA_B = -1.504f;
const float PPM_POR_MG_L = 200.0f / 0.4f;

struct Leitura {
  unsigned long tMs;
  int mq3;
  float ppm;
  float rs;
  float rsRsAr;
  int mq135;
  int mq135Mv;
  float temperatura;
  float umidade;
  bool alcool;
  float tensaoAtualMv;
  float tensaoReferenciaMv;
};

int referencia = 0;
float tensaoArLimpoMv = 0.0f;
float temperaturaC = NAN;
float umidadePct = NAN;
unsigned long ultimaLeituraDhtMs = 0;
unsigned long proximaAmostra = 1;
bool sistemaArquivosOk = false;
char nomeCsv[24] = "leituras_1.csv";
char arquivoCsv[28] = "/leituras_1.csv";

DHT dht(PINO_DHT, DHT11);

void escreverCampoFloat(Print &saida, float valor, int casas = 1) {
  if (isnan(valor)) {
    return;
  }
  saida.print(valor, casas);
}

void escreverCabecalho(Print &saida) {
  saida.println(
      "amostra,t_ms,mq3_raw,ppm,rs,rs_rsar,mq135_raw,mq135_mv,temperature_c,humidity_pct,alcool,tensao_atual_mv,tensao_referencia_mv");
}

void escreverLinha(Print &saida, unsigned long numero, const Leitura &amostra) {
  saida.print(numero);
  saida.print(',');
  saida.print(amostra.tMs);
  saida.print(',');
  saida.print(amostra.mq3);
  saida.print(',');
  saida.print(amostra.ppm, 1);
  saida.print(',');
  escreverCampoFloat(saida, amostra.rs, 2);
  saida.print(',');
  escreverCampoFloat(saida, amostra.rsRsAr, 2);
  saida.print(',');
  saida.print(amostra.mq135);
  saida.print(',');
  saida.print(amostra.mq135Mv);
  saida.print(',');
  escreverCampoFloat(saida, amostra.temperatura);
  saida.print(',');
  escreverCampoFloat(saida, amostra.umidade);
  saida.print(',');
  saida.print(amostra.alcool ? 1 : 0);
  saida.print(',');
  saida.print(amostra.tensaoAtualMv, 2);
  saida.print(',');
  saida.println(amostra.tensaoReferenciaMv, 2);
}

size_t espacoLivreCsv() {
  size_t total = LittleFS.totalBytes();
  size_t usado = LittleFS.usedBytes();
  if (total == 0 || usado >= total) {
    return 0;
  }
  return total - usado;
}

bool apagarCsvMaisAntigo() {
  char caminho[28];
  for (int numero = 1; numero < 10000; numero++) {
    snprintf(caminho, sizeof(caminho), "/leituras_%d.csv", numero);
    if (strcmp(caminho, arquivoCsv) == 0 || !LittleFS.exists(caminho)) {
      continue;
    }
    if (!LittleFS.remove(caminho)) {
      Serial.print("Falha ao apagar ");
      Serial.println(caminho);
      return false;
    }
    Serial.print("CSV antigo removido: ");
    Serial.println(caminho);
    return true;
  }
  return false;
}

bool formatarLittleFs() {
  Serial.println("LittleFS sem bloco livre: formatando a particao");
  LittleFS.end();
  bool formatou = LittleFS.format();
  sistemaArquivosOk = formatou && LittleFS.begin(true);
  if (!sistemaArquivosOk) {
    Serial.println("Sem sistema de arquivos: o CSV sai so no monitor");
    return false;
  }
  Serial.println("LittleFS formatado");
  return true;
}

// true se a particao foi formatada e o nome do CSV precisa ser escolhido de novo.
bool liberarEspacoCsv(bool podeFormatar) {
  if (!sistemaArquivosOk) {
    return false;
  }
  size_t livre = espacoLivreCsv();
  if (livre >= RESERVA_CSV_BYTES) {
    return false;
  }
  Serial.print("Espaco livre no LittleFS: ");
  Serial.println(livre);

  // Sem um bloco inteiro, apagar um CSV tambem aloca e reinicia a placa.
  if (livre < 4096) {
    if (podeFormatar) {
      return formatarLittleFs();
    }
    sistemaArquivosOk = false;
    Serial.println("Sem espaco no LittleFS: o CSV sai so no monitor");
    return false;
  }

  int removidos = 0;
  while (espacoLivreCsv() < RESERVA_CSV_BYTES && removidos < 200) {
    if (espacoLivreCsv() < 4096 || !apagarCsvMaisAntigo()) {
      break;
    }
    removidos++;
  }
  if (espacoLivreCsv() >= RESERVA_CSV_BYTES) {
    return false;
  }
  if (podeFormatar) {
    return formatarLittleFs();
  }
  sistemaArquivosOk = false;
  Serial.println("Sem espaco no LittleFS: o CSV sai so no monitor");
  return false;
}

void escolherCsvNovo() {
  int numero = 1;
  if (!sistemaArquivosOk) {
    snprintf(nomeCsv, sizeof(nomeCsv), "leituras_1.csv");
    snprintf(arquivoCsv, sizeof(arquivoCsv), "/leituras_1.csv");
    return;
  }
  while (numero < 10000) {
    snprintf(nomeCsv, sizeof(nomeCsv), "leituras_%d.csv", numero);
    snprintf(arquivoCsv, sizeof(arquivoCsv), "/%s", nomeCsv);
    if (!LittleFS.exists(arquivoCsv)) {
      break;
    }
    numero++;
  }
}

void iniciarCsv() {
  proximaAmostra = 1;
  escolherCsvNovo();
  if (liberarEspacoCsv(true)) {
    escolherCsvNovo();
  }
  if (!sistemaArquivosOk) {
    return;
  }
  File arquivo = LittleFS.open(arquivoCsv, "w");
  if (!arquivo) {
    sistemaArquivosOk = false;
    Serial.println("Falha ao criar o CSV");
    return;
  }
  escreverCabecalho(arquivo);
  arquivo.close();
}

void acrescentarCsv(unsigned long numero, const Leitura &amostra) {
  liberarEspacoCsv(false);
  if (!sistemaArquivosOk) {
    return;
  }
  File arquivo = LittleFS.open(arquivoCsv, "a");
  if (!arquivo) {
    Serial.println("Falha ao acrescentar leitura no CSV");
    return;
  }
  escreverLinha(arquivo, numero, amostra);
  arquivo.close();
}

float estimarPpm(float tensaoMv, float tensaoReferenciaMv, float &rs, float &rsRsAr) {
  rs = NAN;
  rsRsAr = NAN;
  if (tensaoMv <= 0.0f || tensaoReferenciaMv <= 0.0f ||
      tensaoMv >= TENSAO_CIRCUITO_MV || tensaoReferenciaMv >= TENSAO_CIRCUITO_MV) {
    return 0.0f;
  }

  float rsCalculado = (TENSAO_CIRCUITO_MV / tensaoMv) - 1.0f;
  float rsAr = (TENSAO_CIRCUITO_MV / tensaoReferenciaMv) - 1.0f;
  if (rsCalculado <= 0.0f || rsAr <= 0.0f) {
    return 0.0f;
  }
  rs = rsCalculado;
  rsRsAr = rs / rsAr;

  Serial.print("Tensao atual: ");
  Serial.println(tensaoMv);

  Serial.print("Tensao referencia: ");
  Serial.println(tensaoReferenciaMv);

  Serial.print("Rs: ");
  Serial.println(rs, 2);

  Serial.print("Rs/RsAr: ");
  Serial.println(rsRsAr, 2);

  float razao = RAZAO_AR_LIMPO * rsRsAr;
  float mgPorL = CURVA_A * powf(razao, CURVA_B);
  if (isnan(mgPorL) || isinf(mgPorL) || mgPorL < 0.0f) {
    return 0.0f;
  }
  return mgPorL * PPM_POR_MG_L;
}

void setup() {
  Serial.begin(115200);
  sistemaArquivosOk = LittleFS.begin(true);
  if (!sistemaArquivosOk) {
    Serial.println("Sem sistema de arquivos: o CSV sai so no monitor");
  }
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
  iniciarCsv();
  Serial.print("Arquivo CSV: ");
  Serial.println(nomeCsv);
  Serial.print("CSV_ARQUIVO,");
  Serial.println(nomeCsv);
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
  float rs = NAN;
  float rsRsAr = NAN;
  int tensaoAtualMv = analogReadMilliVolts(PINO_SENSOR);
  float ppm = estimarPpm(tensaoAtualMv, tensaoArLimpoMv, rs, rsRsAr);
  int leituraMq135 = analogRead(PINO_MQ135);
  int mq135Mv = analogReadMilliVolts(PINO_MQ135);
  bool alcool = leitura > (referencia + MARGEM);

  Leitura amostra;
  amostra.tMs = agora;
  amostra.mq3 = leitura;
  amostra.ppm = ppm;
  amostra.rs = rs;
  amostra.rsRsAr = rsRsAr;
  amostra.mq135 = leituraMq135;
  amostra.mq135Mv = mq135Mv;
  amostra.temperatura = temperaturaC;
  amostra.umidade = umidadePct;
  amostra.alcool = alcool;
  amostra.tensaoAtualMv = tensaoAtualMv;
  amostra.tensaoReferenciaMv = tensaoArLimpoMv;
  acrescentarCsv(proximaAmostra, amostra);
  Serial.print("CSV_LINHA,");
  Serial.print(nomeCsv);
  Serial.print(',');
  escreverLinha(Serial, proximaAmostra, amostra);
  proximaAmostra++;

  digitalWrite(PINO_LED, alcool ? HIGH : LOW);

  Serial.print("Leitura: ");
  Serial.print(leitura);
  Serial.print("  ppm: ");
  Serial.print(ppm, 1);
  Serial.print("  mq135: ");
  Serial.print(leituraMq135);
  Serial.print(" (");
  Serial.print(mq135Mv);
  Serial.print(" mV)");
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

  delay(INTERVALO_LEITURA_MS);
}
