#!/usr/bin/perl

use strict;
use warnings;
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LWP::UserAgent;
use JSON;
use HTML::Template;

my $cgi     = CGI->new;
my $action  = $cgi->param('action') // '';
my $plugin  = "lox-audioserver";
my $plugin_mass = "music-assistant";

# -------------------------------
# Docker-Steuerung
# -------------------------------
if ($action) {
    my %cmd = (
        start         => "sudo docker start $plugin",
        stop          => "sudo docker stop $plugin",
        restart       => "sudo docker restart $plugin",
        start_mass    => "sudo docker start $plugin_mass",
        stop_mass     => "sudo docker stop $plugin_mass",
        restart_mass  => "sudo docker restart $plugin_mass",
    );

    system($cmd{$action}) if $cmd{$action};

    print "Status: 302 Found\n";
    print "Location: /admin/plugins/$plugin/index.cgi\n";
    print "Content-Type: text/html\n\n";
    exit;
}

# -------------------------------
# Docker-Status
# -------------------------------
sub docker_status {
    my ($name) = @_;
    my $raw = `sudo docker inspect -f '{{.State.Status}}' $name 2>/dev/null`;
    chomp $raw;
    return ($raw eq 'running') ? 'active' : 'inactive';
}

my $status       = docker_status($plugin);
my $status_mass  = docker_status($plugin_mass);

# -------------------------------
# AudioServer API: /audio/status
# -------------------------------
my $AS_HOST = "127.0.0.1";
my $AS_PORT = "7091";

my $ua = LWP::UserAgent->new(timeout => 3);
my $res = $ua->get("http://$AS_HOST:$AS_PORT/audio/status");

my @players;

if ($res->is_success) {
    my $json = decode_json($res->decoded_content);

    foreach my $z (@{$json->{status_result}}) {

        my $id     = $z->{playerid};
        my $name   = $z->{name}       // "Unbekannt";
        my $title  = $z->{title}      // "";
        my $artist = $z->{artist}     // "";
        my $state  = $z->{mode}       // "";
        my $station = $z->{station}   // "";

        # Lokales Cover
        my $lbpplugindir = $LoxBerry::System::lbpplugindir;
        my $cover_local = "/plugins/$lbpplugindir/covers/zone$id.png";
        my $physical = "/opt/loxberry/webfrontend/html$cover_local";

        if (! -f $physical) {
            $cover_local = "/plugins/$lbpplugindir/templates/images/No-album-art.png";
        }

        push @players, {
            ZONE_ID     => $id,
            ZONE_NAME   => $name,
            ZONE_TITLE  => $title,
            ZONE_ARTIST => $artist,
            ZONE_STATE  => $state,
            ZONE_STATION=> $station,
            LOCAL_COVER => $cover_local,
            PLAYER_URL  => "/admin/plugins/$lbpplugindir/player.cgi?zone=$id",
        };
    }
}

# Fallback
if (!@players) {
    push @players, {
        ZONE_NAME   => "Keine Player gefunden",
        ZONE_TITLE  => "",
        ZONE_ARTIST => "",
        ZONE_STATE  => "",
        LOCAL_COVER => "/plugins/$plugin/templates/images/No-album-art.png",
        PLAYER_URL  => "#",
    };
}

# -------------------------------
# Branches aus GitHub
# -------------------------------
my @branches;
eval {
    my $branches_json = `curl -s https://api.github.com/repos/Holzmusik/LoxBerry-Plugin-Lox-Audioserver/branches`;
    my $branches = decode_json($branches_json);

    my $current_branch = "main";
    if (-e "/opt/loxberry/config/plugins/$plugin/version.txt") {
        $current_branch = LoxBerry::System::read_file("/opt/loxberry/config/plugins/$plugin/version.txt");
        chomp $current_branch;
    }

    foreach my $branch (@{$branches}) {
        my $name = $branch->{name};
        push @branches, { TAG => $name, SELECTED => ($name eq $current_branch ? 1 : 0) };
    }
};

@branches = ( { TAG => "main", SELECTED => 1 } ) unless @branches;

# -------------------------------
# Template laden
# -------------------------------
my $lbpplugindir = $LoxBerry::System::lbpplugindir;
my $templatefile = "/opt/loxberry/webfrontend/html/plugins/$lbpplugindir/templates/index.html";
my $template     = LoxBerry::System::read_file($templatefile);

my $templateout = HTML::Template->new_scalar_ref(
    \$template,
    global_vars       => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
);

my $current_branch = "main";
if (-e "/opt/loxberry/config/plugins/$lbpplugindir/version.txt") {
    $current_branch = LoxBerry::System::read_file("/opt/loxberry/config/plugins/$lbpplugindir/version.txt");
    chomp $current_branch;
}

$templateout->param(
    STATUS        => $status,
    STATUS_MASS   => $status_mass,
    PLAYERS       => \@players,
    VERSIONS      => \@branches,
    CURRENTBRANCH => $current_branch,
    PLUGINVERSION => LoxBerry::System::pluginversion(),
);

# -------------------------------
# Ausgabe
# -------------------------------
LoxBerry::Web::lbheader("Lox-Audioserver + Music Assistant", "", "");
print $templateout->output();
LoxBerry::Web::lbfooter();
