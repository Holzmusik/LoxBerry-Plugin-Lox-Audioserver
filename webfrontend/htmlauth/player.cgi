#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LoxBerry::System;
use LWP::UserAgent;
use HTML::Template;
use JSON;
use File::Path qw(make_path);

my $cgi     = CGI->new;
my $zone_id = $cgi->param('zone') || 1;

# --- Defaultwerte ---
my ($title,$artist,$album,$time,$volume,$cover,$progress) = ("","","","","0","","0");

# --- Plugin-Konfiguration (wie in index.cgi) ---
my $plugin = "lox-audioserver";
my $cfgfile = "$lbpconfigdir/plugins/$lbpplugindir/plugin.cfg";
my ($serverhost, $serverport);
if (-e $cfgfile) {
    eval {
        require Config::Simple;
        my $cfg = Config::Simple->new($cfgfile);
        $serverhost = $cfg->param("SERVER.SERVERHOST");
        $serverport = $cfg->param("SERVER.SERVERPORT");
    };
}
$serverhost ||= `hostname -I | awk '{print \$1}'`;
chomp $serverhost;
$serverport ||= '7090';

# --- HTTP-Client ---
my $ua = LWP::UserAgent->new(timeout => 6);
$ua->agent("lox-audioserver-plugin/1.0");

# --- Versuche zuerst status.cgi, fallback auf API ---
my $body;
my $res;

my @try_urls = (
    "http://127.0.0.1/admin/plugins/$lbpplugindir/status.cgi?zone=$zone_id",
    "http://$serverhost:$serverport/admin/plugins/$lbpplugindir/status.cgi?zone=$zone_id",
    "http://$serverhost:$serverport/admin/api/zones/states",
    "http://$serverhost:$serverport/admin/api/zones",
);

foreach my $url (@try_urls) {
    $res = $ua->get($url);
    warn "Tried $url -> " . $res->status_line;
    if ($res->is_success) {
        $body = $res->decoded_content;
        # If we hit the zones API, we need to extract the single zone object
        if ($url =~ m{/admin/api/zones}) {
            my $data = eval { decode_json($body) };
            if ($data && ref $data->{zones} eq 'ARRAY') {
                foreach my $z (@{ $data->{zones} }) {
                    if (defined $z->{id} && "$z->{id}" eq "$zone_id") {
                        $body = encode_json($z);
                        last;
                    }
                }
            }
        }
        last if $body;
    }
}

unless ($body) {
    $title  = "Fehler beim Abruf von status.cgi/API";
    $artist = $res ? $res->status_line : "kein response";
}

# --- JSON parsen und tolerant Feldnamen lesen ---
if ($body) {
    eval {
        my $data = decode_json($body);

        # Mögliche Feldnamen abdecken
        $title  = $data->{title} // $data->{trackTitle} // $data->{station} // $title;
        $artist = $data->{artist} // $data->{trackArtist} // $artist;
        $album  = $data->{album} // $data->{trackAlbum} // $album;
        $time   = $data->{time} // $data->{positionMs} // $data->{elapsed} // $time;
        $volume = $data->{volume} // $data->{level} // $volume;

        # coverUrl oder coverurl
        my $coverurl = $data->{coverUrl} // $data->{coverurl} // $data->{artworkUrl} // '';

        # Falls API-Objekt mit session enthält, nutze session info
        if (!$title && $data->{session} && ref $data->{session} eq 'HASH') {
            $title = $data->{session}{title} // $title;
            $artist = $data->{session}{artist} // $artist;
            $time = $data->{session}{elapsed} // $time;
        }

        # Progress berechnen falls position/duration vorhanden
        my $position = $data->{positionMs} // $data->{position} // ($data->{session}{elapsed} // 0);
        my $duration = $data->{durationMs} // $data->{duration} // ($data->{session}{duration} // 0);
        if ($position && $duration) {
            $progress = int(($position / $duration) * 100);
        } elsif (defined $data->{progress}) {
            $progress = $data->{progress};
        } else {
            $progress = 0;
        }

        # Cover lokal speichern (nur wenn Bild)
        my $coverdir = "/opt/loxberry/webfrontend/html/plugins/$lbpplugindir/covers";
        my $coverfile = "$coverdir/zone$zone_id.png";
        my $local_cover = "/plugins/$lbpplugindir/covers/zone$zone_id.png";

        if ($coverurl) {
            make_path($coverdir) unless -d $coverdir;
            my $imgres = $ua->get($coverurl);
            if ($imgres->is_success) {
                my $ct = $imgres->header('Content-Type') // '';
                if ($ct =~ m{^image/}) {
                    if (open my $fh, '>', $coverfile) {
                        binmode $fh;
                        print $fh $imgres->content;
                        close $fh;
                        chmod 0644, $coverfile;
                        $cover = $local_cover;
                    } else {
                        warn "Konnte Cover $coverfile nicht schreiben: $!";
                        $cover = "/plugins/$lbpplugindir/images/default_cover.png";
                    }
                } else {
                    warn "Cover-URL liefert kein Bild ($coverurl) Content-Type: $ct";
                    $cover = "/plugins/$lbpplugindir/images/default_cover.png";
                }
            } else {
                warn "Cover-Download fehlgeschlagen für $coverurl -> " . $imgres->status_line;
                $cover = "/plugins/$lbpplugindir/images/default_cover.png";
            }
        } else {
            $cover = "/plugins/$lbpplugindir/images/default_cover.png";
        }
    };
    if ($@) {
        $title  = "Fehler beim JSON-Parsing";
        $artist = $@;
        $cover  = "/plugins/$lbpplugindir/images/default_cover.png";
    }
}

# --- Template laden ---
my $templatefile = "$lbphtmldir/templates/player.html";
my $template     = LoxBerry::System::read_file($templatefile);

my $templateout = HTML::Template->new_scalar_ref(
    \$template,
    global_vars       => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
);

# --- Variablen ins Template einsetzen ---
$templateout->param(
    ZONE_ID  => $zone_id,
    TITLE    => $title,
    ARTIST   => $artist,
    ALBUM    => $album,
    TIME     => $time,
    VOLUME   => $volume,
    COVER    => $cover,
    PROGRESS => $progress,
    REFRESH  => 10,
);

# --- Ausgabe ---
print "Content-Type: text/html\n\n";
print $templateout->output();
