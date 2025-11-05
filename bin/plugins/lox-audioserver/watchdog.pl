#!/usr/bin/perl

use strict;
use warnings;

my $plugin   = "lox-audioserver";
my $logfile  = "/opt/loxberry/log/plugins/$plugin/lox-audioserver.log";
my $start    = "/opt/loxberry/plugins/$plugin/bin/start.sh";

open my $log, '>>', $logfile or die "Kann Log nicht öffnen: $!";

while (1) {
    my $pid = `pgrep -f "node.*lox-audioserver"`;
    chomp $pid;

    if (!$pid) {
        print $log "Watchdog: Prozess nicht gefunden – starte neu\n";
        system($start);
    } else {
        print $log "Watchdog: Prozess läuft (PID $pid)\n";
    }

    sleep 60;
}
