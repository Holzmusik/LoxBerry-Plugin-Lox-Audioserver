#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LWP::UserAgent;

my $cgi     = CGI->new;
my $zone_id = $cgi->param('zone') // '';
my $cmd     = $cgi->param('cmd')  // '';
my $plugin  = "lox-audioserver";

print $cgi->header('text/plain');

if ($zone_id eq '' || $cmd eq '') {
    print "Fehlende Parameter";
    exit;
}

my $serverhost = `hostname -I | awk '{print \$1}'`;
chomp $serverhost;
my $serverport = '7090';

my %cmdmap = (
    pause    => "pause",
    skip     => "next",
    volup    => "volumeUp",
    voldown  => "volumeDown"
);

my $mapped = $cmdmap{$cmd};
if (!$mapped) {
    print "Unbekannter Befehl";
    exit;
}

my $ua = LWP::UserAgent->new(timeout => 5);
my $url = "http://$serverhost:$serverport/admin/api/zones/$zone_id/$mapped";
my $res = $ua->post($url);

if ($res->is_success) {
    print "OK";
} else {
    print "Fehler: " . $res->status_line;
}
