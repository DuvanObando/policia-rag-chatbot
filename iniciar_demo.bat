@echo off
rem ============================================================================
rem  Inicia la demo del Chatbot RAG (Ley 1801 de 2016).
rem   1. Comprueba que el puerto 8000 este libre.
rem   2. Arranca el motor (entorno virtual de engine\ + uvicorn) en una ventana
rem      propia titulada "Motor Chatbot RAG". Si esa ventana se cierra, el motor se apaga.
rem   3. Espera a que /health responda "listo": true.
rem   4. Abre en Chrome /docs (Swagger) y la pagina de diagramas de GitHub Pages.
rem  Para apagar el motor: detener_demo.bat
rem  (Solo ASCII a proposito: asi cmd no se confunde con las tildes.)
rem ============================================================================
setlocal EnableExtensions
title Iniciar demo - Chatbot RAG
cd /d "%~dp0"

set "URL_DOCS=http://localhost:8000/docs"
set "URL_DIAGRAMAS=https://duvanobando.github.io/policia-rag-chatbot/diagramas/index.html"
set "MAX_ESPERA=240"

echo.
echo  === Demo Chatbot RAG - Ley 1801 de 2016 ===
echo.

if not exist "engine\.venv\Scripts\activate.bat" (
  echo  [ERROR] No se encontro el entorno virtual en engine\.venv
  echo          Hay que crearlo e instalar las dependencias ^(ver el README, seccion "Motor RAG"^).
  goto :error
)
if not exist ".env" (
  echo  [AVISO] No se encontro el archivo .env en la raiz del repo: sin claves el motor no quedara listo.
)

rem --- 1. puerto 8000 ocupado?
set "OCUPA="
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok = $true; try { $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 8000); $l.Start(); $l.Stop() } catch { $ok = $false }; if ($ok) { exit 0 } else { $c = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 } | Select-Object -First 1; if ($c) { $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue; Write-Output ($c.OwningProcess.ToString() + ' ' + $p.ProcessName) } else { Write-Output 'desconocido' }; exit 1 }" > "%TEMP%\puerto8000_demo.txt" 2>nul
if errorlevel 1 (
  set /p OCUPA=<"%TEMP%\puerto8000_demo.txt"
  goto :ocupado
)

rem --- 2. arrancar el motor en su propia ventana
echo  Iniciando el motor en la ventana "Motor Chatbot RAG"...
echo  (no cierres esa ventana durante la demo: si la cierras, el motor se apaga)
set "PYTHONIOENCODING=utf-8"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
start "Motor Chatbot RAG" /D "%~dp0engine" cmd /k "call .venv\Scripts\activate.bat && uvicorn api:app --port 8000"

rem --- 3. esperar a que /health diga listo: true
echo.
set /a ESPERA=0
:esperar
ping -n 3 127.0.0.1 >nul
set /a ESPERA+=2
curl.exe -s -m 3 http://127.0.0.1:8000/health 2>nul | findstr /R /C:"listo.:true" >nul
if not errorlevel 1 goto :listo
rem Pasados 12 s, si ya no hay ningun proceso del motor, se cayo (no se usa el titulo de la ventana: no es fiable)
if %ESPERA% GEQ 12 powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'uvicorn.exe') -and $_.CommandLine -like '*uvicorn*api:app*' }) { exit 0 } else { exit 1 }" >nul 2>&1
if %ESPERA% GEQ 12 if errorlevel 1 goto :motor_caido
if %ESPERA% GEQ %MAX_ESPERA% goto :sin_respuesta
echo  Cargando motor, espera... ^(%ESPERA% s^)
goto :esperar

:listo
echo.
echo  Motor listo ^(%ESPERA% s^). Abriendo las paginas en Chrome...
set "CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not defined CHROME goto :sin_chrome
start "" "%CHROME%" "%URL_DOCS%" "%URL_DIAGRAMAS%"
goto :fin_ok

:sin_chrome
echo  [AVISO] No se encontro Chrome: se abren las paginas con el navegador predeterminado.
start "" "%URL_DOCS%"
start "" "%URL_DIAGRAMAS%"

:fin_ok
echo.
echo  ----------------------------------------------------------------------
echo   Listo. Paginas abiertas:
echo     - %URL_DOCS%
echo     - %URL_DIAGRAMAS%
echo.
echo   IMPORTANTE: no cierres la ventana "Motor Chatbot RAG" ^(apaga el motor^).
echo   Para apagarlo: acceso directo "Detener demo Chatbot" o detener_demo.bat
echo  ----------------------------------------------------------------------
ping -n 9 127.0.0.1 >nul
exit /b 0

:ocupado
echo  ----------------------------------------------------------------------
echo   [ATENCION] El puerto 8000 ya esta ocupado ^(PID y programa: %OCUPA%^).
echo.
curl.exe -s -m 3 http://127.0.0.1:8000/health 2>nul | findstr /R /C:"listo.:true" >nul
if not errorlevel 1 goto :ya_corre
echo   Parece que otro programa usa ese puerto, o hay un motor a medias.
echo   - Prueba primero "Detener demo Chatbot" ^(detener_demo.bat^) y vuelve a iniciar.
echo   - Si sigue ocupado, cierra el programa de arriba desde el Administrador de tareas.
goto :ocupado_fin
:ya_corre
echo   Ya hay un motor del chatbot corriendo y listo: no hace falta iniciarlo otra vez.
echo   - Abre %URL_DOCS%
echo   - Para reiniciarlo: "Detener demo Chatbot" y luego "Iniciar demo Chatbot".
:ocupado_fin
echo  ----------------------------------------------------------------------
echo.
pause
exit /b 1

:motor_caido
echo.
echo  [ERROR] El motor se detuvo antes de quedar listo.
echo          Mira el mensaje de error en la ventana "Motor Chatbot RAG" ^(se queda abierta^).
goto :error

:sin_respuesta
echo.
echo  [ERROR] El motor no quedo listo en %MAX_ESPERA% s.
echo          Mira la ventana "Motor Chatbot RAG": ahi aparece el motivo ^(p. ej. falta una clave en .env^).
echo          Tambien puedes abrir http://localhost:8000/health y leer el campo "error".

:error
echo.
pause
exit /b 1
