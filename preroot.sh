#!/bin/bash
# preroot.sh – Stoppt alle Dienste, Timer und Container vor der Deinstallation

PLUGIN="lox-audioserver"
PLUGIN_MASS="music-assistant"

echo "### [preroot] Stoppe systemd Timer und Services ..."

# Timer stoppen
systemctl stop lox-audioserver-cover.timer 2>/dev/null || true
systemctl disable lox-audioserver-cover.timer 2>/dev/null || true

# Service stoppen
systemctl stop lox-audioserver-cover.service 2>/dev/null || true

echo "### [preroot] Stoppe Docker-Container ..."

# Lox-Audioserver Container
docker rm -f "$PLUGIN" 2>/dev/null || true

# Music Assistant Container
docker rm -f "$PLUGIN_MASS" 2>/dev/null || true

exit 0
