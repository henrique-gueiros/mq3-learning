# Detector de álcool com MQ-3 — firmware ESP32

Firmware PlatformIO do detector de álcool. A parte de machine learning fica em `ml/`.

Na partida, o programa mede o ar limpo no pino analógico 34 e guarda essa média como referência. No loop, lê o MQ-3 de novo: se o valor passar da referência mais uma margem de 80, acende o LED do pino 2 e escreve `ALCOOL` no monitor serial (115200 baud). Caso contrário, apaga o LED.

A mesma linha mostra `ppm`, estimado pela curva do datasheet do MQ-3 (0,4 mg/L ≈ 200 ppm). A medição da partida entra como ar limpo. O resistor de carga se cancela; a tensão de teste usada na conta é 5 V, como no datasheet. O ADC da ESP32 satura por volta de 3,1 V, então uma saída analógica em 5 V não cobre a escala inteira do sensor.

Placa configurada: `esp32dev`, framework Arduino.

```bash
cd firmware
pio run          # compila
pio run -t upload
pio device monitor
```
