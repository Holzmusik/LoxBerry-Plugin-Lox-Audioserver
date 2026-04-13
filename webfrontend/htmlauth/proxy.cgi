#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use LWP::UserAgent;
use URI;

my $cgi = CGI->new;

# --- IP-Adresse des LoxBerry ermitteln ---
my $host = $cgi->param('host');
if (!$host) {
    $host = `hostname -I | awk '{print \$1}'`;
    chomp $host;
}

# --- Port setzen ---
my $port = $cgi->param('port') || '7090';
my $base = "http://$host:$port";

# --- Pfad aus path_info ---
my $path = $cgi->path_info();
$path = '/' if !defined($path) || $path eq '';

# --- Query-String bereinigen ---
my $query = $ENV{'QUERY_STRING'} ? "?$ENV{'QUERY_STRING'}" : '';
$query =~ s/(^|&)host=[^&]+//g;
$query =~ s/(^|&)port=[^&]+//g;
$query =~ s/^&//;
$query = $query ? "?$query" : '';

# --- Ziel-URL zusammenbauen ---
my $url = "$base$path$query";

# --- Request senden ---
my $ua = LWP::UserAgent->new(
    timeout      => 15,
    max_redirect => 5,
    agent        => 'LoxBerry-Proxy/1.0'
);

my $res;
if ($ENV{'REQUEST_METHOD'} eq 'POST') {
    my $content;
    read(STDIN, $content, $ENV{'CONTENT_LENGTH'}) if $ENV{'CONTENT_LENGTH'};
    $res = $ua->post($url, Content => $content, 'Content-Type' => $ENV{'CONTENT_TYPE'});
} else {
    $res = $ua->get($url);
}

# --- Redirect manuell behandeln ---
if ($res->code == 302 || $res->code == 301) {
    my $loc = $res->header('Location') || '';
    $loc =~ s/;;.*$//;
    $loc = URI->new_abs($loc, $url)->as_string;
    $res = $ua->get($loc);
}

# --- Antwort ausgeben ---
if ($res->is_success) {
    my $ctype = $res->header('Content-Type') || 'text/html';
    print "Content-Type: $ctype\n\n";

    my $content;
    if ($ctype =~ m{text/html}) {
        $content = $res->decoded_content;

        # href/src/action absolut machen
        $content =~ s{(href|src|action)=\"/(?!/)}{$1=\"$base/}gi;

        # CSS url(...) absolut machen
        $content =~ s{url\((['\"]?)/}{$1$base/}gi;

        # X-Frame-Options entfernen (falls vorhanden)
        $content =~ s{<meta[^>]*http-equiv=["']X-Frame-Options["'][^>]*>}{}gi;
    } else {
        $content = $res->content;
    }

    binmode STDOUT;
    print $content;

} else {
    print "Content-Type: text/html\n\n";
    print "<h2>Fehler beim Laden der Admin-Seite</h2>";
    print "<p>Status: " . $res->status_line . "</p>";
    print "<p>URL: $url</p>";
}
