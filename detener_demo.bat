@echo off
rem ============================================================================
rem  Apaga el motor del Chatbot RAG iniciado con iniciar_demo.bat (o a mano).
rem   1. Cierra los procesos del motor (los que ejecutan "uvicorn api:app", incluida la ventana
rem      "Motor Chatbot RAG"); no se cierra por titulo de ventana para no tocar otras terminales.
rem   2. Comprueba que el puerto 8000 quedo libre.
rem  No toca ningun otro programa que use el puerto 8000.
rem  (Solo ASCII a proposito: asi cmd no se confunde con las tildes.)
rem ============================================================================
setlocal EnableExtensions
title Detener demo - Chatbot RAG

echo.
echo  === Deteniendo el motor del Chatbot RAG ===
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'uvicorn.exe' -or $_.Name -eq 'cmd.exe') -and $_.CommandLine -like '*uvicorn*api:app*' -and $_.ProcessId -ne $PID } | ForEach-Object { taskkill /T /F /PID $_.ProcessId | Out-Null }" >nul 2>&1

set /a INTENTOS=0
:comprobar
set "OCUPA="
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok = $true; try { $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 8000); $l.Start(); $l.Stop() } catch { $ok = $false }; if ($ok) { exit 0 } else { $c = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 } | Select-Object -First 1; if ($c) { $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue; Write-Output ($c.OwningProcess.ToString() + ' ' + $p.ProcessName) } else { Write-Output 'desconocido' }; exit 1 }" > "%TEMP%\puerto8000_demo.txt" 2>nul
if not errorlevel 1 goto :libre
set /a INTENTOS+=1
if %INTENTOS% GEQ 8 goto :ocupado
ping -n 2 127.0.0.1 >nul
goto :comprobar

:libre
echo  Motor detenido. El puerto 8000 quedo libre.
echo.
ping -n 5 127.0.0.1 >nul
exit /b 0

:ocupado
set /p OCUPA=<"%TEMP%\puerto8000_demo.txt"
echo  [AVISO] El puerto 8000 sigue ocupado ^(PID y programa: %OCUPA%^).
echo          No parece ser el motor del chatbot: cierralo a mano desde el Administrador de tareas.
echo.
pause
exit /b 1
