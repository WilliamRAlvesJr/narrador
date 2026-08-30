@echo off
rem Liga e desliga a narracao automatica das respostas do Claude (hook Stop).
rem O arquivo sentinela fica na pasta de dados, fora do plugin.
setlocal
if "%NARRADOR_HOME%"=="" (set "DADOS=%USERPROFILE%\.claude\narrador") else (set "DADOS=%NARRADOR_HOME%")
set "MARCA=%DADOS%\narrar-respostas"

if /I "%~1"=="on" (
  if not exist "%DADOS%" mkdir "%DADOS%"
  type nul > "%MARCA%"
  echo Narracao automatica LIGADA.
  exit /b 0
)
if /I "%~1"=="off" (
  if exist "%MARCA%" del "%MARCA%"
  echo Narracao automatica DESLIGADA.
  exit /b 0
)
if exist "%MARCA%" (echo Narracao automatica: LIGADA) else (echo Narracao automatica: DESLIGADA)
echo Uso: narrar.cmd [on^|off]
echo Sentinela: %MARCA%
