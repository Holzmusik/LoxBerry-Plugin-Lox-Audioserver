#!/bin/bash
# postroot.sh – Native Installation des Lox-Audioservers (ohne Docker)

set -e

echo "### Lox-Audioserver postroot.sh (native) startet ..."

PLUGINNAME=lox-audioserver
LBHOMEDIR=/opt/loxberry
APPDIR=$LBHOMEDIR/bin/plugins/$PLUGINNAME
WEBDIR=$LBHOMEDIR/webfrontend/html/plugins/$PLUGINNAME
GITURL="https://github.com/rudyberends/lox-audioserver.git"
GITBRANCH="4.x-branch"
SERVICEFILE=/etc/systemd/system/lox-audioserver.service

# ------------------------------------------------------------
# Abhängigkeiten
# ------------------------------------------------------------
echo "Installiere System-Abhängigkeiten ..."
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    ffmpeg \
    libasound2

# ------------------------------------------------------------
# Verzeichnisse
# ------------------------------------------------------------
echo "Erstelle Daten- und Log-Verzeichnisse ..."
mkdir -p "$APPDIR/data" "$APPDIR/logs"
chown -R loxberry:loxberry "$APPDIR/data" "$APPDIR/logs"

echo "Erstelle Cover-Verzeichnis im Webfrontend ..."
mkdir -p "$WEBDIR/covers"
chown -R loxberry:loxberry "$WEBDIR/covers"

# ------------------------------------------------------------
# Repository
# ------------------------------------------------------------
if [ ! -d "$APPDIR/repo" ]; then
    echo "Klonen des Repositories ($GITBRANCH) ..."
    git clone --branch "$GITBRANCH" "$GITURL" "$APPDIR/repo"
else
    echo "Aktualisiere bestehendes Repository ..."
    cd "$APPDIR/repo"
    git fetch
    git reset --hard origin/$GITBRANCH
fi

# ------------------------------------------------------------
# Python Virtual Environment
# ------------------------------------------------------------
echo "Erstelle Python Virtual Environment ..."
cd "$APPDIR"
python3 -m venv venv
source venv/bin/activate

echo "Installiere Python-Abhängigkeiten ..."
pip install --upgrade pip
pip install -r repo/requirements.txt

deactivate
chown -R loxberry:loxberry "$APPDIR/venv"

# ------------------------------------------------------------
# systemd Service
# ------------------------------------------------------------
echo "Erstelle systemd Service ..."

cat > "$SERVICEFILE" <<EOF
[Unit]
Description=Lox-Audioserver
After=network.target sound.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$APPDIR/repo
ExecStart=$APPDIR/venv/bin/python server.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

# >>> Mount-Rechte erlauben <<<
CapabilityBoundingSet=CAP_SYS_ADMIN
AmbientCapabilities=CAP_SYS_ADMIN
NoNewPrivileges=no

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICEFILE"

echo "Aktiviere und starte Service ..."
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable lox-audioserver
systemctl restart lox-audioserver

# ------------------------------------------------------------
# CGI-Skripte
# ------------------------------------------------------------
echo "Setze Rechte für CGI-Skripte ..."
for script in index.cgi proxy.cgi; do
    FILE="$LBHOMEDIR/webfrontend/htmlauth/$PLUGINNAME/$script"
    if [ -f "$FILE" ]; then
        chmod 755 "$FILE"
        chown loxberry:loxberry "$FILE"
    fi
done

echo "### postroot.sh abgeschlossen – Lox-Audioserver läuft nativ als systemd-Service."
exit 0
