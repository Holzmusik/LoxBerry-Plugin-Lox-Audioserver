#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LoxBerry::System;
use LWP::UserAgent;
use HTML::Template;
use JSON;
use File::Path qw(make_path);
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);

# CGI initialisieren
my $cgi     = CGI->new;
my $zone_id = $cgi->param('zone') || 1;

# Plugin-Verzeichnisse
my $lbpplugindir = $LoxBerry::System::lbpplugindir;
my $lbphtmldir   = $LoxBerry::System::lbphtmldir;

# Defaultwerte
my ($title, $artist, $album, $name, $station, $elapsed, $duration, $startedAt, $updatedAt, $cover, $volume) =
   ("", "", "", "", "", 0, 0, 0, 0, "", 0);

# HTTP-Client
my $ua = LWP::UserAgent->new(timeout => 5);
$ua->agent("lox-audioserver-player-cgi/1.0");

# Status.cgi des Plugins abfragen
my $url = "http://127.0.0.1/admin/plugins/$lbpplugindir/status.cgi?zone=$zone_id";
my $res = $ua->get($url);

if (!$res->is_success) {
    $title  = "Keine Daten verfügbar";
    $artist = $res->status_line;
    $cover  = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
} else {
    my $data = eval { decode_json($res->decoded_content) };

    if ($@ || ref $data ne 'HASH') {
        $title  = "Fehler beim JSON-Parsing";
        $artist = $@;
        $cover  = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
    } else {

        # Felder übernehmen
        $title     = $data->{title}   // "";
        $artist    = $data->{artist}  // "";
        $album     = $data->{album}   // "";
        $name      = $data->{name}    // "";
        $station   = $data->{station} // "";
        $elapsed   = $data->{elapsed} // "";
        $duration  = $data->{duration} // "";
        $startedAt = $data->{startedAt} // "";
        $updatedAt = $data->{updatedAt} // "";
        $volume    = $data->{volume}  // 0;

        # Cover-URL
        my $coverurl = $data->{cover} // "";

        # Lokales Cover speichern
        my $coverdir  = "/opt/loxberry/webfrontend/html/plugins/$lbpplugindir/covers";
        my $coverfile = "$coverdir/zone$zone_id.png";
        my $local_cover = "/plugins/$lbpplugindir/covers/zone$zone_id.png";

        if ($coverurl) {
            make_path($coverdir) unless -d $coverdir;

            my $imgres = $ua->get($coverurl);
            if ($imgres->is_success && ($imgres->header('Content-Type') // '') =~ /^image/) {
                if (open my $fh, '>', $coverfile) {
                    binmode $fh;
                    print $fh $imgres->content;
                    close $fh;
                    chmod 0644, $coverfile;
                    $cover = $local_cover;
                } else {
                    warn "Cover konnte nicht gespeichert werden: $!";
                    $cover = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
                }
            } else {
                $cover = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
            }
        } else {
            $cover = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
        }
    }
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
    PROGRESS => $progress,
    REFRESH  => 10,
);

# Ausgabe
print "Content-Type: text/html\n\n";
print $templateout->output();
