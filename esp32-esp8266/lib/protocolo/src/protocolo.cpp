#include "protocolo.h"

#include <math.h>
#include <stdarg.h>
#include <stdio.h>

const char CABECALHO_CSV[] =
    "amostra,t_ms,mq3_raw,ppm,rs,rs_rsar,mq135_raw,mq135_mv,temperature_c,humidity_pct,alcool,"
    "tensao_atual_mv,tensao_referencia_mv";

namespace {

// Curva do MQ-3 (datasheet Hanwei). Ro e a resistencia em 0,4 mg/L de
// alcool; nesse ponto o datasheet indica cerca de 200 ppm. No ar limpo,
// Rs/Ro fica perto de 60. O circuito de teste do datasheet usa 5 V; o
// resistor de carga se cancela na razao Rs/Ro.
const float TENSAO_CIRCUITO_MV = 5000.0f;
const float RAZAO_AR_LIMPO = 60.0f;
const float CURVA_A = 0.3934f;
const float CURVA_B = -1.504f;
const float PPM_POR_MG_L = 200.0f / 0.4f;

// Escreve no fim de um texto sem passar do tamanho do buffer.
// Depois do primeiro estouro, "ok" fica false e nada mais e escrito.
struct Texto {
  char *buf;
  size_t tamanho;
  size_t usado;
  bool ok;

  Texto(char *b, size_t t) : buf(b), tamanho(t), usado(0), ok(t > 0) {
    if (ok) {
      buf[0] = '\0';
    }
  }

  void printf(const char *formato, ...) {
    if (!ok) {
      return;
    }
    va_list args;
    va_start(args, formato);
    int n = vsnprintf(buf + usado, tamanho - usado, formato, args);
    va_end(args);
    if (n < 0 || static_cast<size_t>(n) >= tamanho - usado) {
      ok = false;
      buf[tamanho - 1] = '\0';
      return;
    }
    usado += static_cast<size_t>(n);
  }

  // Campo do CSV: vazio quando NAN.
  void campoCsv(float valor, int casas) {
    if (!isnan(valor)) {
      printf("%.*f", casas, valor);
    }
  }

  // Numero do JSON: null quando NAN ou infinito (JSON nao tem NaN).
  void numeroJson(float valor, int casas) {
    if (isnan(valor) || isinf(valor)) {
      printf("null");
    } else {
      printf("%.*f", casas, valor);
    }
  }

  void textoOuNull(const char *valor) {
    if (valor == nullptr) {
      printf("null");
    } else {
      printf("\"%s\"", valor);
    }
  }
};

}  // namespace

bool formatarLinhaCsv(char *saida, size_t tamanho, const Leitura &l) {
  Texto t(saida, tamanho);
  t.printf("%lu,%lu,%d,", static_cast<unsigned long>(l.amostra), static_cast<unsigned long>(l.tMs), l.mq3);
  t.printf("%.1f,", l.ppm);
  t.campoCsv(l.rs, 2);
  t.printf(",");
  t.campoCsv(l.rsRsAr, 2);
  t.printf(",%d,%d,", l.mq135, l.mq135Mv);
  t.campoCsv(l.temperatura, 1);
  t.printf(",");
  t.campoCsv(l.umidade, 1);
  t.printf(",%d,%.2f,%.2f", l.alcool ? 1 : 0, l.tensaoAtualMv, l.tensaoReferenciaMv);
  return t.ok;
}

bool jsonLeitura(char *saida, size_t tamanho, const char *rodadaId, const Leitura &l) {
  Texto t(saida, tamanho);
  t.printf("{\"rodada_id\":\"%s\",\"amostra\":%lu,\"t_ms\":%lu,\"mq3_raw\":%d,\"ppm\":", rodadaId,
           static_cast<unsigned long>(l.amostra), static_cast<unsigned long>(l.tMs), l.mq3);
  t.numeroJson(l.ppm, 1);
  t.printf(",\"mq135_raw\":%d,\"mq135_mv\":%d,\"temperature_c\":", l.mq135, l.mq135Mv);
  t.numeroJson(l.temperatura, 1);
  t.printf(",\"humidity_pct\":");
  t.numeroJson(l.umidade, 1);
  t.printf(",\"alcool\":%d}", l.alcool ? 1 : 0);
  return t.ok;
}

bool jsonEvento(char *saida, size_t tamanho, const char *rodadaId, const char *tipo, uint32_t tMs) {
  Texto t(saida, tamanho);
  t.printf("{\"rodada_id\":\"%s\",\"tipo\":\"%s\",\"t_ms\":%lu}", rodadaId, tipo,
           static_cast<unsigned long>(tMs));
  return t.ok;
}

bool jsonRodada(char *saida, size_t tamanho, const char *rodadaId, const char *placa,
                const char *arquivoSessao, const char *inicioIso) {
  Texto t(saida, tamanho);
  t.printf("{\"rodada_id\":\"%s\",\"placa\":\"%s\",\"caso\":null,\"participante\":null,\"inicio\":",
           rodadaId, placa);
  t.textoOuNull(inicioIso);
  t.printf(",\"arquivo_sessao\":\"%s\",\"origem\":\"placa\"}", arquivoSessao);
  return t.ok;
}

bool montarTopico(char *saida, size_t tamanho, const char *placa, const char *tipo) {
  Texto t(saida, tamanho);
  t.printf("mq3/%s/%s", placa, tipo);
  return t.ok;
}

void uuidV4(const uint8_t bytes[16], char saida[TAMANHO_UUID]) {
  uint8_t b[16];
  for (int i = 0; i < 16; i++) {
    b[i] = bytes[i];
  }
  b[6] = (b[6] & 0x0F) | 0x40;  // versao 4 (aleatorio)
  b[8] = (b[8] & 0x3F) | 0x80;  // variante RFC 4122
  snprintf(saida, TAMANHO_UUID,
           "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x", b[0], b[1], b[2],
           b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]);
}

float estimarPpm(float tensaoMv, float tensaoReferenciaMv, float &rs, float &rsRsAr) {
  rs = NAN;
  rsRsAr = NAN;
  if (tensaoMv <= 0.0f || tensaoReferenciaMv <= 0.0f || tensaoMv >= TENSAO_CIRCUITO_MV ||
      tensaoReferenciaMv >= TENSAO_CIRCUITO_MV) {
    return 0.0f;
  }
  float rsCalculado = (TENSAO_CIRCUITO_MV / tensaoMv) - 1.0f;
  float rsAr = (TENSAO_CIRCUITO_MV / tensaoReferenciaMv) - 1.0f;
  if (rsCalculado <= 0.0f || rsAr <= 0.0f) {
    return 0.0f;
  }
  rs = rsCalculado;
  rsRsAr = rs / rsAr;

  float razao = RAZAO_AR_LIMPO * rsRsAr;
  float mgPorL = CURVA_A * powf(razao, CURVA_B);
  if (isnan(mgPorL) || isinf(mgPorL) || mgPorL < 0.0f) {
    return 0.0f;
  }
  return mgPorL * PPM_POR_MG_L;
}
