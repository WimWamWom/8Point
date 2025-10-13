import requests
import os
import json
import logging
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)
# Fallback: auch lokale .env im Python-Ordner laden, falls oben nicht vorhanden
if not os.getenv('API'):
    local_env = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(local_env):
        load_dotenv(local_env)

API = os.getenv('API')
if not API:
    logging.error("Clash of Clans API-Token (API) ist nicht gesetzt. Bitte .env konfigurieren.")

def get_clan_info(clan_tag):
    # Tag normalisieren: '#' entfernen, Leerzeichen trimmen
    try:
        sanitized_tag = str(clan_tag).strip()
        if sanitized_tag.startswith('#'):
            sanitized_tag = sanitized_tag[1:]
    except Exception:
        return None

    url = f"https://api.clashofclans.com/v1/clans/%23{sanitized_tag}"
    headers = {
        'Authorization': f'Bearer {API}'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        logging.error(f"HTTP-Fehler beim Abrufen der Clan-Daten für #{sanitized_tag}: {e}")
        return None

    if response.status_code == 200:
        data = response.json()

        name = data['name']
        tag = data['tag']
        link = f"https://link.clashofclans.com/en/?action=OpenClanProfile&tag={tag[1:]}"
        
        beitritt = "Offen für Alle" if data['type'] == "open" else "Nur auf Einladung" if data['type'] == "inviteOnly" else "Geschlossen"
        ort = data.get('location', {}).get('countryCode', None)
        location = f":flag_{ort.lower()}:    " if ort else ""
        description = data['description']
        badge = data['badgeUrls']['large']
        clan_level = data['clanLevel']
        clan_points = data['clanPoints']
        clan_builder_base_points = data['clanBuilderBasePoints']
        capitalhall = data['clanCapital']['capitalHallLevel']
        capital_points = data['clanCapitalPoints']
        townhall = data['requiredTownhallLevel']
        trophies = data['requiredTrophies']
        members = data['members']
        leader = next((member['name'] for member in data['memberList'] if member['role'] == 'leader'), None)
        
        labels = [label['name'] for label in data.get('labels', [])][:3]
        tags = [label for label in labels]  # Translation code for tags can be added here

        warfrequency = {
            "unknown": "Nicht festgelegt",
            "always": "Immer",
            "more_than_once_per_week": "Zweimal pro Woche",
            "once_per_week": "Einmal pro Woche",
            "less_than_once_per_week": "Selten",
            "never": "Nie",
            "any": "Nicht festgelegt"
        }.get(data['warFrequency'], "Nicht festgelegt")

        warlogpublic = data['isWarLogPublic']
        winstreak = data.get('warWinStreak', 0)
        wins = data.get('warWins', 0)
        ties = data.get('warTies', 0)
        losses = data.get('warLosses', 0)
        siegsrate = round((wins / (wins + ties + losses)) * 100, 1) if (wins + ties + losses) > 0 else 0.0
        liga = data['warLeague']['name']

        return {
            "name": name,
            "tag": tag,
            "link": link,
            "description": description,
            "badge": badge,
            "clan_level": clan_level,
            "clan_points": clan_points,
            "clan_builder_base_points": clan_builder_base_points,
            "capitalhall": capitalhall,
            'capital_points': capital_points,
            "members": members,
            "tags": tags,
            "warfrequency": warfrequency,
            "warlogpublic": warlogpublic,
            "winstreak": winstreak,
            "war_wins": wins,
            "war_ties": ties,
            "war_losses": losses,
            "siegesrate": f"{siegsrate}%",
            "war_league": liga,
            "location": location,
            "beitritt": beitritt,
            "townhall": townhall,
            "trophies": trophies,
            "leader": leader,
        }
    else:
        # Nützliche Fehlermeldung loggen
        try:
            payload = response.json()
        except Exception:
            payload = response.text
        logging.error(f"Clash API {response.status_code} für Clan #{sanitized_tag}: {payload}")
        return None

def get_clan_name_and_tag(clan):
    clan_info = get_clan_info(clan)
    if not clan_info:
        return None
    return f"{clan_info['name']} ({clan_info['tag']})"

def refresh_rolls(clan_list):
    all_leaders = []
    all_coleaders = []
    all_elders = []
    all_members = []

    for clan_tag in clan_list:
        url = f"https://api.clashofclans.com/v1/clans/%23{clan_tag[1:]}"
        headers = {
            'Authorization': f'Bearer {API}'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Leader abrufen
            leader = next((member['name'] for member in data['memberList'] if member['role'] == 'leader'), None)
            # Co-Leader abrufen
            coleaders = [member['name'] for member in data.get('memberList', []) if member.get('role') == 'coLeader']
            elders = [member['name'] for member in data.get('memberList', []) if member.get('role') == 'admin']
            members = [member['name'] for member in data.get('memberList', []) if member.get('role') == 'member']
            # Leader und Co-Leader zur Liste hinzufügen
            all_leaders.append(leader)
            all_coleaders.extend(coleaders)
            all_elders.extend(elders)
            all_members.extend(members)

    # Liste alphabetisch sortieren

    all_leaders = sorted(all_leaders, key=lambda x: x.lower())
    all_coleaders = sorted(all_coleaders, key=lambda x: x.lower())
    all_elders = sorted(all_elders, key=lambda x: x.lower())
    all_members = sorted(all_members, key=lambda x: x.lower())

    data = {
        "leaders": all_leaders,
        "coleaders": all_coleaders,
        "elders": all_elders,
        "members": all_members
    }

    # Speichere das Dictionary als JSON-Datei
    with open('rolls.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

def load_rolls(roll):
    JSON_FILE = "rolls.json"
    try:
        if roll == "leader":
            with open(JSON_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                meber = data.get("leaders", [])
                return meber
        elif roll == "vize":
            with open(JSON_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                meber = data.get("coleaders", [])
                return meber
        elif roll == "elders":
            with open(JSON_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                meber = data.get("elders", [])
                return meber
        elif roll == "members":
            with open(JSON_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                meber = data.get("members", [])
                return meber
    except FileNotFoundError:
        return []