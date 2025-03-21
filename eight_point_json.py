import json


def load_clans():
    JSON_FILE = "eight_point_clans.json"
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)         
            eight_point_clans = data.get("eight_point_clans", [])
            return eight_point_clans
    except FileNotFoundError:
        return []

def save_clans(clans):
    JSON_FILE = "eight_point_clans.json"
    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump({"eight_point_clans": clans}, file, indent=4)
        