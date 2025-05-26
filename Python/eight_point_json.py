import json
import os

path = os.path.join(os.path.dirname(__file__), 'eight_point_clans.json')

def load_clans():
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            eight_point_clans = data.get("eight_point_clans", [])
            return eight_point_clans
    except FileNotFoundError:
        return []


def save_clans(clans):
    with open(path, "w", encoding="utf-8") as file:  
        json.dump({"eight_point_clans": clans}, file, indent=4, ensure_ascii=False)
