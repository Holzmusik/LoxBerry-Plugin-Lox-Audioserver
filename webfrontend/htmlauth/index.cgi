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
my $plugin_mass = "music-assistant";

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
    my $selected_version = "latest";
    if (-e "/opt/loxberry/config/plugins/$lbpplugindir/version.txt") {
        $selected_version = LoxBerry::System::read_file("/opt/loxberry/config/plugins/$lbpplugindir/version.txt");
        chomp $selected_version;
    }
    system("sudo docker pull ghcr.io/rudyberends/lox-audioserver:$selected_version && sudo docker rm -f $plugin && sudo docker run -d --name $plugin --restart=always -p 7090:7090 -p 7091:7091 -p 7095:7095 ghcr.io/rudyberends/lox-audioserver:$selected_version");
    sleep 2;
}

# --- Aktionen für Music Assistant ---
if ($action eq 'start_mass') {
    system("sudo docker start $plugin_mass");
    sleep 2;
}
elsif ($action eq 'stop_mass') {
    system("sudo docker stop $plugin_mass");
}
elsif ($action eq 'restart_mass') {
    system("sudo docker restart $plugin_mass");
    sleep 2;
}
elsif ($action eq 'upgrade_mass') {
    system("sudo docker pull ghcr.io/music-assistant/server:latest && sudo docker rm -f $plugin_mass && sudo docker run -d --name $plugin_mass --restart=always -p 8095:8095 -v /opt/loxberry/bin/plugins/lox-audioserver/mass-config:/config -v /opt/loxberry/bin/plugins/lox-audioserver/mass-media:/media -e TZ=Europe/Berlin ghcr.io/music-assistant/server:latest");
    sleep 2;
}

# --- Status abfragen und mappen ---
my $rawstatus = `sudo docker inspect -f '{{.State.Status}}' $plugin 2>/dev/null`;
chomp $rawstatus;
my $status = ($rawstatus eq 'running') ? 'active' : 'inactive';

my $rawstatus_mass = `sudo docker inspect -f '{{.State.Status}}' $plugin_mass 2>/dev/null`;
chomp $rawstatus_mass;
my $status_mass = ($rawstatus_mass eq 'running') ? 'active' : 'inactive';

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

# --- Branches aus GitHub holen ---
my @branches;
eval {
    my $branches_json = `curl -s https://api.github.com/repos/rudyberends/lox-audioserver/branches`;
    my $branches = decode_json($branches_json);

    my $current_branch = "main";
    if (-e "/opt/loxberry/config/plugins/$lbpplugindir/version.txt") {
        $current_branch = LoxBerry::System::read_file("/opt/loxberry/config/plugins/$lbpplugindir/version.txt");
        chomp $current_branch;
    }

    foreach my $branch (@{$branches}) {
        my $name = $branch->{name};
        push @branches, { TAG => $name, SELECTED => ($name eq $current_branch ? 1 : 0) };
    }
};

# --- Template laden ---
my $templatefile = "$lbphtmldir/templates/index.html";
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

# --- Variablen ins Template ---
$templateout->param(
    STATUS        => $status,
    STATUS_MASS   => $status_mass,
    LOGS          => $logs,
    PLUGINVERSION => LoxBerry::System::pluginversion(),
    SERVERHOST    => $serverhost,
    SERVERPORT    => $serverport,
    PLAYERS       => \@players,
    VERSIONS      => \@branches,
    CURRENTBRANCH => $current_branch,
);

# --- Ausgabe ---
LoxBerry::Web::lbheader("Lox-Audioserver + Music Assistant", "", "");
print $templateout->output();
LoxBerry::Web::lbfooter();
