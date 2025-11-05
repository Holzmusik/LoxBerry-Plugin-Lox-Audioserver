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
    -access_control_allow_origin => '*'   # erlaubt direkten Browser-Zugriff
);

if ($zone_id eq '') {
    print encode_json({ error => "Zone-ID fehlt" });
    exit;
}

# Host/Port des Audioservers
my $serverhost = `hostname -I | awk '{print \$1}'`;
chomp $serverhost;
my $serverport = '7090';

# API abfragen
my $ua  = LWP::UserAgent->new(timeout => 5);
my $res = $ua->get("http://$serverhost:$serverport/api/zones/states");

if (!$res->is_success) {
    print encode_json({ error => "API nicht erreichbar" });
    exit;
}

my $data = decode_json($res->decoded_content);

# Default-Werte
my ($title, $artist, $name, $album, $volume, $cover, $state, $mode, $power,
    $positionMs, $durationMs, $progress, $sourceName, $connected) =
   ("","","",0,"","","","",0,0,0,"",0);

foreach my $zone (@{$data->{zones}}) {
    next unless $zone->{id} eq $zone_id;

    $title      = $zone->{title}      // '';
	$name       = $zone->{name}      // '';
    $artist     = $zone->{artist}     // '';
    $album      = $zone->{album}      // '';
    $volume     = $zone->{volume}     // 0;
    $cover      = $zone->{coverUrl}   // "/plugins/$plugin/covers/zone$zone_id.png";
    $state      = $zone->{state}      // '';
    $mode       = $zone->{mode}       // '';
    $power      = $zone->{power}      // '';
    $positionMs = $zone->{positionMs} // 0;
    $durationMs = $zone->{durationMs} // 0;
    $sourceName = $zone->{sourceName} // '';
    $connected  = $zone->{connected}  // 0;

    $progress = ($durationMs && $positionMs)
        ? int(($positionMs / $durationMs) * 100)
        : 0;

    last;
}

print encode_json({
    title      => $title,
	name       => $name,
    artist     => $artist,
    album      => $album,
    volume     => $volume,
    cover      => $cover,
    state      => $state,       # z.B. "playing"
    mode       => $mode,        # z.B. "play"
    power      => $power,       # "on"/"off"
    positionMs => $positionMs,  # Fortschritt in ms
    durationMs => $durationMs,  # Gesamtlänge in ms
    progress   => $progress,    # 0–100 %
    source     => $sourceName,  # z.B. "Spotify"
    connected  => $connected    # true/false
});
