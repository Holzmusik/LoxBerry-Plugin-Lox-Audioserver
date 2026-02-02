#!/bin/bash

PLUGIN="lox-audioserver"
PLUGINPATH="/opt/loxberry/bin/plugins/$PLUGIN"
LOGFILE="/opt/loxberry/log/plugins/$PLUGIN/postupgrade.log"

echo ">>> postupgrade.sh für $PLUGIN gestartet" >> "$LOGFILE"

# Rechte korrigieren
chown -R loxberry:loxberry "$PLUGINPATH"
chmod -R 755 "$PLUGINPATH/bin" "$PLUGINPATH/webfrontend/htmlauth"

# Docker prüfen
if ! command -v docker >/dev/null 2>&1; then
    echo "FEHLER: Docker ist nicht installiert! Bitte Docker nachinstallieren." >> "$LOGFILE"
    exit 1
fi

# Container aktualisieren
echo "Ziehe aktuelles Docker-Image ..." >> "$LOGFILE"
docker pull ghcr.io/lox-audioserver/lox-audioserver:dev >> "$LOGFILE" 2>&1

# Container neu starten
if docker ps -a --format '{{.Names}}' | grep -q "^$PLUGIN$"; then
    echo "Starte Container $PLUGIN neu ..." >> "$LOGFILE"
    docker rm -f $PLUGIN >> "$LOGFILE" 2>&1
fi

docker run -d \
  --name $PLUGIN \
  --restart=always \
  --network host \
  -v "$PLUGINPATH/data:/app/data" \
  -v "$PLUGINPATH/logs:/app/logs" \
  ghcr.io/lox-audioserver/lox-audioserver:dev >> "$LOGFILE" 2>&1

echo ">>> postupgrade.sh fertig" >> "$LOGFILE"
