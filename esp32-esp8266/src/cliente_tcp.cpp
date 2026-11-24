#include "cliente_tcp.h"

#include <errno.h>
#include <fcntl.h>
#include <lwip/netdb.h>
#include <lwip/sockets.h>

ClienteTcp::ClienteTcp(bool forcarIpv6, uint32_t timeoutMs) : _forcarIpv6(forcarIpv6), _timeoutMs(timeoutMs) {}

ClienteTcp::~ClienteTcp() { stop(); }

int ClienteTcp::connect(IPAddress ip, uint16_t porta) { return connect(ip.toString().c_str(), porta); }

int ClienteTcp::connect(const char *host, uint16_t porta) {
  stop();

  // Endereco com ':' e IPv6 literal; nome so vira IPv6 se pedido.
  bool literalIpv6 = strchr(host, ':') != nullptr;
  struct addrinfo dicas = {};
  dicas.ai_family = (_forcarIpv6 || literalIpv6) ? AF_INET6 : AF_UNSPEC;
  dicas.ai_socktype = SOCK_STREAM;
  char portaTexto[8];
  snprintf(portaTexto, sizeof(portaTexto), "%u", porta);
  struct addrinfo *lista = nullptr;
  if (getaddrinfo(host, portaTexto, &dicas, &lista) != 0 || lista == nullptr) {
    log_e("getaddrinfo falhou para %s", host);
    return 0;
  }

  int fd = -1;
  for (struct addrinfo *a = lista; a != nullptr && fd < 0; a = a->ai_next) {
    int candidato = socket(a->ai_family, a->ai_socktype, a->ai_protocol);
    if (candidato < 0) {
      continue;
    }
    fcntl(candidato, F_SETFL, fcntl(candidato, F_GETFL, 0) | O_NONBLOCK);
    int r = lwip_connect(candidato, a->ai_addr, a->ai_addrlen);
    bool ok = false;
    if (r == 0) {
      ok = true;
    } else if (errno == EINPROGRESS) {
      fd_set escrita;
      FD_ZERO(&escrita);
      FD_SET(candidato, &escrita);
      struct timeval tv;
      tv.tv_sec = _timeoutMs / 1000;
      tv.tv_usec = (_timeoutMs % 1000) * 1000;
      if (select(candidato + 1, nullptr, &escrita, nullptr, &tv) > 0) {
        int erro = 0;
        socklen_t tamanho = sizeof(erro);
        ok = getsockopt(candidato, SOL_SOCKET, SO_ERROR, &erro, &tamanho) == 0 && erro == 0;
      }
    }
    if (ok) {
      fd = candidato;
    } else {
      close(candidato);
    }
  }
  freeaddrinfo(lista);
  if (fd < 0) {
    return 0;
  }

  // Volta ao modo bloqueante, com timeout nas leituras e escritas.
  fcntl(fd, F_SETFL, fcntl(fd, F_GETFL, 0) & ~O_NONBLOCK);
  struct timeval tv;
  tv.tv_sec = _timeoutMs / 1000;
  tv.tv_usec = (_timeoutMs % 1000) * 1000;
  setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
  setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
  int ligado = 1;
  setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &ligado, sizeof(ligado));
  _fd = fd;
  return 1;
}

size_t ClienteTcp::write(uint8_t byte) { return write(&byte, 1); }

size_t ClienteTcp::write(const uint8_t *dados, size_t tamanho) {
  if (_fd < 0) {
    return 0;
  }
  size_t enviados = 0;
  while (enviados < tamanho) {
    int n = send(_fd, dados + enviados, tamanho - enviados, 0);
    if (n <= 0) {
      stop();
      return enviados;
    }
    enviados += n;
  }
  return enviados;
}

int ClienteTcp::available() {
  if (_fd < 0) {
    return 0;
  }
  int pendentes = 0;
  if (lwip_ioctl(_fd, FIONREAD, &pendentes) < 0) {
    return 0;
  }
  return pendentes + (_byteAdiantado >= 0 ? 1 : 0);
}

int ClienteTcp::read() {
  uint8_t byte;
  return read(&byte, 1) == 1 ? byte : -1;
}

int ClienteTcp::read(uint8_t *buffer, size_t tamanho) {
  if (_fd < 0 || tamanho == 0) {
    return -1;
  }
  size_t lidos = 0;
  if (_byteAdiantado >= 0) {
    buffer[lidos++] = static_cast<uint8_t>(_byteAdiantado);
    _byteAdiantado = -1;
    if (tamanho == 1) {
      return 1;
    }
  }
  // Nao bloqueia esperando dados que o PubSubClient nao pediu.
  int pendentes = 0;
  lwip_ioctl(_fd, FIONREAD, &pendentes);
  if (pendentes <= 0) {
    return lidos > 0 ? static_cast<int>(lidos) : -1;
  }
  int n = recv(_fd, buffer + lidos, tamanho - lidos, 0);
  if (n < 0) {
    return lidos > 0 ? static_cast<int>(lidos) : -1;
  }
  if (n == 0) {  // o broker fechou a conexao
    stop();
    return lidos > 0 ? static_cast<int>(lidos) : -1;
  }
  return static_cast<int>(lidos) + n;
}

int ClienteTcp::peek() {
  if (_byteAdiantado < 0) {
    uint8_t byte;
    if (_fd < 0 || available() <= 0 || recv(_fd, &byte, 1, 0) != 1) {
      return -1;
    }
    _byteAdiantado = byte;
  }
  return _byteAdiantado;
}

void ClienteTcp::stop() {
  if (_fd >= 0) {
    close(_fd);
    _fd = -1;
  }
  _byteAdiantado = -1;
}

uint8_t ClienteTcp::connected() {
  if (_fd < 0) {
    return 0;
  }
  if (available() > 0) {
    return 1;
  }
  // Sem dados pendentes, confere se o outro lado fechou.
  uint8_t byte;
  int n = recv(_fd, &byte, 1, MSG_PEEK | MSG_DONTWAIT);
  if (n == 0) {
    stop();
    return 0;
  }
  if (n < 0 && errno != EWOULDBLOCK && errno != EAGAIN) {
    stop();
    return 0;
  }
  return 1;
}
