#!/usr/bin/perl

use strict;
use warnings;
use CGI;
use LoxBerry::System;
use LWP::UserAgent;
use HTML::Template;
use JSON;

# CGI initialisieren
my $cgi     = CGI->new;
my $zone_id = $cgi->param('zone') || 1;

# Plugin-Verzeichnisse
my $lbpplugindir = $LoxBerry::System::lbpplugindir;
my $lbphtmldir   = $LoxBerry::System::lbphtmldir;

# Defaultwerte
my ($title, $artist, $album, $name, $station, $elapsed, $duration, $cover, $volume) =
   ("", "", "", "", "", 0, 0, "", 0);

# AudioServer API (High Performance)
my $AS_HOST = "127.0.0.1";
my $AS_PORT = "7091";
my $url = "http://$AS_HOST:$AS_PORT/audio/$zone_id/status";

my $ua = LWP::UserAgent->new(timeout => 3);
my $res = $ua->get($url);

if ($res->is_success) {

    my $json = eval { decode_json($res->decoded_content) };

    if (!$@ && ref $json eq 'HASH') {

        my $s = $json->{status_result}[0];

        # Felder übernehmen
        $title    = $s->{title}    // "";
        $artist   = $s->{artist}   // "";
        $album    = $s->{album}    // "";
        $name     = $s->{name}     // "";
        $station  = $s->{station}  // "";
        $elapsed  = $s->{time}     // 0;
        $duration = $s->{duration} // 0;
        $volume   = $s->{volume}   // 0;

        # Cover kommt jetzt aus update_covers.sh
        my $coverfile = "/plugins/$lbpplugindir/covers/zone$zone_id.png";

        if (-f "/opt/loxberry/webfrontend/html/plugins/$lbpplugindir/covers/zone$zone_id.png") {
            $cover = $coverfile;
        } else {
            $cover = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
        }

    } else {
        $title  = "Fehler beim JSON-Parsing";
        $artist = $@;
        $cover  = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
    }

} else {
    $title  = "Keine Daten verfügbar";
    $artist = $res->status_line;
    $cover  = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
}

# Template laden
my $templatefile = "$lbphtmldir/templates/player.html";
my $template     = LoxBerry::System::read_file($templatefile);

my $templateout = HTML::Template->new_scalar_ref(
    \$template,
    global_vars       => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
);

# Variablen ins Template
$templateout->param(
    ZONE_ID  => $zone_id,
    TITLE    => $title,
    ARTIST   => $artist,
    ALBUM    => $album,
    NAME     => $name,
    STATION  => $station,
    COVER    => $cover,
    VOLUME   => $volume,
    REFRESH  => 10,
);

# Ausgabe
print "Content-Type: text/html\n\n";
print $templateout->output();
