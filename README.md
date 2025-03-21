# [8Point Discord Bot](https://link.clashofclans.com/en/?action=OpenClanProfile&tag=298QPUCCC)

## Inhalt
- [Verwendung](#Verwendung)
- [Befehle](#Befehle)

## Verwendung
Um den Bot zu starten, wird ein [Discord Bot](https://discord.com/developers/applications) benötigt. Von diesem braucht man dann den Token.  
Auch wird eine [Clash of Clans API](https://developer.clashofclans.com/#/) benötigt sowie eine Server-ID/Guild-ID, die man aus Discord kopieren kann.  
Diese drei Dinge setzt man dann in eine `.env`-Datei, welche sich relativ gesehen im Überordner des Programms befinden muss.

```
bot_token=Discord Bot Token 
API=Clash of Clans API 
guildIDs=Guild IDs (Server-IDs) von Discord, mit , separiert
```

Außerdem benötigt man folgende zusätzliche Python-Bibliotheken:

```
pip install discord.py 
pip install python-dotenv 
pip install pytz 
pip install requests
```

## Befehle
- [/mitglieder](#mitglieder)
- [/8point-clans](#8point-clans)
- [/clan-übersicht](#clan-übersicht)

## /mitglieder
Zeigt eine Übersicht der Mitglieder der Clanfamilie.

**Erforderliche Parameter:**
- Alle Mitglieder
- Anführer
- Vize-Anführer
- Älteste
- Mitglieder

**Optionale Parameter:**
- Aktualisieren [Ja / Nein]

## /8point-clans
Verwaltet die 8Point-Clans.

**Aktionen:**
- Clans anzeigen
- Clan hinzufügen
- Clan entfernen

**Optionale Parameter:**
- Clan-Kürzel angeben (für Hinzufügen oder Entfernen)
- Position angeben (bei Hinzufügen)

## /clan-übersicht
Zeigt Informationen zu den Clans an.

**Optionen:**
- 8Point-Clans anzeigen
- Eigene Clan-Kürzel eingeben (mit Komma getrennt)
