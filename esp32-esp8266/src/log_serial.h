// Saida serial protegida por mutex. Sensores e rede escrevem na serial; sem
// o mutex, uma linha podia sair misturada com outra.
#pragma once

void iniciarLogSerial();
// Escreve uma linha inteira de uma vez.
void escreverLinhaSerial(const char *linha);
// printf para a serial, uma linha por chamada (ate 256 caracteres).
void logf(const char *formato, ...) __attribute__((format(printf, 1, 2)));
