#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use JSON;
use LWP::UserAgent;

my $cgi     = CGI->new;
my $zone_id = $cgi->param('zone') // '';
my $plugin  = "lox-audioserver";

print $cgi->header(
    -type => 'application/json',
    -access_control_allow_origin => '*'
);

if ($zone_id eq '') {
    print encode_json({ error => "Zone-ID fehlt" });
    exit;
}

# Audioserver läuft lokal auf dem LoxBerry
my $serverhost = "127.0.0.1";
my $serverport = "7090";

# API korrekt abrufen
my $ua  = LWP::UserAgent->new(timeout => 5);
my $res = $ua->get("http://$serverhost:$serverport/admin/api/zones/states");

if (!$res->is_success) {
    print encode_json({ error => "API nicht erreichbar" });
    exit;
}

my $data = decode_json($res->decoded_content);

# Standardwerte
my ($title, $artist, $album, $name, $cover, $state, $sourceName, $station);
my ($elapsed, $duration, $startedAt, $updatedAt) = (0, 0, 0, 0);

foreach my $zone (@{$data->{zones}}) {

    next unless $zone->{id} == $zone_id;

    $title      = $zone->{title}      // '';
    $artist     = $zone->{artist}     // '';
    $album      = $zone->{album}      // '';
    $name       = $zone->{name}       // '';
    $state      = $zone->{state}      // '';
    $sourceName = $zone->{sourceName} // '';
    $station    = $zone->{station}    // '';

    # Fortschritt aus tech.session
    if ($zone->{tech} && $zone->{tech}->{session}) {
        my $s = $zone->{tech}->{session};
        $elapsed   = $s->{elapsed}   // 0;
        $duration  = $s->{duration}  // 0;
        $startedAt = $s->{startedAt} // 0;
        $updatedAt = $s->{updatedAt} // 0;
    }

    # Cover-URL korrekt behandeln
    $cover = $zone->{coverUrl}
          // $zone->{coverurl}
          // "/plugins/$plugin/templates/images/No-album-art.png";

    last;
}

print encode_json({
    title      => $title,
    artist     => $artist,
    album      => $album,
    name       => $name,
    station    => $station,
    cover      => $cover,
    state      => $state,
    source     => $sourceName,
    elapsed    => $elapsed,
    duration   => $duration,
    startedAt  => $startedAt,
    updatedAt  => $updatedAt,
    volume     => 0,
});
