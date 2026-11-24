// Protocolo do Sopro Seguro: o que a placa escreve no CSV e publica no MQTT.
//
// Tudo aqui e C++ puro (sem Arduino) para rodar tambem no PC, nos testes de
// test/test_protocolo (pio test -e native). O contrato MQTT e o mesmo da
// ponte serial: applications/coleta/mensagens.py e ARCHITECTURE.md.
#pragma once

#include <stddef.h>
#include <stdint.h>

// Uma leitura dos sensores. "amostra" e numerada pela tarefa de
// armazenamento (1, 2, 3... dentro de cada rodada); o resto vem da tarefa
// de sensores. NAN marca o que nao foi lido (DHT11 nos primeiros segundos).
struct Leitura {
  uint32_t amostra;
  uint32_t tMs;
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

// Tamanho do texto de um UUID (36 caracteres + '\0').
const size_t TAMANHO_UUID = 37;

// Cabecalho do CSV de 13 colunas (o mesmo do firmware anterior).
extern const char CABECALHO_CSV[];

// Cada funcao de texto devolve false se o texto nao coube em "saida".

// Linha do CSV, sem quebra de linha. Campos NAN ficam vazios.
bool formatarLinhaCsv(char *saida, size_t tamanho, const Leitura &leitura);

// Mensagem de mq3/<placa>/leituras. Campos NAN viram null.
bool jsonLeitura(char *saida, size_t tamanho, const char *rodadaId, const Leitura &leitura);

// Mensagem de mq3/<placa>/eventos (sopro_inicio, sopro_fim, rodada_fim).
bool jsonEvento(char *saida, size_t tamanho, const char *rodadaId, const char *tipo, uint32_t tMs);

// Mensagem retida de mq3/<placa>/rodada. "inicioIso" pode ser nullptr
// (sem relogio de NTP): vai como null. caso e participante tambem podem ser
// nullptr ou "" (vao como null): a placa nao sabe quem esta soprando, entao
// so levam o padrao configurado em segredos.h.
bool jsonRodada(char *saida, size_t tamanho, const char *rodadaId, const char *placa,
                const char *arquivoSessao, const char *inicioIso, const char *caso = nullptr,
                const char *participante = nullptr);

// mq3/<placa>/<tipo>
bool montarTopico(char *saida, size_t tamanho, const char *placa, const char *tipo);

// UUID versao 4 a partir de 16 bytes aleatorios (a placa usa esp_random()).
void uuidV4(const uint8_t bytes[16], char saida[TAMANHO_UUID]);

// ppm estimado pela curva do datasheet do MQ-3 (Hanwei). A tensao da
// partida e tratada como ar limpo. Devolve 0 fora da escala e preenche
// rs e rsRsAr (NAN quando nao da para calcular).
float estimarPpm(float tensaoMv, float tensaoReferenciaMv, float &rs, float &rsRsAr);
