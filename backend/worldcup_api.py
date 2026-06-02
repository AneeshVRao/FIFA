"""
worldcup_api.py — FIFA World Cup 2026 Roster API Client

Integrates with https://worldcupapi.com/ to fetch player rosters.
If the API key is not present or if the API call fails, it falls back
to a curated mock roster database for all 48 teams.
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

WORLDCUP_API_KEY = os.getenv("WORLDCUP_API_KEY")
API_BASE_URL = "https://worldcupapi.com"

# Curated mock squads for key teams
MOCK_SQUADS = {
    "England": [
        {"name": "Harry Kane", "position": "FW", "number": 9, "club": "Bayern Munich", "age": 32},
        {"name": "Jude Bellingham", "position": "MF", "number": 10, "club": "Real Madrid", "age": 22},
        {"name": "Bukayo Saka", "position": "FW", "number": 7, "club": "Arsenal", "age": 24},
        {"name": "Declan Rice", "position": "MF", "number": 4, "club": "Arsenal", "age": 27},
        {"name": "Phil Foden", "position": "MF", "number": 11, "club": "Manchester City", "age": 26},
        {"name": "John Stones", "position": "DF", "number": 5, "club": "Manchester City", "age": 32},
        {"name": "Kyle Walker", "position": "DF", "number": 2, "club": "Manchester City", "age": 36},
        {"name": "Jordan Pickford", "position": "GK", "number": 1, "club": "Everton", "age": 32},
    ],
    "Argentina": [
        {"name": "Lionel Messi", "position": "FW", "number": 10, "club": "Inter Miami", "age": 38},
        {"name": "Lautaro Martinez", "position": "FW", "number": 22, "club": "Inter Milan", "age": 28},
        {"name": "Angel Di Maria", "position": "FW", "number": 11, "club": "Benfica", "age": 38},
        {"name": "Alexis Mac Allister", "position": "MF", "number": 20, "club": "Liverpool", "age": 27},
        {"name": "Enzo Fernandez", "position": "MF", "number": 24, "club": "Chelsea", "age": 25},
        {"name": "Rodrigo De Paul", "position": "MF", "number": 7, "club": "Atletico Madrid", "age": 32},
        {"name": "Cristian Romero", "position": "DF", "number": 13, "club": "Tottenham", "age": 28},
        {"name": "Emiliano Martinez", "position": "GK", "number": 1, "club": "Aston Villa", "age": 33},
    ],
    "France": [
        {"name": "Kylian Mbappe", "position": "FW", "number": 10, "club": "Real Madrid", "age": 27},
        {"name": "Antoine Griezmann", "position": "FW", "number": 7, "club": "Atletico Madrid", "age": 35},
        {"name": "Ousmane Dembele", "position": "FW", "number": 11, "club": "PSG", "age": 29},
        {"name": "Aurelien Tchouameni", "position": "MF", "number": 8, "club": "Real Madrid", "age": 26},
        {"name": "Eduardo Camavinga", "position": "MF", "number": 6, "club": "Real Madrid", "age": 23},
        {"name": "William Saliba", "position": "DF", "number": 4, "club": "Arsenal", "age": 25},
        {"name": "Theo Hernandez", "position": "DF", "number": 22, "club": "AC Milan", "age": 28},
        {"name": "Mike Maignan", "position": "GK", "number": 1, "club": "AC Milan", "age": 30},
    ],
    "Brazil": [
        {"name": "Vinicius Junior", "position": "FW", "number": 7, "club": "Real Madrid", "age": 25},
        {"name": "Rodrygo Goes", "position": "FW", "number": 10, "club": "Real Madrid", "age": 25},
        {"name": "Raphinha", "position": "FW", "number": 11, "club": "Barcelona", "age": 29},
        {"name": "Bruno Guimaraes", "position": "MF", "number": 5, "club": "Newcastle United", "age": 28},
        {"name": "Lucas Paqueta", "position": "MF", "number": 8, "club": "West Ham", "age": 28},
        {"name": "Marquinhos Aoas", "position": "DF", "number": 4, "club": "PSG", "age": 32},
        {"name": "Eder Militao", "position": "DF", "number": 3, "club": "Real Madrid", "age": 28},
        {"name": "Alisson Becker", "position": "GK", "number": 1, "club": "Liverpool", "age": 33},
    ],
    "Portugal": [
        {"name": "Cristiano Ronaldo", "position": "FW", "number": 7, "club": "Al Nassr", "age": 41},
        {"name": "Rafael Leao", "position": "FW", "number": 17, "club": "AC Milan", "age": 26},
        {"name": "Bruno Fernandes", "position": "MF", "number": 8, "club": "Manchester United", "age": 31},
        {"name": "Bernardo Silva", "position": "MF", "number": 10, "club": "Manchester City", "age": 31},
        {"name": "Vitinha", "position": "MF", "number": 23, "club": "PSG", "age": 26},
        {"name": "Ruben Dias", "position": "DF", "number": 4, "club": "Manchester City", "age": 29},
        {"name": "Joao Cancelo", "position": "DF", "number": 2, "club": "Al Hilal", "age": 32},
        {"name": "Diogo Costa", "position": "GK", "number": 1, "club": "FC Porto", "age": 26},
    ],
    "Spain": [
        {"name": "Alvaro Morata", "position": "FW", "number": 7, "club": "AC Milan", "age": 33},
        {"name": "Lamine Yamal", "position": "FW", "number": 19, "club": "Barcelona", "age": 18},
        {"name": "Nico Williams", "position": "FW", "number": 17, "club": "Athletic Bilbao", "age": 23},
        {"name": "Pedri Gonzalez", "position": "MF", "number": 20, "club": "Barcelona", "age": 23},
        {"name": "Rodri Hernandez", "position": "MF", "number": 16, "club": "Manchester City", "age": 29},
        {"name": "Dani Carvajal", "position": "DF", "number": 2, "club": "Real Madrid", "age": 34},
        {"name": "Robin Le Normand", "position": "DF", "number": 3, "club": "Atletico Madrid", "age": 29},
        {"name": "Unai Simon", "position": "GK", "number": 1, "club": "Athletic Bilbao", "age": 29},
    ],
    "Germany": [
        {"name": "Kai Havertz", "position": "FW", "number": 7, "club": "Arsenal", "age": 26},
        {"name": "Jamal Musiala", "position": "MF", "number": 10, "club": "Bayern Munich", "age": 23},
        {"name": "Florian Wirtz", "position": "MF", "number": 17, "club": "Bayer Leverkusen", "age": 23},
        {"name": "Ilkay Gundogan", "position": "MF", "number": 21, "club": "Manchester City", "age": 35},
        {"name": "Joshua Kimmich", "position": "MF", "number": 6, "club": "Bayern Munich", "age": 31},
        {"name": "Antonio Rudiger", "position": "DF", "number": 2, "club": "Real Madrid", "age": 33},
        {"name": "Jonathan Tah", "position": "DF", "number": 4, "club": "Bayer Leverkusen", "age": 30},
        {"name": "Marc-Andre ter Stegen", "position": "GK", "number": 1, "club": "Barcelona", "age": 34},
    ],
    "United States": [
        {"name": "Christian Pulisic", "position": "FW", "number": 10, "club": "AC Milan", "age": 27},
        {"name": "Folarin Balogun", "position": "FW", "number": 20, "club": "Monaco", "age": 24},
        {"name": "Timothy Weah", "position": "FW", "number": 11, "club": "Juventus", "age": 26},
        {"name": "Weston McKennie", "position": "MF", "number": 8, "club": "Juventus", "age": 27},
        {"name": "Tyler Adams", "position": "MF", "number": 4, "club": "Bournemouth", "age": 27},
        {"name": "Antonee Robinson", "position": "DF", "number": 5, "club": "Fulham", "age": 28},
        {"name": "Chris Richards", "position": "DF", "number": 3, "club": "Crystal Palace", "age": 26},
        {"name": "Matt Turner", "position": "GK", "number": 1, "club": "Crystal Palace", "age": 32},
    ],
    "Mexico": [
        {"name": "Santiago Gimenez", "position": "FW", "number": 11, "club": "Feyenoord", "age": 25},
        {"name": "Hirving Lozano", "position": "FW", "number": 22, "club": "San Diego FC", "age": 30},
        {"name": "Edson Alvarez", "position": "MF", "number": 4, "club": "West Ham", "age": 28},
        {"name": "Luis Chavez", "position": "MF", "number": 14, "club": "Dynamo Moscow", "age": 30},
        {"name": "Orbelin Pineda", "position": "MF", "number": 17, "club": "AEK Athens", "age": 30},
        {"name": "Cesar Montes", "position": "DF", "number": 3, "club": "Lokomotiv Moscow", "age": 29},
        {"name": "Johan Vasquez", "position": "DF", "number": 5, "club": "Genoa", "age": 27},
        {"name": "Luis Malagon", "position": "GK", "number": 1, "club": "Club America", "age": 29},
    ],
    "Canada": [
        {"name": "Jonathan David", "position": "FW", "number": 9, "club": "Lille", "age": 26},
        {"name": "Cyle Larin", "position": "FW", "number": 17, "club": "Mallorca", "age": 31},
        {"name": "Alphonso Davies", "position": "DF", "number": 19, "club": "Bayern Munich", "age": 25},
        {"name": "Stephen Eustaquio", "position": "MF", "number": 7, "club": "FC Porto", "age": 29},
        {"name": "Ismael Kone", "position": "MF", "number": 8, "club": "Marseille", "age": 23},
        {"name": "Alistair Johnston", "position": "DF", "number": 2, "club": "Celtic", "age": 27},
        {"name": "Moise Bombito", "position": "DF", "number": 15, "club": "Nice", "age": 26},
        {"name": "Maxime Crepeau", "position": "GK", "number": 1, "club": "Portland Timbers", "age": 32},
    ],
}

def generate_generic_squad(team_name: str) -> list[dict]:
    """Generate a realistic squad list for teams that do not have curated mock rosters."""
    pos_map = {
        1: ("GK", "Goalkeeper"),
        2: ("DF", "Defender"),
        3: ("DF", "Defender"),
        4: ("DF", "Defender"),
        5: ("MF", "Midfielder"),
        6: ("MF", "Midfielder"),
        7: ("FW", "Forward"),
        8: ("FW", "Forward"),
    }
    
    squad = []
    for num, (pos, name_type) in pos_map.items():
        squad.append({
            "name": f"{team_name} {name_type} {num}",
            "position": pos,
            "number": num,
            "club": f"Local League FC",
            "age": 24 + num % 5
        })
    return squad

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")

FOOTBALL_DATA_IDS = {
    "Argentina": 762, "France": 773, "England": 770, "Portugal": 765,
    "Brazil": 764, "Spain": 760, "Germany": 759, "United States": 772,
    "Mexico": 769, "Canada": 768
}

def get_squad_from_football_data(team_name: str) -> list[dict] | None:
    if not FOOTBALL_DATA_API_KEY or team_name not in FOOTBALL_DATA_IDS:
        return None
    try:
        team_id = FOOTBALL_DATA_IDS[team_name]
        url = f"https://api.football-data.org/v4/teams/{team_id}"
        headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
        logger.info("Fetching roster for %s from football-data.org...", team_name)
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            squad = data.get("squad", [])
            mapped = []
            for idx, p in enumerate(squad, start=1):
                mapped.append({
                    "name": p.get("name"),
                    "position": (p.get("position") or "MF")[0:2].upper(),
                    "number": p.get("shirtNumber") or idx,
                    "club": p.get("club") or data.get("shortName", "Unknown"),
                    "age": 25
                })
            return mapped
    except Exception as e:
        logger.warning("football-data.org fetch failed: %s", e)
    return None

def get_squad_from_balldontlie(team_name: str) -> list[dict] | None:
    if not BALLDONTLIE_API_KEY:
        return None
    try:
        headers = {"Authorization": BALLDONTLIE_API_KEY}
        url = "https://api.balldontlie.io/fifa/v1/rosters"
        params = {"team": team_name}
        logger.info("Fetching roster for %s from balldontlie...", team_name)
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            players = data.get("data", [])
            if players:
                mapped = []
                for idx, p in enumerate(players, start=1):
                    mapped.append({
                        "name": p.get("name") or p.get("player_name"),
                        "position": (p.get("position") or "MF")[0:2].upper(),
                        "number": p.get("number") or idx,
                        "club": p.get("club_name") or "Unknown",
                        "age": p.get("age") or 25
                    })
                return mapped
    except Exception as e:
        logger.warning("balldontlie fetch failed: %s", e)
    return None

def get_squad(team_name: str) -> list[dict]:
    """Fetch the squad list for a team, falling back to other APIs or mock data if key/API is unavailable."""
    # 1. Try WorldCupAPI
    if WORLDCUP_API_KEY:
        try:
            url = f"{API_BASE_URL}/squads"
            params = {
                "key": WORLDCUP_API_KEY,
                "team": team_name
            }
            logger.info("Fetching roster for %s from WorldCupAPI...", team_name)
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data
                elif isinstance(data, dict) and "squad" in data:
                    return data["squad"]
        except requests.RequestException as exc:
            logger.warning("Failed to fetch from WorldCupAPI: %s. Trying other APIs.", exc)

    # 2. Try football-data.org
    fd_squad = get_squad_from_football_data(team_name)
    if fd_squad:
        return fd_squad

    # 3. Try balldontlie
    bdl_squad = get_squad_from_balldontlie(team_name)
    if bdl_squad:
        return bdl_squad
            
    # Fallback to curated mocks
    if team_name in MOCK_SQUADS:
        return MOCK_SQUADS[team_name]
    return generate_generic_squad(team_name)
