// tarefaArmazenamento: dona do CSV no LittleFS e da serial de dados.
//
// Recebe leituras e eventos da fila de registros, na ordem em que
// aconteceram, e para cada leitura:
//   1. numera a amostra (1, 2, 3... dentro da rodada);
//   2. acrescenta a linha ao CSV no LittleFS;
//   3. escreve "CSV_LINHA,<arquivo>,<campos>" na serial (a ponte
//      applications/coleta/ponte.py continua funcionando como antes);
//   4. entrega a mesma leitura a tarefaRede pela fila de rede.
//
// Uma rodada vai da partida (ou do ultimo aperto longo do botao) ate o
// proximo rodada_fim. Cada rodada tem um UUID v4 (o banco usa uuid), um CSV
// novo e uma mensagem "rodada" retida no MQTT.
//
// Todo o estado do CSV (nome, contador, sistema de arquivos) e privado
// desta tarefa: nenhuma outra tarefa o le ou escreve.
#include <Arduino.h>
#include <LittleFS.h>
#include <esp_system.h>

#include "config.h"
#include "filas.h"
#include "log_serial.h"
#include "tarefas.h"

namespace {

struct EstadoCsv {
  bool sistemaArquivosOk;
  char nome[24];
  char caminho[28];
  char caminhoEventos[40];  // /leituras_N.eventos.csv, ao lado do CSV
  uint32_t proximaAmostra;
  char rodadaId[TAMANHO_UUID];
};

size_t espacoLivre() {
  size_t total = LittleFS.totalBytes();
  size_t usado = LittleFS.usedBytes();
  if (total == 0 || usado >= total) {
    return 0;
  }
  return total - usado;
}

bool apagarCsvMaisAntigo(const EstadoCsv &csv) {
  char caminho[28];
  for (int numero = 1; numero < 10000; numero++) {
    snprintf(caminho, sizeof(caminho), "/leituras_%d.csv", numero);
    if (strcmp(caminho, csv.caminho) == 0 || !LittleFS.exists(caminho)) {
      continue;
    }
    if (!LittleFS.remove(caminho)) {
      logf("Falha ao apagar %s", caminho);
      return false;
    }
    char eventos[40];
    snprintf(eventos, sizeof(eventos), "/leituras_%d.eventos.csv", numero);
    LittleFS.remove(eventos);
    logf("CSV antigo removido: %s", caminho);
    return true;
  }
  return false;
}

bool formatarLittleFs(EstadoCsv &csv) {
  logf("LittleFS sem bloco livre: formatando a particao");
  LittleFS.end();
  bool formatou = LittleFS.format();
  csv.sistemaArquivosOk = formatou && LittleFS.begin(true);
  if (!csv.sistemaArquivosOk) {
    logf("Sem sistema de arquivos: o CSV sai so no monitor");
    return false;
  }
  logf("LittleFS formatado");
  return true;
}

// true se a particao foi formatada e o nome do CSV precisa ser escolhido de novo.
bool liberarEspaco(EstadoCsv &csv, bool podeFormatar) {
  if (!csv.sistemaArquivosOk) {
    return false;
  }
  size_t livre = espacoLivre();
  if (livre >= RESERVA_CSV_BYTES) {
    return false;
  }
  logf("Espaco livre no LittleFS: %u", static_cast<unsigned>(livre));

  // Sem um bloco inteiro, apagar um CSV tambem aloca e reinicia a placa.
  if (livre < 4096) {
    if (podeFormatar) {
      return formatarLittleFs(csv);
    }
    csv.sistemaArquivosOk = false;
    logf("Sem espaco no LittleFS: o CSV sai so no monitor");
    return false;
  }

  int removidos = 0;
  while (espacoLivre() < RESERVA_CSV_BYTES && removidos < 200) {
    if (espacoLivre() < 4096 || !apagarCsvMaisAntigo(csv)) {
      break;
    }
    removidos++;
  }
  if (espacoLivre() >= RESERVA_CSV_BYTES) {
    return false;
  }
  if (podeFormatar) {
    return formatarLittleFs(csv);
  }
  csv.sistemaArquivosOk = false;
  logf("Sem espaco no LittleFS: o CSV sai so no monitor");
  return false;
}

void escolherNomeCsv(EstadoCsv &csv) {
  snprintf(csv.nome, sizeof(csv.nome), "leituras_1.csv");
  snprintf(csv.caminho, sizeof(csv.caminho), "/leituras_1.csv");
  if (!csv.sistemaArquivosOk) {
    return;
  }
  for (int numero = 1; numero < 10000; numero++) {
    snprintf(csv.nome, sizeof(csv.nome), "leituras_%d.csv", numero);
    snprintf(csv.caminho, sizeof(csv.caminho), "/%s", csv.nome);
    if (!LittleFS.exists(csv.caminho)) {
      break;
    }
  }
}

void gerarRodadaId(char saida[TAMANHO_UUID]) {
  uint8_t bytes[16];
  esp_fill_random(bytes, sizeof(bytes));
  uuidV4(bytes, saida);
}

// Entrega a mensagem a rede sem esperar: se a fila estiver cheia (rede
// travada), a mensagem se perde aqui, mas o CSV e a serial continuam
// completos. A ponte e o CSV sao a fonte de verdade; o MQTT e o canal rapido.
void entregarRede(const Filas *filas, const MensagemRede &mensagem) {
  if (xQueueSend(filas->rede, &mensagem, 0) != pdTRUE) {
    logf("Fila de rede cheia: mensagem nao publicada (CSV preservado)");
  }
}

// Abre uma rodada: UUID novo, CSV novo, aviso na serial e na fila de rede.
void abrirRodada(EstadoCsv &csv, const Filas *filas) {
  csv.proximaAmostra = 1;
  gerarRodadaId(csv.rodadaId);
  escolherNomeCsv(csv);
  if (liberarEspaco(csv, true)) {
    escolherNomeCsv(csv);
  }
  snprintf(csv.caminhoEventos, sizeof(csv.caminhoEventos), "/%.*s.eventos.csv",
           static_cast<int>(strlen(csv.nome) - 4), csv.nome);
  if (csv.sistemaArquivosOk) {
    File eventos = LittleFS.open(csv.caminhoEventos, "w");
    if (eventos) {
      eventos.println("tipo,t_ms");
      eventos.close();
    }
    File arquivo = LittleFS.open(csv.caminho, "w");
    if (!arquivo) {
      csv.sistemaArquivosOk = false;
      logf("Falha ao criar o CSV");
    } else {
      arquivo.println(CABECALHO_CSV);
      arquivo.close();
    }
  }
  logf("Arquivo CSV: %s", csv.nome);
  logf("CSV_ARQUIVO,%s", csv.nome);
  logf("Rodada %s", csv.rodadaId);

  MensagemRede mensagem = {};
  mensagem.tipo = TipoMensagem::RODADA;
  strlcpy(mensagem.rodadaId, csv.rodadaId, sizeof(mensagem.rodadaId));
  strlcpy(mensagem.arquivo, csv.nome, sizeof(mensagem.arquivo));
  mensagem.tMs = millis();
  entregarRede(filas, mensagem);
}

void acrescentarCsv(EstadoCsv &csv, const char *linha) {
  liberarEspaco(csv, false);
  if (!csv.sistemaArquivosOk) {
    return;
  }
  File arquivo = LittleFS.open(csv.caminho, "a");
  if (!arquivo) {
    logf("Falha ao acrescentar leitura no CSV");
    return;
  }
  arquivo.println(linha);
  arquivo.close();
}

void tratarLeitura(EstadoCsv &csv, const Filas *filas, Leitura leitura) {
  leitura.amostra = csv.proximaAmostra++;

  char campos[160];
  if (!formatarLinhaCsv(campos, sizeof(campos), leitura)) {
    logf("Linha do CSV maior que o buffer: leitura %lu descartada",
         static_cast<unsigned long>(leitura.amostra));
    return;
  }
  acrescentarCsv(csv, campos);
  logf("CSV_LINHA,%s,%s", csv.nome, campos);
  logf("Leitura: %d  ppm: %.1f  mq135: %d (%d mV)  temp: %s  umidade: %s%s", leitura.mq3, leitura.ppm,
       leitura.mq135, leitura.mq135Mv, isnan(leitura.temperatura) ? "--" : String(leitura.temperatura, 1).c_str(),
       isnan(leitura.umidade) ? "--" : String(leitura.umidade, 1).c_str(),
       leitura.alcool ? "  ALCOOL - LED aceso" : "  ar limpo - LED apagado");

  MensagemRede mensagem = {};
  mensagem.tipo = TipoMensagem::LEITURA;
  strlcpy(mensagem.rodadaId, csv.rodadaId, sizeof(mensagem.rodadaId));
  mensagem.leitura = leitura;
  entregarRede(filas, mensagem);
}

void tratarEvento(EstadoCsv &csv, const Filas *filas, TipoEvento evento, uint32_t tMs) {
  // Serial e arquivo primeiro: o MQTT (QoS 0) pode perder o evento, estes nao.
  char linha[48];
  snprintf(linha, sizeof(linha), "%s,%lu", nomeEvento(evento), static_cast<unsigned long>(tMs));
  logf("CSV_EVENTO,%s,%s", csv.nome, linha);
  if (csv.sistemaArquivosOk) {
    File arquivo = LittleFS.open(csv.caminhoEventos, "a");
    if (arquivo) {
      arquivo.println(linha);
      arquivo.close();
    } else {
      logf("Falha ao gravar o evento no arquivo de eventos");
    }
  }
  MensagemRede mensagem = {};
  mensagem.tipo = TipoMensagem::EVENTO;
  strlcpy(mensagem.rodadaId, csv.rodadaId, sizeof(mensagem.rodadaId));
  mensagem.evento = evento;
  mensagem.tMs = tMs;
  entregarRede(filas, mensagem);
  logf("Evento: %s em %lu ms", nomeEvento(evento), static_cast<unsigned long>(tMs));

  if (evento == TipoEvento::RODADA_FIM) {
    abrirRodada(csv, filas);
  }
}

}  // namespace

void tarefaArmazenamento(void *parametro) {
  Filas *filas = static_cast<Filas *>(parametro);

  EstadoCsv csv = {};
  csv.sistemaArquivosOk = LittleFS.begin(true);
  if (!csv.sistemaArquivosOk) {
    logf("Sem sistema de arquivos: o CSV sai so no monitor");
  }
  abrirRodada(csv, filas);

  for (;;) {
    Registro registro;
    xQueueReceive(filas->registros, &registro, portMAX_DELAY);
    if (registro.tipo == TipoRegistro::LEITURA) {
      tratarLeitura(csv, filas, registro.leitura);
    } else {
      tratarEvento(csv, filas, registro.evento, registro.tMs);
    }
  }
}
