#!/bin/bash

APPDIR="/opt/loxberry/bin/plugins/lox-audioserver/app"
LOGFILE="/opt/loxberry/log/plugins/lox-audioserver/upgrade.log"

echo ">>> Upgrade gestartet $(date)" >> "$LOGFILE"

cd "$APPDIR" || exit 1

# Abhängigkeiten aktualisieren
npm install --no-optional >> "$LOGFILE" 2>&1

# Neu bauen, falls build-Skript existiert
if grep -q "\"build\"" package.json; then
  npm run build >> "$LOGFILE" 2>&1
fi

# Service neu starten
systemctl restart lox-audioserver

echo ">>> Upgrade abgeschlossen $(date)" >> "$LOGFILE"
