#!/bin/bash
# postroot.sh – Docker-basierte Installation mit den Pfaden aus dem offiziellen Repo

echo "### Lox-Audioserver postroot.sh (Docker) startet ..."

PLUGINNAME=lox-audioserver
LBHOMEDIR=/opt/loxberry
APPDIR=$LBHOMEDIR/bin/plugins/$PLUGINNAME
WEBDIR=$LBHOMEDIR/webfrontend/html/plugins/$PLUGINNAME
GITURL="https://github.com/lox-audioserver/lox-audioserver.git"
GITBRANCH="dev"
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
