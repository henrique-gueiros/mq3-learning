// tarefaRede: Wi-Fi, MQTT e uma fila de mensagens pendentes limitada.
//
// Na partida abre uma rodada (UUID v4, arquivo_sessao "ao_vivo": nao ha
// CSV na placa). Recebe Leitura da tarefaSensores, numera a amostra e
// publica quando o broker esta conectado. Sem Wi-Fi ou broker, as
// leituras ficam na fila interna (MAX_PENDENTES_REDE); o que nao cabe
// e descartado. O sopro nao e marcado aqui: a equipe marca na ponte.
//
// Topicos (contrato de applications/coleta/mensagens.py):
//   mq3/<placa>/rodada    retida, na partida
//   mq3/<placa>/leituras  uma leitura por mensagem
//   mq3/<placa>/status    retida; {"estado":"online"} ao conectar e
//                         {"estado":"offline"} como last will
//
// QoS: o PubSubClient so publica com QoS 0 (sem confirmacao do broker).
// O last will vai com QoS 1. Veja o README para a troca por uma lib com QoS 1.
#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <esp_system.h>
#include <string.h>
#include <time.h>

#include "cliente_tcp.h"
#include "config.h"
#include "filas.h"
#include "log_serial.h"
#include "tarefas.h"

namespace {

enum class TipoMensagem : uint8_t { RODADA, LEITURA };

struct MensagemRede {
  TipoMensagem tipo;
  char rodadaId[TAMANHO_UUID];
  Leitura leitura;
  uint32_t tMs;      // RODADA: millis da abertura
  char arquivo[24];  // RODADA: nome logico (nao e um arquivo na placa)
};

// Fila de pendentes em vetor (so esta tarefa a usa; sem mutex).
// Cheia: descarta a leitura mais antiga; a mensagem rodada nunca sai.
class Pendentes {
 public:
  size_t tamanho() const { return _n; }
  const MensagemRede &frente() const { return _itens[0]; }
  uint32_t descartadas() const { return _descartadas; }

  void adicionar(const MensagemRede &mensagem) {
    if (_n == MAX_PENDENTES_REDE) {
      size_t i = indiceDescartavel();
      _descartadas++;
      if (i == _n) {
        return;  // so ha rodadas na fila: descarta a nova (nunca uma rodada)
      }
      remover(i);
    }
    _itens[_n++] = mensagem;
  }

  void tirarFrente() { remover(0); }

 private:
  size_t indiceDescartavel() const {
    // A leitura mais antiga. A rodada (retida) nunca e descartada.
    // Devolve _n se nao ha o que tirar.
    for (size_t i = 0; i < _n; i++) {
      if (_itens[i].tipo == TipoMensagem::LEITURA) {
        return i;
      }
    }
    return _n;
  }

  void remover(size_t i) {
    memmove(&_itens[i], &_itens[i + 1], (_n - i - 1) * sizeof(MensagemRede));
    _n--;
  }

  MensagemRede _itens[MAX_PENDENTES_REDE];
  size_t _n = 0;
  uint32_t _descartadas = 0;
};

const char MENSAGEM_ONLINE[] = "{\"estado\":\"online\"}";
const char MENSAGEM_OFFLINE[] = "{\"estado\":\"offline\"}";

bool brokerEhIpv6() { return MQTT_USAR_IPV6 != 0 || strchr(MQTT_HOST, ':') != nullptr; }

// Horario UTC de um instante da placa (millis), se o NTP ja acertou o relogio.
bool horarioIso(uint32_t tMs, char *saida, size_t tamanho) {
  time_t agora = time(nullptr);
  if (agora < 1700000000) {  // relogio ainda em 1970
    return false;
  }
  time_t instante = agora - static_cast<time_t>((millis() - tMs) / 1000);
  struct tm tm;
  gmtime_r(&instante, &tm);
  return strftime(saida, tamanho, "%Y-%m-%dT%H:%M:%S+00:00", &tm) > 0;
}

// Publica uma mensagem; false se o broker nao aceitou (volta para a fila).
bool publicar(PubSubClient &mqtt, const MensagemRede &m) {
  char json[TAMANHO_JSON];
  char topico[64];
  const char *tipoTopico = "leituras";
  bool retida = false;
  bool coube = false;

  switch (m.tipo) {
    case TipoMensagem::RODADA: {
      char inicio[32];
      bool temHorario = horarioIso(m.tMs, inicio, sizeof(inicio));
      coube = jsonRodada(json, sizeof(json), m.rodadaId, PLACA, m.arquivo, temHorario ? inicio : nullptr,
                         CASO_PADRAO, PARTICIPANTE_PADRAO);
      tipoTopico = "rodada";
      retida = true;
      break;
    }
    case TipoMensagem::LEITURA:
      coube = jsonLeitura(json, sizeof(json), m.rodadaId, m.leitura);
      break;
  }
  if (!coube || !montarTopico(topico, sizeof(topico), PLACA, tipoTopico)) {
    logf("Mensagem MQTT maior que o buffer: descartada");
    return true;  // nao adianta tentar de novo
  }
  return mqtt.publish(topico, json, retida);
}

void gerarRodadaId(char saida[TAMANHO_UUID]) {
  uint8_t bytes[16];
  esp_fill_random(bytes, sizeof(bytes));
  uuidV4(bytes, saida);
}

}  // namespace

void tarefaRede(void *parametro) {
  Filas *filas = static_cast<Filas *>(parametro);

  char topicoStatus[64];
  montarTopico(topicoStatus, sizeof(topicoStatus), PLACA, "status");
  char idCliente[48];
  snprintf(idCliente, sizeof(idCliente), "%s-%04X", PLACA, static_cast<unsigned>(ESP.getEfuseMac() >> 32));

  // Wi-Fi: o core reconecta sozinho (setAutoReconnect); este laco ainda
  // recomeca a conexao se ela ficar caida por ESPERA_WIFI_MS.
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.onEvent(
      [](arduino_event_id_t, arduino_event_info_t) {
        // IPv6 da estacao: precisa ser pedido depois de associar ao AP.
        // O endereco global vem do anuncio do roteador (SLAAC).
        WiFi.enableIpV6();
      },
      ARDUINO_EVENT_WIFI_STA_CONNECTED);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  logf("Wi-Fi: conectando a \"%s\"", WIFI_SSID);

  static Pendentes pendentes;  // 120 x ~150 bytes: fora da pilha da tarefa
  char rodadaId[TAMANHO_UUID];
  gerarRodadaId(rodadaId);
  uint32_t proximaAmostra = 1;
  {
    MensagemRede rodada = {};
    rodada.tipo = TipoMensagem::RODADA;
    strlcpy(rodada.rodadaId, rodadaId, sizeof(rodada.rodadaId));
    strlcpy(rodada.arquivo, ARQUIVO_AO_VIVO, sizeof(rodada.arquivo));
    rodada.tMs = millis();
    pendentes.adicionar(rodada);
    logf("Rodada %s (ao vivo, sem CSV na placa)", rodadaId);
  }
  ClienteTcp tcp(brokerEhIpv6(), TIMEOUT_TCP_MS);
  PubSubClient mqtt(tcp);
  mqtt.setServer(MQTT_HOST, MQTT_PORTA);
  mqtt.setBufferSize(512);
  mqtt.setSocketTimeout(5);
  mqtt.setKeepAlive(15);

  bool ntpIniciado = false;
  uint32_t ntpIniciadoEm = 0;
  bool wifiAvisado = false;
  uint32_t semWifiDesde = millis();
  uint32_t ultimaTentativaMqtt = 0;
  uint32_t descartadasAvisadas = 0;

  for (;;) {
    // 1. Recebe dos sensores (espera ate 200 ms: tambem serve de ritmo do laco).
    Leitura leitura;
    if (xQueueReceive(filas->leituras, &leitura, pdMS_TO_TICKS(200)) == pdTRUE) {
      do {
        leitura.amostra = proximaAmostra++;
        MensagemRede mensagem = {};
        mensagem.tipo = TipoMensagem::LEITURA;
        strlcpy(mensagem.rodadaId, rodadaId, sizeof(mensagem.rodadaId));
        mensagem.leitura = leitura;
        pendentes.adicionar(mensagem);
        logf("Leitura %lu  ppm: %.1f  mq135: %d  umidade: %s",
             static_cast<unsigned long>(leitura.amostra), leitura.ppm, leitura.mq135,
             isnan(leitura.umidade) ? "--" : String(leitura.umidade, 1).c_str());
      } while (xQueueReceive(filas->leituras, &leitura, 0) == pdTRUE);
    }
    if (pendentes.descartadas() != descartadasAvisadas) {
      descartadasAvisadas = pendentes.descartadas();
      logf("Rede: %lu leituras antigas descartadas (broker fora do ar)",
           static_cast<unsigned long>(descartadasAvisadas));
    }

    // 2. Wi-Fi.
    if (WiFi.status() != WL_CONNECTED) {
      wifiAvisado = false;
      if (millis() - semWifiDesde > ESPERA_WIFI_MS) {
        logf("Wi-Fi: sem conexao ha %lu s; recomecando", static_cast<unsigned long>(ESPERA_WIFI_MS / 1000));
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_SENHA);
        semWifiDesde = millis();
      }
      continue;
    }
    semWifiDesde = millis();
    if (!wifiAvisado) {
      wifiAvisado = true;
      logf("Wi-Fi: conectado, IPv4 %s", WiFi.localIP().toString().c_str());
    }
    if (!ntpIniciado) {
      ntpIniciado = true;
      ntpIniciadoEm = millis();
      configTime(0, 0, "pool.ntp.org", "time.google.com");
    }

    // 3. MQTT. Espera o NTP acertar o relogio (ate 8 s) para a mensagem
    // "rodada" retida levar o horario de inicio.
    if (!mqtt.connected()) {
      if (time(nullptr) < 1700000000 && millis() - ntpIniciadoEm < 8000) {
        continue;
      }
      if (millis() - ultimaTentativaMqtt < ESPERA_MQTT_MS && ultimaTentativaMqtt != 0) {
        continue;
      }
      ultimaTentativaMqtt = millis();
      logf("MQTT: conectando a %s:%d", MQTT_HOST, MQTT_PORTA);
      bool ok = mqtt.connect(idCliente, strlen(MQTT_USUARIO) > 0 ? MQTT_USUARIO : nullptr,
                             strlen(MQTT_USUARIO) > 0 ? MQTT_SENHA : nullptr, topicoStatus, 1, true,
                             MENSAGEM_OFFLINE);
      if (!ok) {
        logf("MQTT: falhou (estado %d)", mqtt.state());
        continue;
      }
      mqtt.publish(topicoStatus, MENSAGEM_ONLINE, true);
      logf("MQTT: conectado; %u mensagens pendentes", static_cast<unsigned>(pendentes.tamanho()));
    }

    // 4. Esvazia os pendentes, em ordem. Falhou: para e tenta na proxima volta.
    while (pendentes.tamanho() > 0) {
      if (!publicar(mqtt, pendentes.frente())) {
        logf("MQTT: publicacao falhou; mantendo %u pendentes", static_cast<unsigned>(pendentes.tamanho()));
        mqtt.disconnect();
        break;
      }
      pendentes.tirarFrente();
    }
    mqtt.loop();
  }
}
