# Lox-Audioserver Plugin für LoxBerry

Dieses Plugin integriert den lox-audioserver nativ in LoxBerry und bietet eine einfache Weboberfläche zur Steuerung und Überwachung.

## 🔧 Funktionen

- Start / Stop / Restart des Audioservers direkt über das Webfrontend
- Anzeige des aktuellen Dienststatus
- Log-Ausgabe der letzten 20 Zeilen
- Branch-Wechsler für die Audioserver-Installation (inkl. Pull, Build und Restart)
- Link zur Admin-Oberfläche des Audioservers (`http://<loxberry>:7091/admin`)
- Vollständig LoxBerry-konform: keine Root-Rechte, keine `sudoers`-Anpassungen

## 📦 Installation

1. Plugin über das LoxBerry-Webinterface installieren (`lox-audioserver.zip`)
2. Express Plugin ab Version 0.0.3 muss installiert sein
3. Nach Installation wird der Audioserver automatisch gestartet

## 📁 Verzeichnisstruktur

lox-audioserver/ 
├── bin/ # Start-/Stop-Skripte 
├── config/ # Reserviert für spätere Konfiguration 
├── templates/ # Webfrontend (Handlebars) 
├── webfrontend/ # Express-Routing und Fallback 
├── plugin.cfg # Plugin-Metadaten 
├── postroot.sh # Installationsskript 
├── postupgrade.sh # Upgrade-Skript 
└── README.md


## 🧩 Hinweise

- Der Dienst wird über `/opt/loxberry/system/daemons/system/lox-audioserver` gestartet
- Die Logdatei befindet sich unter `/opt/loxberry/log/plugins/lox-audioserver/lox-audioserver.log`
- Branch-Wechsel erfolgt über `git checkout`, `npm install`, `npm run build`

## 🧪 Getestet mit

- LoxBerry 3.0.x
- Node.js ≥ 18
- lox-audioserver (eigene Installation im Plugin-Verzeichnis)

## 📬 Kontakt

Entwickler: Sascha  
Fragen, Feedback oder Erweiterungsvorschläge gerne über das LoxForum oder GitHub.
