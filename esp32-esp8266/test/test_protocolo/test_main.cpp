// Testes do protocolo, rodados no PC: pio test -e native
// Conferem que a placa escreve o mesmo CSV de antes e o JSON do contrato
// MQTT da coleta (applications/coleta/mensagens.py).
#include <math.h>
#include <string.h>
#include <unity.h>

#include "protocolo.h"

static Leitura leituraExemplo() {
  Leitura l = {};
  l.amostra = 7;
  l.tMs = 12345;
  l.mq3 = 812;
  l.ppm = 3.26f;
  l.rs = 4.5f;
  l.rsRsAr = 0.75f;
  l.mq135 = 1500;
  l.mq135Mv = 1320;
  l.temperatura = 26.0f;
  l.umidade = 61.0f;
  l.alcool = false;
  l.tensaoAtualMv = 900.0f;
  l.tensaoReferenciaMv = 850.5f;
  return l;
}

void setUp() {}
void tearDown() {}

void test_linha_csv_tem_as_13_colunas_do_firmware_antigo() {
  char linha[160];
  Leitura l = leituraExemplo();
  formatarLinhaCsv(linha, sizeof(linha), l);
  TEST_ASSERT_EQUAL_STRING("7,12345,812,3.3,4.50,0.75,1500,1320,26.0,61.0,0,900.00,850.50", linha);
}

void test_linha_csv_deixa_vazio_o_que_o_dht_nao_leu() {
  char linha[160];
  Leitura l = leituraExemplo();
  l.temperatura = NAN;
  l.umidade = NAN;
  l.rs = NAN;
  l.rsRsAr = NAN;
  l.alcool = true;
  formatarLinhaCsv(linha, sizeof(linha), l);
  TEST_ASSERT_EQUAL_STRING("7,12345,812,3.3,,,1500,1320,,,1,900.00,850.50", linha);
}

void test_json_leitura_segue_o_contrato() {
  char json[320];
  Leitura l = leituraExemplo();
  jsonLeitura(json, sizeof(json), "abc", l);
  TEST_ASSERT_EQUAL_STRING(
      "{\"rodada_id\":\"abc\",\"amostra\":7,\"t_ms\":12345,\"mq3_raw\":812,\"ppm\":3.3,"
      "\"mq135_raw\":1500,\"mq135_mv\":1320,\"temperature_c\":26.0,\"humidity_pct\":61.0,\"alcool\":0}",
      json);
}

void test_json_leitura_manda_null_sem_dht() {
  char json[320];
  Leitura l = leituraExemplo();
  l.temperatura = NAN;
  l.umidade = NAN;
  jsonLeitura(json, sizeof(json), "abc", l);
  TEST_ASSERT_NOT_NULL(strstr(json, "\"temperature_c\":null,\"humidity_pct\":null"));
}

void test_json_evento() {
  char json[128];
  jsonEvento(json, sizeof(json), "abc", "sopro_inicio", 4000);
  TEST_ASSERT_EQUAL_STRING("{\"rodada_id\":\"abc\",\"tipo\":\"sopro_inicio\",\"t_ms\":4000}", json);
}

void test_json_rodada_sem_horario() {
  char json[320];
  jsonRodada(json, sizeof(json), "abc", "placa01", "leituras_3.csv", nullptr);
  TEST_ASSERT_EQUAL_STRING(
      "{\"rodada_id\":\"abc\",\"placa\":\"placa01\",\"caso\":null,\"participante\":null,"
      "\"inicio\":null,\"arquivo_sessao\":\"leituras_3.csv\",\"origem\":\"placa\"}",
      json);
}

void test_json_rodada_com_horario() {
  char json[320];
  jsonRodada(json, sizeof(json), "abc", "placa01", "leituras_3.csv", "2026-11-24T13:00:00+00:00");
  TEST_ASSERT_NOT_NULL(strstr(json, "\"inicio\":\"2026-11-24T13:00:00+00:00\""));
}

void test_uuid_v4_marca_versao_e_variante() {
  uint8_t bytes[16];
  for (int i = 0; i < 16; i++) {
    bytes[i] = 0xFF;
  }
  char uuid[37];
  uuidV4(bytes, uuid);
  TEST_ASSERT_EQUAL_STRING("ffffffff-ffff-4fff-bfff-ffffffffffff", uuid);
  for (int i = 0; i < 16; i++) {
    bytes[i] = 0x00;
  }
  uuidV4(bytes, uuid);
  TEST_ASSERT_EQUAL_STRING("00000000-0000-4000-8000-000000000000", uuid);
}

void test_topico() {
  char topico[64];
  montarTopico(topico, sizeof(topico), "placa01", "leituras");
  TEST_ASSERT_EQUAL_STRING("mq3/placa01/leituras", topico);
}

void test_ppm_e_zero_no_ar_da_partida_fora_da_escala() {
  float rs = 0;
  float rsRsAr = 0;
  TEST_ASSERT_EQUAL_FLOAT(0.0f, estimarPpm(0.0f, 800.0f, rs, rsRsAr));
  TEST_ASSERT_TRUE(isnan(rs));
}

void test_ppm_no_ar_da_partida_usa_a_curva_do_datasheet() {
  float rs = 0;
  float rsRsAr = 0;
  // Rs/RsAr = 1: razao 60, ppm = 0,3934 * 60^-1,504 * 500.
  float ppm = estimarPpm(800.0f, 800.0f, rs, rsRsAr);
  TEST_ASSERT_FLOAT_WITHIN(0.0001f, 1.0f, rsRsAr);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.3934f * powf(60.0f, -1.504f) * 500.0f, ppm);
}

void test_texto_truncado_devolve_falso() {
  char pequeno[8];
  Leitura l = leituraExemplo();
  TEST_ASSERT_FALSE(formatarLinhaCsv(pequeno, sizeof(pequeno), l));
  TEST_ASSERT_FALSE(jsonLeitura(pequeno, sizeof(pequeno), "abc", l));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_linha_csv_tem_as_13_colunas_do_firmware_antigo);
  RUN_TEST(test_linha_csv_deixa_vazio_o_que_o_dht_nao_leu);
  RUN_TEST(test_json_leitura_segue_o_contrato);
  RUN_TEST(test_json_leitura_manda_null_sem_dht);
  RUN_TEST(test_json_evento);
  RUN_TEST(test_json_rodada_sem_horario);
  RUN_TEST(test_json_rodada_com_horario);
  RUN_TEST(test_uuid_v4_marca_versao_e_variante);
  RUN_TEST(test_topico);
  RUN_TEST(test_ppm_e_zero_no_ar_da_partida_fora_da_escala);
  RUN_TEST(test_ppm_no_ar_da_partida_usa_a_curva_do_datasheet);
  RUN_TEST(test_texto_truncado_devolve_falso);
  return UNITY_END();
}
