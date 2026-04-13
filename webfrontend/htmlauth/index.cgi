#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LWP::UserAgent;
use HTTP::Cookies;
use HTML::Template;
use Config::Simple;
use JSON;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);

my $cgi    = CGI->new;
my $action = $cgi->param('action') // '';
my $plugin = "lox-audioserver";
my $plugin_mass = "music-assistant";

# --- Aktionen über Docker steuern ---
if ($action) {
    if ($action eq 'start') {
        system("sudo docker start $plugin");
    }
    elsif ($action eq 'stop') {
        system("sudo docker stop $plugin");
    }
    elsif ($action eq 'restart') {
        system("sudo docker restart $plugin");
    }
    elsif ($action eq 'start_mass') {
        system("sudo docker start $plugin_mass");
    }
    elsif ($action eq 'stop_mass') {
        system("sudo docker stop $plugin_mass");
    }
    elsif ($action eq 'restart_mass') {
        system("sudo docker restart $plugin_mass");
    }

    print "Status: 302 Found\n";
    print "Location: /admin/plugins/lox-audioserver/index.cgi\n";
    print "Content-Type: text/html\n\n";
    exit;
}

# --- Plugin-Konfiguration laden ---
my $cfgfile = "$lbpconfigdir/plugins/$lbpplugindir/plugin.cfg";
my ($serverhost, $serverport);

if (-e $cfgfile) {
    my $cfg = Config::Simple->new($cfgfile);
    if ($cfg) {
        $serverhost = $cfg->param("SERVER.SERVERHOST");
        $serverport = $cfg->param("SERVER.SERVERPORT");
    }
}

$serverhost ||= `hostname -I | awk '{print \$1}'`;
chomp $serverhost;
$serverport ||= '7090';

# --- Docker Status ---
my $rawstatus = `sudo docker inspect -f '{{.State.Status}}' $plugin 2>/dev/null`;
chomp $rawstatus;
my $status = ($rawstatus eq 'running') ? 'active' : 'inactive';

my $rawstatus_mass = `sudo docker inspect -f '{{.State.Status}}' $plugin_mass 2>/dev/null`;
chomp $rawstatus_mass;
my $status_mass = ($rawstatus_mass eq 'running') ? 'active' : 'inactive';

# --- Logs holen ---
my $logs = "";
eval {
    my $ua  = LWP::UserAgent->new(timeout => 5);
    my $res = $ua->get("http://$serverhost:$serverport/admin/logs");
    $logs = $res->decoded_content if $res->is_success;
};
$logs ||= "Keine Logs verfügbar.";

# --- Player-Infos holen (mit Login!) ---
my @players;

eval {
    my $ua = LWP::UserAgent->new(timeout => 5);
    my $cookies = HTTP::Cookies->new();
    $ua->cookie_jar($cookies);

    # --- Login ---
    my $login_res = $ua->post(
        "http://$serverhost:$serverport/admin/api/auth/login",
        'Content-Type' => 'application/json',
        Content        => encode_json({
            username => "Setup",
            password => "Saschasmtf8"
        })
    );

    if (!$login_res->is_success) {
        die "Login fehlgeschlagen: " . $login_res->status_line;
    }

    # --- API abrufen ---
    my $res = $ua->get("http://$serverhost:$serverport/admin/api/zones/states");
    die "API nicht erreichbar" unless $res->is_success;

    my $data = decode_json($res->decoded_content);

    foreach my $zone (@{$data->{zones}}) {

        my $id     = $zone->{id};
        my $name   = $zone->{name}       // 'Unbekannt';
        my $title  = $zone->{title}      // '';
        my $artist = $zone->{artist}     // '';
        my $station = $zone->{station}   // '';
        my $state  = $zone->{state}      // '';
        my $coverurl = $zone->{coverUrl} // $zone->{coverurl} // '';

        # Cover speichern
        my $coverdir  = "/opt/loxberry/webfrontend/html/plugins/$lbpplugindir/covers";
        my $coverfile = "$coverdir/zone$id.png";
        my $local_cover = "/plugins/$lbpplugindir/covers/zone$id.png";

        if ($coverurl) {
            mkdir $coverdir unless -d $coverdir;
            my $imgres = $ua->get($coverurl);
            if ($imgres->is_success) {
                open my $fh, '>', $coverfile;
                binmode $fh;
                print $fh $imgres->content;
                close $fh;
                chmod 0644, $coverfile;
            }
        }

        push @players, {
            ZONE_ID     => $id,
            ZONE_NAME   => $name,
            ZONE_TITLE  => $title,
            ZONE_ARTIST => $artist,
            ZONE_STATE  => $state,
            ZONE_STATION=> $station,
            LOCAL_COVER => $local_cover,
            PLAYER_URL  => "/admin/plugins/$lbpplugindir/player.cgi?zone=$id",
        };
    }
};

# Fallback
if (!@players) {
    push @players, {
        ZONE_NAME   => "Keine Player gefunden",
        ZONE_TITLE  => "",
        ZONE_ARTIST => "",
        ZONE_STATE  => "",
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

@branches = ( { TAG => "main", SELECTED => 1 } ) unless @branches;

# --- Template laden ---
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
    LOGS          => $logs,
    PLAYERS       => \@players,
    VERSIONS      => \@branches,
    CURRENTBRANCH => $current_branch,
    SERVERHOST    => $serverhost,
    SERVERPORT    => $serverport,
    PLUGINVERSION => LoxBerry::System::pluginversion(),
);

# --- Ausgabe ---
LoxBerry::Web::lbheader("Lox-Audioserver + Music Assistant", "", "");
print $templateout->output();
LoxBerry::Web::lbfooter();
