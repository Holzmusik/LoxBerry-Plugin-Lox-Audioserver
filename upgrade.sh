#!/bin/bash

PLUGIN="lox-audioserver"
PLUGINPATH="/opt/loxberry/bin/plugins/$PLUGIN"
APPDIR="$PLUGINPATH/app"
LOGFILE="/opt/loxberry/log/plugins/$PLUGIN/upgrade.log"
CONFIGFILE="/opt/loxberry/config/plugins/$PLUGIN/version.txt"

echo ">>> upgrade.sh für $PLUGIN gestartet" >> "$LOGFILE"

# Gewünschte Version aus Config lesen (Default: latest)
if [ -f "$CONFIGFILE" ]; then
    SELECTED_VERSION=$(cat "$CONFIGFILE")
else
    SELECTED_VERSION="latest"
fi
echo "Verwende Version: $SELECTED_VERSION" >> "$LOGFILE"

# Alte Konfigurationsdateien migrieren
if [ -f "/opt/loxberry/config/plugins/$PLUGIN/config.json" ]; then
    echo "Konfigurationsdatei gefunden, sichere Kopie..." >> "$LOGFILE"
    cp "/opt/loxberry/config/plugins/$PLUGIN/config.json" \
       "/opt/loxberry/config/plugins/$PLUGIN/config.json.bak" >> "$LOGFILE" 2>&1
fi

# Alten Container entfernen, falls vorhanden
if docker ps -a --format '{{.Names}}' | grep -q "^$PLUGIN$"; then
    echo "Entferne alten Container $PLUGIN ..." >> "$LOGFILE"
    docker rm -f $PLUGIN >> "$LOGFILE" 2>&1
fi

# Neues Image ziehen
echo "Ziehe Docker-Image ghcr.io/rudyberends/lox-audioserver:$SELECTED_VERSION ..." >> "$LOGFILE"
docker pull ghcr.io/rudyberends/lox-audioserver:$SELECTED_VERSION >> "$LOGFILE" 2>&1

# Container starten
echo "Starte neuen Container mit Version $SELECTED_VERSION ..." >> "$LOGFILE"
docker run -d \
  --name $PLUGIN \
  --restart=always \
  -p 7090:7090 \
  -p 7091:7091 \
  -p 7095:7095 \
  -v "$APPDIR/data:/app/data" \
  -v "$APPDIR/logs:/app/logs" \
  ghcr.io/rudyberends/lox-audioserver:$SELECTED_VERSION >> "$LOGFILE" 2>&1

# Rechte korrigieren
chown -R loxberry:loxberry "$PLUGINPATH"
chmod -R 755 "$PLUGINPATH/bin" "$PLUGINPATH/webfrontend/htmlauth"

echo ">>> upgrade.sh fertig" >> "$LOGFILE"
