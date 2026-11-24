// tarefaRede: Wi-Fi, MQTT e uma fila de mensagens pendentes limitada.
//
// Recebe MensagemRede da tarefaArmazenamento, guarda numa fila interna
// (MAX_PENDENTES_REDE) e publica quando o broker esta conectado. Sem Wi-Fi
// ou broker, o CSV e a serial continuam: a rede e o canal rapido, nao a
// fonte de verdade.
//
// Topicos (contrato de applications/coleta/mensagens.py):
//   mq3/<placa>/rodada    retida, no inicio de cada rodada
//   mq3/<placa>/leituras  uma leitura por mensagem
//   mq3/<placa>/eventos   sopro_inicio, sopro_fim, rodada_fim
//   mq3/<placa>/status    retida; {"estado":"online"} ao conectar e
//                         {"estado":"offline"} como last will
//
// QoS: o PubSubClient so publica com QoS 0 (sem confirmacao do broker).
// O last will vai com QoS 1. Veja o README para a troca por uma lib com QoS 1.
#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <string.h>
#include <time.h>

#include "cliente_tcp.h"
#include "config.h"
#include "filas.h"
#include "log_serial.h"
#include "tarefas.h"

namespace {

// Fila de pendentes em vetor (so esta tarefa a usa; sem mutex).
// Cheia: descarta a leitura mais antiga; rodada e eventos so saem por ultimo.
class Pendentes {
 public:
  size_t tamanho() const { return _n; }
  const MensagemRede &frente() const { return _itens[0]; }
  uint32_t descartadas() const { return _descartadas; }

  void adicionar(const MensagemRede &mensagem) {
    if (_n == MAX_PENDENTES_REDE) {
      remover(indiceDescartavel());
      _descartadas++;
    }
    _itens[_n++] = mensagem;
  }

  void tirarFrente() { remover(0); }

 private:
  size_t indiceDescartavel() const {
    for (size_t i = 0; i < _n; i++) {
      if (_itens[i].tipo == TipoMensagem::LEITURA) {
        return i;
      }
    }
    return 0;
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
      coube = jsonRodada(json, sizeof(json), m.rodadaId, PLACA, m.arquivo, temHorario ? inicio : nullptr);
      tipoTopico = "rodada";
      retida = true;
      break;
    }
    case TipoMensagem::LEITURA:
      coube = jsonLeitura(json, sizeof(json), m.rodadaId, m.leitura);
      break;
    case TipoMensagem::EVENTO:
      coube = jsonEvento(json, sizeof(json), m.rodadaId, nomeEvento(m.evento), m.tMs);
      tipoTopico = "eventos";
      break;
  }
  if (!coube || !montarTopico(topico, sizeof(topico), PLACA, tipoTopico)) {
    logf("Mensagem MQTT maior que o buffer: descartada");
    return true;  // nao adianta tentar de novo
  }
  return mqtt.publish(topico, json, retida);
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
    // 1. Recebe do armazenamento (espera ate 200 ms: tambem serve de ritmo do laco).
    MensagemRede mensagem;
    if (xQueueReceive(filas->rede, &mensagem, pdMS_TO_TICKS(200)) == pdTRUE) {
      pendentes.adicionar(mensagem);
      while (xQueueReceive(filas->rede, &mensagem, 0) == pdTRUE) {
        pendentes.adicionar(mensagem);
      }
    }
    if (pendentes.descartadas() != descartadasAvisadas) {
      descartadasAvisadas = pendentes.descartadas();
      logf("Rede: %lu leituras antigas descartadas (broker fora do ar; o CSV esta completo)",
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
