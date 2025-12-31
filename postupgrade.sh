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
docker pull ghcr.io/rudyberends/lox-audioserver:latest >> "$LOGFILE" 2>&1

# Container neu starten
if docker ps -a --format '{{.Names}}' | grep -q "^$PLUGIN$"; then
    echo "Starte Container $PLUGIN neu ..." >> "$LOGFILE"
    docker rm -f $PLUGIN >> "$LOGFILE" 2>&1
fi

docker run -d \
  --name $PLUGIN \
  --restart=always \
  -p 7090:7090 \
  -p 7091:7091 \
  -p 7095:7095 \
  -v "$PLUGINPATH/data:/app/data" \
  -v "$PLUGINPATH/logs:/app/logs" \
  ghcr.io/rudyberends/lox-audioserver:testing >> "$LOGFILE" 2>&1

echo ">>> postupgrade.sh fertig" >> "$LOGFILE"
