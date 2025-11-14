#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LoxBerry::System;

my $cgi = CGI->new;

my $plugin       = "lox-audioserver";
my $configfile   = "/opt/loxberry/config/plugins/$plugin/version.txt";
my $upgradescript = "/opt/loxberry/bin/plugins/$plugin/upgrade.sh";

# POST-Daten lesen
my $version = $cgi->param('version') // '';

if ($version ne '') {
    # Auswahl speichern
    open my $fh, '>', $configfile or die "Kann $configfile nicht schreiben: $!";
    print $fh $version;
    close $fh;

    # Upgrade-Script im Hintergrund starten
    system("bash $upgradescript &");

    # Nur Redirect zurück ins index.cgi
    print $cgi->redirect("/plugins/$plugin/index.cgi");

} else {
    print $cgi->header('text/html; charset=UTF-8');
    print "<html><head><title>Fehler</title></head><body>";
    print "<h2>Fehler</h2>";
    print "<p>Keine Version ausgewählt.</p>";
    print "</body></html>";
}
