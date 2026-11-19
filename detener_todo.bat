@echo off
rem ============================================================================
rem  Apaga TODO el Chatbot RAG iniciado con iniciar_todo.bat (o a mano):
rem   - el motor: procesos que ejecutan "uvicorn api:app";
rem   - el backend: procesos que ejecutan "node src/server.js" DESDE la carpeta backend de este repo;
rem   - el frontend: el "vite" de la carpeta frontend de este repo.
rem  No cierra otras terminales ni otros proyectos de Node. Comprueba que 8000, 4000 y 5173 queden libres.
rem  (Solo ASCII a proposito: asi cmd no se confunde con las tildes.)
rem ============================================================================
setlocal EnableExtensions
title Detener todo - Chatbot RAG
cd /d "%~dp0"

echo.
echo  === Deteniendo motor, backend y frontend del Chatbot RAG ===
echo.

set "REPO=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$repo = $env:REPO.TrimEnd('\'); Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -and ( ($_.CommandLine -like '*uvicorn*api:app*') -or ($_.Name -eq 'node.exe' -and ($_.CommandLine -like '*src/server.js*' -or $_.CommandLine -like '*src\server.js*') ) -or ($_.CommandLine -like ('*' + $repo + '\frontend*') -and $_.CommandLine -like '*vite*') -or ($_.Name -eq 'cmd.exe' -and ($_.CommandLine -like '*npm run start*' -or $_.CommandLine -like '*npm run dev*' -or $_.CommandLine -like '*uvicorn api:app*')) ) } | ForEach-Object { taskkill /T /F /PID $_.ProcessId 2>$null | Out-Null }" >nul 2>&1

ping -n 3 127.0.0.1 >nul
set "OCUPADOS="
for %%P in (8000 4000 5173) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, %%P); $l.Start(); $l.Stop(); exit 0 } catch { exit 1 }" >nul 2>&1
  if errorlevel 1 call set "OCUPADOS=%%OCUPADOS%% %%P"
)
if defined OCUPADOS goto :ocupados
echo  Todo detenido. Los puertos 8000, 4000 y 5173 quedaron libres.
echo.
ping -n 5 127.0.0.1 >nul
exit /b 0

:ocupados
echo  [AVISO] Siguen ocupados los puertos:%OCUPADOS%
echo          Puede ser otro programa: cierralo desde el Administrador de tareas.
echo.
pause
exit /b 1
