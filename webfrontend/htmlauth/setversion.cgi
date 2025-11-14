#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LoxBerry::System;

my $cgi = CGI->new;
print $cgi->header('text/html; charset=UTF-8');

my $plugin       = "lox-audioserver";
my $configfile   = "/opt/loxberry/config/plugins/$plugin/version.txt";
my $upgradescript = "/opt/loxberry/bin/plugins/$plugin/upgrade.sh";

# POST-Daten lesen
my $version = $cgi->param('version') // '';

print "<html><head><title>Version setzen</title></head><body>";

if ($version ne '') {
    # Auswahl speichern
    open my $fh, '>', $configfile or die "Kann $configfile nicht schreiben: $!";
    print $fh $version;
    close $fh;

    print "<h2>Version gespeichert</h2>";
    print "<p>Gewählte Version: <b>$version</b></p>";
    print "<p>Upgrade wird gestartet...</p>";

    # Upgrade-Script im Hintergrund starten
    system("bash $upgradescript &");

} else {
    print "<h2>Fehler</h2>";
    print "<p>Keine Version ausgewählt.</p>";
}

print "</body></html>";
