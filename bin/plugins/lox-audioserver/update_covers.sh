#!/bin/bash

PLUGIN=lox-audioserver
BASE="http://127.0.0.1/admin/plugins/$PLUGIN/status.cgi?zone="

zone=1

while true; do
    # Prüfen, ob Zone existiert
    STATUS=$(curl -s "$BASE$zone")

    # Wenn leer oder kein gültiges JSON → keine weitere Zone
    echo "$STATUS" | jq . >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        break
    fi

    # Player-CGI triggern, damit PNG aktualisiert wird
    curl -s "http://127.0.0.1/admin/plugins/$PLUGIN/player.cgi?zone=$zone" >/dev/null

    zone=$((zone+1))
done
