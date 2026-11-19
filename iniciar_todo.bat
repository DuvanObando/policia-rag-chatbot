@echo off
rem ============================================================================
rem  Inicia TODO el Chatbot RAG: motor (FastAPI), backend (Express) y frontend (Vite).
rem   1. Comprueba que existan engine\.venv, backend\node_modules y frontend\node_modules.
rem   2. Comprueba que los puertos 8000, 4000 y 5173 esten libres.
rem   3. Abre tres ventanas: "Motor Chatbot RAG", "Backend Chatbot RAG" y "Frontend Chatbot RAG".
rem   4. Espera a que el motor diga "listo": true y a que el frontend responda.
rem   5. Abre el navegador en http://localhost:5173
rem  Para apagar todo: detener_todo.bat
rem  Instalacion previa: docs\guia-companeros\traspaso-santiago-castro.md
rem  (Solo ASCII a proposito: asi cmd no se confunde con las tildes.)
rem ============================================================================
setlocal EnableExtensions
title Iniciar todo - Chatbot RAG
cd /d "%~dp0"

set "URL_APP=http://localhost:5173"
set "MAX_ESPERA=240"

echo.
echo  === Chatbot RAG: motor + backend + frontend ===
echo.

if not exist "engine\.venv\Scripts\activate.bat" (
  echo  [ERROR] Falta el entorno virtual engine\.venv ^(ver la guia de traspaso, paso 3^).
  goto :error
)
if not exist "backend\node_modules" (
  echo  [ERROR] Falta backend\node_modules: corre "npm install" dentro de backend ^(paso 5^).
  goto :error
)
if not exist "frontend\node_modules" (
  echo  [ERROR] Falta frontend\node_modules: corre "npm install" dentro de frontend ^(paso 5^).
  goto :error
)
if not exist ".env" (
  echo  [AVISO] No hay .env en la raiz: sin claves el motor no quedara listo.
)

rem --- puertos libres?
for %%P in (8000 4000 5173) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, %%P); $l.Start(); $l.Stop(); exit 0 } catch { exit 1 }" >nul 2>&1
  if errorlevel 1 (
    echo  [ATENCION] El puerto %%P ya esta ocupado. Corre detener_todo.bat y vuelve a intentar.
    goto :error
  )
)

set "PYTHONIOENCODING=utf-8"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
echo  Abriendo las ventanas del motor, el backend y el frontend...
echo  (no las cierres durante la demo: si cierras una, ese servicio se apaga)
start "Motor Chatbot RAG" /D "%~dp0engine" cmd /k "call .venv\Scripts\activate.bat && uvicorn api:app --port 8000"
start "Backend Chatbot RAG" /D "%~dp0backend" cmd /k "npm run start"
start "Frontend Chatbot RAG" /D "%~dp0frontend" cmd /k "npm run dev"

rem --- esperar al motor
echo.
set /a ESPERA=0
:esperar
ping -n 3 127.0.0.1 >nul
set /a ESPERA+=2
curl.exe -s -m 3 http://127.0.0.1:8000/health 2>nul | findstr /R /C:"listo.:true" >nul
if not errorlevel 1 goto :motor_listo
if %ESPERA% GEQ 12 powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'uvicorn.exe') -and $_.CommandLine -like '*uvicorn*api:app*' }) { exit 0 } else { exit 1 }" >nul 2>&1
if %ESPERA% GEQ 12 if errorlevel 1 goto :motor_caido
if %ESPERA% GEQ %MAX_ESPERA% goto :sin_respuesta
echo  Cargando motor, espera... ^(%ESPERA% s^)
goto :esperar

:motor_listo
echo  Motor listo ^(%ESPERA% s^). Esperando el backend y el frontend...
set /a ESPERA2=0
:esperar_web
curl.exe -s -m 3 http://127.0.0.1:4000/health 2>nul | findstr /R /C:"listo" >nul
if errorlevel 1 goto :web_no
curl.exe -s -m 3 -o nul http://localhost:5173 2>nul
if errorlevel 1 goto :web_no
goto :abrir
:web_no
set /a ESPERA2+=2
if %ESPERA2% GEQ 60 goto :web_lento
ping -n 3 127.0.0.1 >nul
goto :esperar_web

:web_lento
echo  [AVISO] El backend o el frontend no respondieron en 60 s. Mira sus ventanas.

:abrir
echo.
echo  Abriendo %URL_APP% ...
start "" "%URL_APP%"
echo.
echo  ----------------------------------------------------------------------
echo   Listo: %URL_APP%
echo   - Usuario: boton "Entrar como usuario".
echo   - Administrador: la ADMIN_CLAVE de tu .env.
echo   No cierres las tres ventanas. Para apagar todo: detener_todo.bat
echo  ----------------------------------------------------------------------
ping -n 9 127.0.0.1 >nul
exit /b 0

:motor_caido
echo.
echo  [ERROR] El motor se detuvo antes de quedar listo: mira la ventana "Motor Chatbot RAG".
goto :error

:sin_respuesta
echo.
echo  [ERROR] El motor no quedo listo en %MAX_ESPERA% s. Abre http://localhost:8000/health y lee "error".

:error
echo.
pause
exit /b 1
