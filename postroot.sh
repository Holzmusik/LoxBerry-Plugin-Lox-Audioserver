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
echo "Erstelle schnelles MQTT-Update-Script ..."

MQTTUPDATESCRIPT="/opt/loxberry/bin/plugins/$PLUGINNAME/mqtt_delta.pl"
cat << 'EOF' > $MQTTUPDATESCRIPT
#!/usr/bin/perl
$ENV{'LBHOMEDIR'} = '/opt/loxberry';
$ENV{'PERL5LIB'} = '/opt/loxberry/libs/perllib';

use strict;
use warnings;
use LoxBerry::IO;
use File::Path qw(make_path);

my ($topic, $value) = @ARGV;
exit 0 if !$topic;

# Cache-Verzeichnis
my $cache_dir = "/opt/loxberry/data/lox-audioserver/mqttcache";
make_path($cache_dir);

# Topic-Dateiname sicher machen
(my $safe_topic = $topic) =~ s/[^\w\-]/_/g;
my $cache_file = "$cache_dir/$safe_topic.txt";

# Alten Wert laden
my $old = "";
if (-e $cache_file) {
    open my $fh, "<", $cache_file;
    $old = <$fh>;
    close $fh;
    chomp $old;
}

# Delta: Nur senden, wenn sich der Wert geändert hat
if ($old ne $value) {
    my $mqtt = LoxBerry::IO::mqtt_connect();
    $mqtt->publish($topic, $value);
    $mqtt->disconnect();

    # neuen Wert speichern
    open my $fh, ">", $cache_file;
    print $fh $value;
    close $fh;
}

exit 0;
EOF

chmod +x $MQTTUPDATESCRIPT
chown loxberry:loxberry $MQTTUPDATESCRIPT



echo "Erstelle schnelles Cover-Update-Script ..."

UPDATESCRIPT="/opt/loxberry/bin/plugins/$PLUGINNAME/update_covers.sh"

cat << 'EOF' > $UPDATESCRIPT
#!/bin/bash
# Ultra-schnelles Cover- und MQTT-Update über die offizielle AudioServer API
# Keine status.cgi, kein Perl-CGI, minimale CPU-Last

set -euo pipefail

# --- LoxBerry-Umgebung für systemd sicherstellen ---
export LBHOMEDIR=/opt/loxberry
export PERL5LIB=/opt/loxberry/libs/perllib
export HOME=/opt/loxberry
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

PLUGIN="lox-audioserver"
AS_IP="localhost"
AS_PORT="7091"

COVERDIR="/opt/loxberry/webfrontend/html/plugins/$PLUGIN/covers"
mkdir -p "$COVERDIR"

LOCKFILE="/var/lock/lox-audioserver-cover.lock"
exec 200>"$LOCKFILE"
flock -n 200 || exit 0

# --- Auto-Zonenerkennung ---
ZONES=$(curl -s "http://$AS_IP:$AS_PORT/audio/status" | jq -r '.status_result[].playerid' 2>/dev/null || echo "")

if [ -z "$ZONES" ]; then
    ZONES=$(seq 1 10)
fi

update_zone() {
    Z=$1

    JSON=$(curl -s "http://$AS_IP:$AS_PORT/audio/$Z/status")
    [ -z "$JSON" ] && return

    COVERURL=$(echo "$JSON" | jq -r '.status_result[0].coverurl // empty')
    [ -z "$COVERURL" ] && return

    TMP_JPG="/dev/shm/cover_${Z}.jpg"
    TMP_PNG="/dev/shm/cover_${Z}.png"
    FINAL_PNG="$COVERDIR/zone${Z}.png"

    curl -s -o "$TMP_JPG" "$COVERURL" || return
    [ ! -s "$TMP_JPG" ] && return

    if ! file "$TMP_JPG" | grep -qE 'image|bitmap'; then
        rm -f "$TMP_JPG"
        return
    fi

    # JPG -> PNG konvertieren (immer in TMP)
    convert "$TMP_JPG" -resize 480x480 "$TMP_PNG"

    # PNG-Delta: nur schreiben, wenn sich das PNG wirklich geändert hat
    if [ -f "$FINAL_PNG" ]; then
        NEW_HASH=$(sha256sum "$TMP_PNG" | awk '{print $1}')
        OLD_HASH=$(sha256sum "$FINAL_PNG" | awk '{print $1}')
    else
        NEW_HASH="x"
        OLD_HASH="y"
    fi

    if [ "$NEW_HASH" != "$OLD_HASH" ]; then
        mv "$TMP_PNG" "$FINAL_PNG"
        chmod 644 "$FINAL_PNG"
    else
        rm -f "$TMP_PNG"
    fi

    rm -f "$TMP_JPG"

    # --- MQTT-Delta über Perl ---
    MQTT_BASE="lox/audioserver/$Z"

    publish_if_changed() {
        local key="$1"
        local value="$2"
        local topic="$MQTT_BASE/$key"

        /opt/loxberry/bin/plugins/lox-audioserver/mqtt_delta.pl "$topic" "$value"
    }

    TITLE=$(echo "$JSON" | jq -r '.status_result[0].title // empty')
    ARTIST=$(echo "$JSON" | jq -r '.status_result[0].artist // empty')
    ALBUM=$(echo "$JSON" | jq -r '.status_result[0].album // empty')
    STATION=$(echo "$JSON" | jq -r '.status_result[0].station // empty')
    MODE=$(echo "$JSON" | jq -r '.status_result[0].mode // empty')
    VOLUME=$(echo "$JSON" | jq -r '.status_result[0].volume // empty')
    TIMEPOS=$(echo "$JSON" | jq -r '.status_result[0].time // empty')
    DURATION=$(echo "$JSON" | jq -r '.status_result[0].duration // empty')
    CLIENTSTATE=$(echo "$JSON" | jq -r '.status_result[0].clientState // empty')
    POWER=$(echo "$JSON" | jq -r '.status_result[0].power // empty')
    AUDIOPATH=$(echo "$JSON" | jq -r '.status_result[0].audiopath // empty')
    SOURCENAME=$(echo "$JSON" | jq -r '.status_result[0].sourceName // empty')

    publish_if_changed "title" "$TITLE"
    publish_if_changed "artist" "$ARTIST"
    publish_if_changed "album" "$ALBUM"
    publish_if_changed "station" "$STATION"
    publish_if_changed "mode" "$MODE"
    publish_if_changed "volume" "$VOLUME"
    publish_if_changed "time" "$TIMEPOS"
    publish_if_changed "duration" "$DURATION"
    publish_if_changed "clientState" "$CLIENTSTATE"
    publish_if_changed "power" "$POWER"
    publish_if_changed "audiopath" "$AUDIOPATH"
    publish_if_changed "sourceName" "$SOURCENAME"
}

for Z in $ZONES; do
    update_zone "$Z"
done


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
Environment="LBHOMEDIR=/opt/loxberry"
Environment="HOME=/opt/loxberry"
Environment="PERL5LIB=/opt/loxberry/libs/perllib"
Environment="PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
WorkingDirectory=/opt/loxberry
ExecStart=/bin/bash /opt/loxberry/bin/plugins/lox-audioserver/update_covers.sh
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
