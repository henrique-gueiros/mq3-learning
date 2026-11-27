# Coleta no Windows (PowerShell)

Roteiro da rodada `clean` (90 s) e `mouthwash` (4 min). Abra o PowerShell na raiz do repositório:

```powershell
Set-Location "C:\Sistemas embarcados\Projeto embarcados\mq3-learning"
```

Neste PowerShell o separador de comandos é `;`. `&&` não funciona. Caminhos de script precisam do operador `&` e de `.\` ou do caminho completo. O lançador `py` não está instalado neste computador.

## 0. Ambiente Python

O `ml\.venv` desta máquina já é Windows, Python 3.11.9, com as dependências da coleta. Não crie `applications\ml\.venv`.

Na raiz:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
& ".\ml\.venv\Scripts\Activate.ps1"
```

Docker Desktop aberto. O PlatformIO está em:

```powershell
$PIO = "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe"
```

## 1. Gravar o firmware de coleta (uma vez)

A worktree do commit `d61e301` ficou dentro do repositório, porque o `git worktree add` rodou a partir de `applications`:

`mq3-learning\mq3-firmware-coleta`

Com a placa no USB, na raiz:

```powershell
Set-Location ".\mq3-firmware-coleta\esp32-esp8266"
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -t upload
Set-Location "C:\Sistemas embarcados\Projeto embarcados\mq3-learning"
```

Feche o monitor serial antes do upload e antes da ponte. A porta USB aceita um programa por vez.

## 2. Preparar o computador (a cada dia)

Na raiz, com o Docker Desktop aberto:

```powershell
docker compose up -d
Set-ExecutionPolicy -Scope Process Bypass
& ".\ml\.venv\Scripts\Activate.ps1"
Set-Location ".\applications"
```

Descubra a porta da placa:

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
```

Se aparecerem várias, desconecte a placa, rode de novo e veja qual sumiu. Troque `COM3` pela porta que restou:

```powershell
$PORTA = "COM3"
```

Se a placa não aparecer em nenhuma porta, falta o driver USB, normalmente o CP210x da Silicon Labs.

Espere 5 min com a placa ligada antes da primeira rodada.

## 3. Sopro sem álcool (uma rodada por pessoa, 90 s)

Ainda em `applications`, com o ambiente ativo:

```powershell
python -m coleta.ponte --porta $PORTA --caso clean --participante p01 --duracao 90
python -m coleta.ponte --porta $PORTA --caso clean --participante p02 --duracao 90
python -m coleta.ponte --porta $PORTA --caso clean --participante p03 --duracao 90
python -m coleta.ponte --porta $PORTA --caso clean --participante p04 --duracao 90
```

Em cada rodada:

1. Espere 20 s.
2. Faça 3 sopros de cerca de 4 s, a 10 cm do sensor, com cerca de 20 s entre eles.
3. Em cada sopro: Enter quando começar, `f` + Enter quando parar.

## 4. Enxaguante (uma rodada por pessoa, 4 min)

```powershell
python -m coleta.ponte --porta $PORTA --caso mouthwash --participante p01 --duracao 240
python -m coleta.ponte --porta $PORTA --caso mouthwash --participante p02 --duracao 240
python -m coleta.ponte --porta $PORTA --caso mouthwash --participante p03 --duracao 240
```

Em cada rodada:

1. Espere 20 s.
2. A pessoa bochecha 20 ml por 30 s e cospe longe da placa.
3. Sopros logo depois, com 1 min e com 3 min depois do bochecho. Em cada um: Enter quando começar, `f` + Enter quando parar.

Antes da próxima pessoa, deixe 1 min com a janela aberta. Use o mesmo código (`p01`…) para a mesma pessoa nas duas rodadas.

## 5. Conferir o que foi gravado

Em `applications`:

```powershell
Get-ChildItem "..\ml\data\raw\sessions" | Sort-Object LastWriteTime -Descending | Select-Object -First 10
Get-Content "..\ml\data\raw\attempts.csv" -Tail 20
```

## 6. Voltar a placa ao firmware atual

Na raiz:

```powershell
Set-Location ".\esp32-esp8266"
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -t upload
```
