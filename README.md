# [8Point Discord Bot](https://link.clashofclans.com/en/?action=OpenClanProfile&tag=298QPUCCC)

## Inhalt
- [Verwendung](#Verwendung)
- [Befehle](#Befehle)


## Verwendung
Um de nBot zu starten, wird ein [Discord bot](https://discord.com/developers/applications) benötigt, von diesem Braucht man dann den Token. 
Auch wird einer [Clash of Clans API](https://developer.clashofclans.com/#/) benötigt. Und eine Server ID/ Guild ID, welche man aus discord kopieren kann.
Diese 3 Sachen setzt man dann in eine .env datei, welche sich relativ gesehen in dem Überordern des Programms befidnen muss.
```
  bot_token=Discord bot token
  API=Clash of clans API
  guildIDs=guild IDs(server ids) von Discord mit , seperriert
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
- Vize Anführer
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
- 8Point Clans anzeigen
- Eigene Clan-Kürzel eingeben (mit Komma getrennt)
