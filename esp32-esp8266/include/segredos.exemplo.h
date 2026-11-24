// Modelo dos segredos do firmware. Copie para include/segredos.h (que o
// git ignora) e preencha com a rede e o broker da coleta:
//
//   cp include/segredos.exemplo.h include/segredos.h
//
// Sem segredos.h o firmware compila com estes valores de exemplo e nao
// conecta em rede nenhuma; o CSV e a serial continuam funcionando.
#pragma once

#define WIFI_SSID "nome-da-rede"
#define WIFI_SENHA "senha-da-rede"

// Endereco do broker MQTT (Mosquitto do docker-compose, porta 1883).
// Pode ser um nome ("broker.local"), um IPv4 ("192.168.0.10") ou um
// IPv6 ("2804:abcd::10"). Endereco com ':' usa IPv6 automaticamente.
#define MQTT_HOST "192.168.0.10"
#define MQTT_PORTA 1883
// Mosquitto da coleta aceita conexao anonima: deixe vazio.
#define MQTT_USUARIO ""
#define MQTT_SENHA ""
// 1 forca IPv6 tambem quando MQTT_HOST e um nome (procura o registro AAAA).
#define MQTT_USAR_IPV6 0

// Nome da placa nos topicos mq3/<placa>/... So letras, numeros e hifen (vai
// no JSON sem escape). Use um nome diferente do da
// ponte serial (placa01) se as duas publicarem ao mesmo tempo.
#define PLACA "esp32-01"

// Rotulo padrao das rodadas desta placa. Vazio = null no banco (a placa nao
// sabe o que foi soprado nem por quem). Use as condicoes de
// applications/coleta/casos.py (ex.: "perfume", "drink") e um id anonimo.
#define CASO_PADRAO ""
#define PARTICIPANTE_PADRAO ""
