#!/bin/bash
# postroot.sh – Docker-basierte Installation mit den Pfaden aus dem offiziellen Repo

echo "### Lox-Audioserver postroot.sh (Docker) startet ..."

PLUGINNAME=lox-audioserver
LBHOMEDIR=/opt/loxberry
APPDIR=$LBHOMEDIR/bin/plugins/$PLUGINNAME
WEBDIR=$LBHOMEDIR/webfrontend/html/plugins/$PLUGINNAME
GITURL="https://github.com/lox-audioserver/lox-audioserver.git"
#GITURL="https://github.com/mr-manuel/Loxone_lox-audioserver.git"
GITBRANCH="testing"
LOCALIMG="lox-audioserver:beta-local"


# Docker prüfen und ggf. installieren
if ! command -v docker >/dev/null 2>&1; then
    echo "Docker ist nicht installiert – Installation wird gestartet ..."
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y docker.io
        systemctl enable docker
        systemctl start docker
    elif command -v yum >/dev/null 2>&1; then
        yum install -y docker
        systemctl enable docker
        systemctl start docker
    else
        echo "FEHLER: Paketmanager nicht erkannt – bitte Docker manuell installieren."
        exit 1
    fi
fi

echo "Installiere ImageMagick und Perl-Bindings ..."
if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y imagemagick libimage-magick-perl
elif command -v yum >/dev/null 2>&1; then
    yum install -y ImageMagick perl-Image-Magick
else
    echo "WARNUNG: Konnte ImageMagick nicht installieren – Paketmanager unbekannt."
fi

echo "Erstelle schnelles Cover-Update-Script ..."

UPDATESCRIPT="/opt/loxberry/bin/plugins/$PLUGINNAME/update_covers.sh"

cat << 'EOF' > $UPDATESCRIPT

#!/bin/bash
# Finales Cover-Update für Lox-Audioserver (CM5-kompatibel)
# Holt Cover direkt aus status.cgi, konvertiert nach PNG und speichert zuverlässig.

set -euo pipefail

PLUGIN="lox-audioserver"
STATUS_URL="http://127.0.0.1/admin/plugins/$PLUGIN/status.cgi?zone="

# Fester Pfad – CM5 hat keine Shell-Plugin-Variablen
COVERDIR="/opt/loxberry/webfrontend/html/plugins/$PLUGIN/covers"
mkdir -p "$COVERDIR"

LOCKFILE="/var/lock/lox-audioserver-cover.lock"
exec 200>$LOCKFILE
flock -n 200 || exit 0

MAX_ZONES=10

update_zone() {
    Z=$1

    # JSON holen
    JSON=$(curl -s "$STATUS_URL$Z" || true)
    [ -z "$JSON" ] && return

    # Cover-URL extrahieren
    COVERURL=$(echo "$JSON" | jq -r '.cover // empty')
    [ -z "$COVERURL" ] && return

    TMP="/tmp/cover_${Z}_orig"
    FINAL="$COVERDIR/zone${Z}.png"

    # Originalbild laden
    curl -s "$COVERURL" -o "$TMP" || return

    # Prüfen, ob es ein Bild ist
    if ! file "$TMP" | grep -qE 'image|bitmap'; then
        rm -f "$TMP"
        return
    fi

    # PNG konvertieren (egal welches Quellformat)
    convert "$TMP" PNG:"$FINAL"

    chmod 644 "$FINAL"
    touch "$FINAL"
    rm -f "$TMP"
}

# Alle Zonen parallel aktualisieren
for Z in $(seq 1 $MAX_ZONES); do
    update_zone "$Z" &
done
wait


EOF

chmod +x $UPDATESCRIPT
chown loxberry:loxberry $UPDATESCRIPT





echo "Erstelle systemd Service für Cover-Updates ..."

SERVICE_FILE="/etc/systemd/system/lox-audioserver-cover.service"

cat << 'EOF' > $SERVICE_FILE
[Unit]
Description=Lox-Audioserver Cover Update Service

[Service]
Type=oneshot
User=loxberry
Group=loxberry
ExecStart=/opt/loxberry/bin/plugins/lox-audioserver/update_covers.sh
EOF

echo "Erstelle systemd Timer für Cover-Updates ..."

TIMER_FILE="/etc/systemd/system/lox-audioserver-cover.timer"

cat << 'EOF' > $TIMER_FILE
[Unit]
Description=Run Lox-Audioserver Cover Update every second

[Timer]
OnBootSec=5
OnUnitActiveSec=5
AccuracySec=100ms

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable lox-audioserver-cover.timer
systemctl start lox-audioserver-cover.timer


# In Plugin-Verzeichnis wechseln
cd "$APPDIR" || exit 1

# Verzeichnisse wie im Repo vorgeschlagen anlegen
echo "Erstelle ./data und ./logs ..."
mkdir -p ./data ./logs
chown -R loxberry:loxberry ./data ./logs

# Verzeichnis für Coverbilder im Webfrontend anlegen
echo "Erstelle Cover-Verzeichnis im Webfrontend ..."
mkdir -p "$WEBDIR/covers"
chown -R loxberry:loxberry "$WEBDIR/covers"

# Alten Container entfernen, falls vorhanden
if docker ps -a --format '{{.Names}}' | grep -q "^$PLUGINNAME$"; then
    echo "Entferne alten Container $PLUGINNAME ..."
    docker rm -f $PLUGINNAME
fi

# Repository klonen oder aktualisieren
if [ ! -d "$APPDIR/repo" ]; then
    echo "Klonen des beta-branch ..."
    git clone --branch "$GITBRANCH" "$GITURL" "$APPDIR/repo"
else   
   echo "Aktualisiere bestehendes Repository ..."
   cd "$APPDIR/repo"
   git fetch
   git reset --hard origin/$GITBRANCH
fi

# Docker-Image lokal bauen
echo "Baue lokales Docker-Image $LOCALIMG ..."
cd "$APPDIR/repo"
docker build -t "$LOCALIMG" .

# Container starten mit den Pfaden aus dem Repo
echo "Starte neuen Container $PLUGINNAME ..."
docker run -d \
  --name $PLUGINNAME \
  --restart=always \
  --network host \
  --cap-add SYS_ADMIN \
  --cap-add DAC_READ_SEARCH \
  --security-opt apparmor=unconfined \
  -v "$APPDIR/data:/app/data" \
  -v "$APPDIR/logs:/app/logs" \
  "$LOCALIMG"
  
# CGI-Skripte Rechte setzen (Proxy & Index)
echo "Setze Rechte für CGI-Skripte ..."
for script in index.cgi proxy.cgi; do
    if [ -f $LBHOMEDIR/webfrontend/htmlauth/$PLUGINNAME/$script ]; then
        chmod 755 $LBHOMEDIR/webfrontend/htmlauth/$PLUGINNAME/$script
        chown loxberry:loxberry $LBHOMEDIR/webfrontend/htmlauth/$PLUGINNAME/$script
    fi
done

### Music Assistant Integration ###
PLUGINNAME_MASS=music-assistant

# Alten Container entfernen, falls vorhanden
if docker ps -a --format '{{.Names}}' | grep -q "^$PLUGINNAME_MASS$"; then
    echo "Entferne alten Container $PLUGINNAME_MASS ..."
    docker rm -f $PLUGINNAME_MASS
fi

# Neueste Version ziehen
echo "Ziehe aktuelles Music Assistant Docker-Image ..."
docker pull ghcr.io/music-assistant/server:latest

# Verzeichnisse für Config und Media anlegen
echo "Erstelle Config- und Media-Verzeichnisse für Music Assistant ..."
mkdir -p "$APPDIR/mass-config" "$APPDIR/mass-media"
chown -R loxberry:loxberry "$APPDIR/mass-config" "$APPDIR/mass-media"

# Container starten
echo "Starte neuen Container $PLUGINNAME_MASS ..."
docker run -d \
  --name $PLUGINNAME_MASS \
  --restart=always \
  --network host \
  -v "$APPDIR/mass-config:/config" \
  -v "$APPDIR/mass-media:/media" \
  -e TZ=Europe/Berlin \
  ghcr.io/music-assistant/server:latest

echo "### postroot.sh abgeschlossen – Lox-Audioserver + Music Assistant laufen jetzt in Docker."
exit 0
