// Cliente TCP para o PubSubClient que aceita IPv4 e IPv6.
//
// O WiFiClient do core arduino-esp32 2.0.x so abre sockets IPv4 (AF_INET),
// entao nao alcanca um broker por endereco IPv6. Este cliente usa
// getaddrinfo + sockets do lwIP e deixa o sistema escolher a familia
// (ou forca IPv6). Hipotese ainda nao testada em hardware: ver README.
#pragma once

#include <Arduino.h>
#include <Client.h>

class ClienteTcp : public Client {
 public:
  // forcarIpv6: procura so enderecos IPv6 (registro AAAA para nomes).
  explicit ClienteTcp(bool forcarIpv6 = false, uint32_t timeoutMs = 5000);
  ~ClienteTcp() override;

  int connect(IPAddress ip, uint16_t porta) override;
  int connect(const char *host, uint16_t porta) override;
  size_t write(uint8_t byte) override;
  size_t write(const uint8_t *dados, size_t tamanho) override;
  int available() override;
  int read() override;
  int read(uint8_t *buffer, size_t tamanho) override;
  int peek() override;
  void flush() override {}
  void stop() override;
  uint8_t connected() override;
  operator bool() override { return connected(); }

 private:
  int _fd = -1;
  bool _forcarIpv6;
  uint32_t _timeoutMs;
  int _byteAdiantado = -1;  // para o peek()
};
