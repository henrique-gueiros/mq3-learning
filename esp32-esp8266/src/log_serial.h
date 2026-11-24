// Saida serial protegida por mutex. Varias tarefas escrevem na serial; sem
// o mutex, uma linha CSV_LINHA podia sair misturada com outra mensagem e a
// ponte (applications/coleta/ponte.py) perderia a leitura.
#pragma once

void iniciarLogSerial();
// Escreve uma linha inteira de uma vez.
void escreverLinhaSerial(const char *linha);
// printf para a serial, uma linha por chamada (ate 256 caracteres).
void logf(const char *formato, ...) __attribute__((format(printf, 1, 2)));
