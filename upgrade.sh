#!/bin/bash

PLUGIN="lox-audioserver"
PLUGINPATH="/opt/loxberry/bin/plugins/$PLUGIN"
APPDIR="$PLUGINPATH/app"
LOGFILE="/opt/loxberry/log/plugins/$PLUGIN/upgrade.log"

echo ">>> upgrade.sh für $PLUGIN gestartet" >> "$LOGFILE"

# Alte Konfigurationsdateien migrieren
if [ -f "/opt/loxberry/config/plugins/$PLUGIN/config.json" ]; then
    echo "Konfigurationsdatei gefunden, sichere Kopie..." >> "$LOGFILE"
    cp "/opt/loxberry/config/plugins/$PLUGIN/config.json" \
       "/opt/loxberry/config/plugins/$PLUGIN/config.json.bak" >> "$LOGFILE" 2>&1
fi

# Node-Repo aktualisieren oder neu klonen
if [ -d "$APPDIR" ]; then
    echo "Update des Node-Repos..." >> "$LOGFILE"
    cd "$APPDIR" || exit 1
    if command -v git >/dev/null 2>&1; then
        # Aktuelle und Remote-Version vergleichen
        LOCAL_HASH=$(git rev-parse HEAD)
        REMOTE_HASH=$(git ls-remote origin main | awk '{print $1}')

        if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
            echo "Neue Version gefunden, update..." >> "$LOGFILE"
            git reset --hard >> "$LOGFILE" 2>&1
            git pull --rebase >> "$LOGFILE" 2>&1
            npm install --production >> "$LOGFILE" 2>&1
            npm run build >> "$LOGFILE" 2>&1 || true
        else
            echo "Keine Änderungen im Repo – überspringe npm install/build." >> "$LOGFILE"
        fi
    else
        echo "Git nicht verfügbar – versuche Fallback mit Release-ZIP ..." >> "$LOGFILE"
        wget -O /tmp/lox-audioserver.zip https://github.com/rudyberends/lox-audioserver/archive/refs/heads/main.zip >> "$LOGFILE" 2>&1
        unzip -o /tmp/lox-audioserver.zip -d /tmp >> "$LOGFILE" 2>&1
        rm -rf "$APPDIR"/*
        mv /tmp/lox-audioserver-main/* "$APPDIR"/
        rm -rf /tmp/lox-audioserver-main /tmp/lox-audioserver.zip
        npm install --production >> "$LOGFILE" 2>&1
        npm run build >> "$LOGFILE" 2>&1 || true
    fi
else
    echo "App-Verzeichnis nicht gefunden – klone neu..." >> "$LOGFILE"
    git clone --branch main https://github.com/rudyberends/lox-audioserver.git "$APPDIR" >> "$LOGFILE" 2>&1
    cd "$APPDIR" || exit 1
    npm install --production >> "$LOGFILE" 2>&1
    npm run build >> "$LOGFILE" 2>&1 || true
fi

# Rechte korrigieren
chown -R loxberry:loxberry "$PLUGINPATH"
chmod -R 755 "$PLUGINPATH/bin" "$PLUGINPATH/webfrontend/htmlauth"

echo ">>> upgrade.sh fertig" >> "$LOGFILE"
