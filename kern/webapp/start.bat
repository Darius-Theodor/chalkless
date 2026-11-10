@echo off
rem Chalkless-Übersicht starten (Doppelklick). Fenster offen lassen; schließen beendet die Übersicht.
rem Exit-Codes von server.py: 0 beendet, 3 läuft schon (Browser wird geöffnet), 4 kein freier Port.
chcp 65001 >nul
cd /d "%~dp0..\.."
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python wurde nicht gefunden. Sag im Chat: "Starte die Übersicht" - der Agent hilft dir weiter.
  pause
  exit /b 1
)
%PY% kern\webapp\server.py %*
set "RC=%ERRORLEVEL%"
if "%RC%"=="3" ( "%SystemRoot%\System32\timeout.exe" /t 5 >nul 2>nul & exit /b 0 )
if not "%RC%"=="0" pause
exit /b %RC%
