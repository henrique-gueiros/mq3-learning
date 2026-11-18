# Esquemáticos

| Arquivo | O quê |
| --- | --- |
| `esquematico-circuito.png` | Ligação da ESP32 com os sensores |
| `montagem-fisica.jpg` | Foto da montagem na protoboard |

| Componente | Pino da ESP32 | Alimentação |
| --- | --- | --- |
| MQ-3 (AOUT) | GPIO 34 | 5 V |
| MQ-135 (AOUT) | GPIO 35 | 5 V |
| DHT11 (DATA) | GPIO 4 | 3V3 |
| LED | GPIO 2 | — |

A tensão de alimentação do MQ-3 fica em ~4,8 V desde 10/11/2026. O ADC da ESP32
satura perto de 3,1 V (ver `esp32-esp8266/README.md`).

Falta o arquivo-fonte do esquemático na ferramenta usada (Wokwi, Fritzing, KiCad...):
quem desenhou o esquemático deve acrescentá-lo nesta pasta.
