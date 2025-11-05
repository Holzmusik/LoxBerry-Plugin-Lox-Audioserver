#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LWP::UserAgent;
use HTML::Template;
use Config::Simple;
use JSON;

my $cgi    = CGI->new;
my $action = $cgi->param('action') // '';
my $plugin = "lox-audioserver";

# --- Aktionen über Docker steuern ---
if ($action eq 'start') {
    system("sudo docker start $plugin");
    sleep 2;
}
elsif ($action eq 'stop') {
    system("sudo docker stop $plugin");
}
elsif ($action eq 'restart') {
    system("sudo docker restart $plugin");
    sleep 2;
}
elsif ($action eq 'upgrade') {
    system("sudo docker pull ghcr.io/rudyberends/lox-audioserver:latest && sudo docker restart $plugin");
    sleep 2;
}

# --- Status abfragen und mappen ---
my $rawstatus = `sudo docker inspect -f '{{.State.Status}}' $plugin 2>/dev/null`;
chomp $rawstatus;
my $status = ($rawstatus eq 'running') ? 'active' : 'inactive';

# --- Plugin-Konfiguration laden ---
my $cfgfile = "$lbpconfigdir/plugins/$lbpplugindir/plugin.cfg";
my ($serverhost, $serverport);

if (-e $cfgfile) {
    my $cfg = Config::Simple->new($cfgfile)
        or warn "Konnte $cfgfile nicht laden: " . Config::Simple->error();
    if ($cfg) {
        $serverhost = $cfg->param("SERVER.SERVERHOST");
        $serverport = $cfg->param("SERVER.SERVERPORT");
    }
}

# --- IP-Adresse des LoxBerry dynamisch ermitteln ---
$serverhost ||= `hostname -I | awk '{print \$1}'`;
chomp $serverhost;
$serverport ||= '7090';

# --- Logs direkt vom Audioserver holen ---
my $logs = "";
eval {
    my $ua  = LWP::UserAgent->new(timeout => 5);
    my $res = $ua->get("http://$serverhost:$serverport/admin/logs");
    if ($res->is_success) {
        $logs = $res->decoded_content;
    }
};
$logs ||= "Keine Logs verfügbar.";

# --- Player-Infos über API holen ---
my @players;
eval {
    my $ua  = LWP::UserAgent->new(timeout => 5);
    my $res = $ua->get("http://$serverhost:$serverport/admin/api/zones/states");
    if ($res->is_success) {
        my $data = decode_json($res->decoded_content);
        foreach my $zone (@{$data->{zones}}) {
            my $id     = $zone->{id};
            my $name   = $zone->{name}       // 'Unbekannt';
            my $title  = $zone->{title}      // '';
            my $artist = $zone->{artist}     // '';
            my $track  = $zone->{track}      // '';
            my $time   = $zone->{time}       // '';
            my $volume = $zone->{volume}     // '';
            my $coverurl = $zone->{coverUrl} // '';

            # Cover lokal speichern
            my $coverfile   = "/opt/loxberry/webfrontend/html/plugins/$lbpplugindir/covers/zone$id.png";
            my $local_cover = "/plugins/$lbpplugindir/covers/zone$id.png";

            if ($coverurl) {
                my $imgres = $ua->get($coverurl);
                if ($imgres->is_success) {
                    open my $fh, '>', $coverfile;
                    binmode $fh;
                    print $fh $imgres->content;
                    close $fh;
                    chmod 0644, $coverfile;
                }
            }

            # Link zur gemeinsamen Player-Seite
            my $player_url = "/plugins/$lbpplugindir/player.html?zone=$id";

            push @players, {
                ZONE_NAME   => $name,
                ZONE_TITLE  => $title,
                ZONE_ARTIST => $artist,
                ZONE_TRACK  => $track,
                ZONE_TIME   => $time,
                ZONE_VOLUME => $volume,
                LOCAL_COVER => $local_cover,
                PLAYER_URL  => $player_url,
            };
        }
    }
};
if (!@players) {
    push @players, {
        ZONE_NAME   => "Keine Player gefunden",
        ZONE_TITLE  => "",
        ZONE_ARTIST => "",
        ZONE_TRACK  => "",
        ZONE_TIME   => "",
        ZONE_VOLUME => "",
        LOCAL_COVER => "/plugins/$lbpplugindir/images/default_cover.png",
        PLAYER_URL  => "#",
    };
}

# --- Template laden ---
my $templatefile = "$lbphtmldir/templates/index.html";
my $template     = LoxBerry::System::read_file($templatefile);

my $templateout = HTML::Template->new_scalar_ref(
    \$template,
    global_vars       => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
);

# --- Variablen ins Template ---
$templateout->param(
    STATUS        => $status,
    LOGS          => $logs,
    PLUGINVERSION => LoxBerry::System::pluginversion(),
    SERVERHOST    => $serverhost,
    SERVERPORT    => $serverport,
    PLAYERS       => \@players,
);

# --- Ausgabe ---
LoxBerry::Web::lbheader("Lox-Audioserver", "", "");
print $templateout->output();
LoxBerry::Web::lbfooter();
