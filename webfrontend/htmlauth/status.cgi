#!/usr/bin/perl

use strict;
use warnings;
use CGI;
use JSON;
use LWP::UserAgent;

my $cgi     = CGI->new;
my $zone_id = $cgi->param('zone') // '';

print $cgi->header(
    -type => 'application/json',
    -access_control_allow_origin => '*'
);

if ($zone_id eq '') {
    print encode_json({ error => "Zone-ID fehlt" });
    exit;
}

my $AS_HOST = "127.0.0.1";
my $AS_PORT = "7091";

# API: /audio/<zone>/status
my $url = "http://$AS_HOST:$AS_PORT/audio/$zone_id/status";

my $ua = LWP::UserAgent->new(timeout => 3);
my $res = $ua->get($url);

if (!$res->is_success) {
    print encode_json({ error => "AudioServer API nicht erreichbar" });
    exit;
}

my $json = decode_json($res->decoded_content);
my $s = $json->{status_result}[0];

# JSON-Ausgabe für Web-UI
print encode_json({
    title        => $s->{title}        // '',
    artist       => $s->{artist}       // '',
    album        => $s->{album}        // '',
    name         => $s->{name}         // '',
    station      => $s->{station}      // '',
    coverurl     => $s->{coverurl}     // '',
    audiopath    => $s->{audiopath}    // '',
    duration     => $s->{duration}     // 0,
    time         => $s->{time}         // 0,
    volume       => $s->{volume}       // 0,
    mode         => $s->{mode}         // '',
    audiotype    => $s->{audiotype}    // '',
    type         => $s->{type}         // '',
    clientState  => $s->{clientState}  // '',
    power        => $s->{power}        // '',
    powerState   => $s->{powerState}   // '',
    qid          => $s->{qid}          // '',
    qindex       => $s->{qindex}       // 0,
    queueAuthority => $s->{queueAuthority} // '',
    plshuffle    => $s->{plshuffle}    // 0,
    plrepeat     => $s->{plrepeat}     // 0,
});
