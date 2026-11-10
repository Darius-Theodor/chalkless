#!/bin/sh
# Chalkless-Übersicht starten (Doppelklick im Finder). Fenster offen lassen; schließen beendet die Übersicht.
# Exit-Codes von server.py: 0 beendet, 3 läuft schon (Browser wird geöffnet), 4 kein freier Port.
cd "$(dirname "$0")/../.." || exit 1
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo 'Python wurde nicht gefunden. Sag im Chat: "Starte die Übersicht" - der Agent hilft dir weiter.'
  read -r _
  exit 1
fi
"$PY" kern/webapp/server.py "$@"
rc=$?
if [ "$rc" -eq 3 ]; then sleep 5; exit 0; fi
if [ "$rc" -ne 0 ]; then echo '(Eingabetaste schließt dieses Fenster.)'; read -r _; fi
exit "$rc"
