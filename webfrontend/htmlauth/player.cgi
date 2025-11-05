#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LoxBerry::System;
use LWP::UserAgent;
use HTML::Template;
use JSON;

my $cgi     = CGI->new;
my $zone_id = $cgi->param('zone') || 1;

# --- Defaultwerte ---
my ($title,$artist,$album,$time,$volume,$cover,$progress) = ("","","","","0","","0");

# --- Statusdaten von status.cgi holen ---
my $ua  = LWP::UserAgent->new(timeout => 5);
my $url = "http://127.0.0.1/admin/plugins/lox-audioserver/status.cgi?zone=$zone_id";
my $res = $ua->get($url);

if ($res->is_success) {
    eval {
        my $data = decode_json($res->decoded_content);
        $title    = $data->{title}    // '';
        $artist   = $data->{artist}   // '';
        $album    = $data->{album}    // '';
        $time     = $data->{time}     // '';
        $volume   = $data->{volume}   // 0;
        $cover    = $data->{cover}    // '';
        $progress = $data->{progress} // 0;
    };
    if ($@) {
        # JSON konnte nicht geparst werden
        $title  = "Fehler beim JSON-Parsing";
        $artist = $res->decoded_content;
    }
} else {
    # HTTP-Fehler
    $title  = "Fehler beim Abruf von status.cgi";
    $artist = $res->status_line;
}

# --- Template laden ---
my $templatefile = "$lbphtmldir/templates/player.html";
my $template     = LoxBerry::System::read_file($templatefile);

my $templateout = HTML::Template->new_scalar_ref(
    \$template,
    global_vars       => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
);

# --- Variablen ins Template einsetzen ---
$templateout->param(
    ZONE_ID  => $zone_id,
    TITLE    => $title,
    ARTIST   => $artist,
    ALBUM    => $album,
    TIME     => $time,
    VOLUME   => $volume,
    COVER    => $cover,
    PROGRESS => $progress,
    REFRESH  => 10,   # Sekunden für Meta-Refresh
);

# --- Ausgabe nur mit Content-Type ---
print "Content-Type: text/html\n\n";
print $templateout->output();
