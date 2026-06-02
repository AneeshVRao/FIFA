"""
player_similarity.py — Vector Similarity Recruiter Engine

Computes cosine similarity between 10-dimensional performance profiles of active
2026 tournament roster players and historical World Cup legends.
10D Vector profile dimensions:
  [Goals/90, Assists/90, Pass Completion %, Key Passes, Progressive Carries,
   Tackles, Interceptions, Pressures, Shots, xG]
"""

import hashlib
import numpy as np
import logging

logger = logging.getLogger(__name__)

# List of historical legends and their 10D profiles
HISTORICAL_PLAYERS = {
    "Pele": {
        "name": "Pelé",
        "era": "1958 - 1970",
        "country": "Brazil",
        "position": "FW",
        "club": "Santos FC",
        # [Goals/90, Assists/90, Pass %, Key Passes, Prog Carries, Tackles, Interceptions, Pressures, Shots, xG]
        "vector": [1.12, 0.48, 81.5, 3.2, 4.8, 0.8, 0.4, 6.2, 4.8, 0.95],
    },
    "Diego Maradona": {
        "name": "Diego Maradona",
        "era": "1982 - 1994",
        "country": "Argentina",
        "position": "MF",
        "club": "Napoli",
        "vector": [0.65, 0.72, 85.0, 4.5, 7.2, 1.2, 0.8, 8.4, 3.5, 0.58],
    },
    "Zinedine Zidane": {
        "name": "Zinedine Zidane",
        "era": "1998 - 2006",
        "country": "France",
        "position": "MF",
        "club": "Real Madrid",
        "vector": [0.38, 0.55, 91.2, 3.8, 5.2, 1.8, 1.1, 14.5, 2.5, 0.32],
    },
    "Ronaldo Nazario": {
        "name": "Ronaldo Nazário",
        "era": "1994 - 2006",
        "country": "Brazil",
        "position": "FW",
        "club": "Real Madrid",
        "vector": [0.94, 0.32, 79.8, 2.1, 6.1, 0.5, 0.3, 5.0, 4.6, 0.88],
    },
    "Johan Cruyff": {
        "name": "Johan Cruyff",
        "era": "1974",
        "country": "Netherlands",
        "position": "FW",
        "club": "Barcelona",
        "vector": [0.72, 0.82, 87.2, 4.8, 8.0, 1.5, 1.0, 12.0, 3.8, 0.68],
    },
    "Ronaldinho": {
        "name": "Ronaldinho Gaucho",
        "era": "2002 - 2006",
        "country": "Brazil",
        "position": "FW",
        "club": "Barcelona",
        "vector": [0.48, 0.68, 84.1, 4.2, 6.8, 1.0, 0.7, 9.8, 3.2, 0.42],
    },
    "Lothar Matthaeus": {
        "name": "Lothar Matthäus",
        "era": "1982 - 1998",
        "country": "Germany",
        "position": "MF",
        "club": "Bayern Munich",
        "vector": [0.28, 0.35, 88.5, 2.8, 4.2, 3.2, 2.8, 22.4, 2.2, 0.22],
    },
    "Paolo Maldini": {
        "name": "Paolo Maldini",
        "era": "1990 - 2002",
        "country": "Italy",
        "position": "DF",
        "club": "AC Milan",
        "vector": [0.03, 0.08, 89.4, 0.8, 2.1, 3.8, 3.2, 11.2, 0.4, 0.02],
    },
    "Franz Beckenbauer": {
        "name": "Franz Beckenbauer",
        "era": "1966 - 1974",
        "country": "Germany",
        "position": "DF",
        "club": "Bayern Munich",
        "vector": [0.18, 0.28, 92.1, 2.2, 4.8, 2.8, 3.5, 12.8, 1.2, 0.12],
    },
    "Miroslav Klose": {
        "name": "Miroslav Klose",
        "era": "2002 - 2014",
        "country": "Germany",
        "position": "FW",
        "club": "Lazio",
        "vector": [0.82, 0.21, 74.5, 1.2, 1.8, 0.8, 0.4, 15.2, 3.5, 0.78],
    },
    "Andrea Pirlo": {
        "name": "Andrea Pirlo",
        "era": "2006 - 2014",
        "country": "Italy",
        "position": "MF",
        "club": "Juventus",
        "vector": [0.12, 0.45, 93.8, 4.1, 2.5, 1.9, 1.5, 10.4, 1.1, 0.10],
    },
    "Andres Iniesta": {
        "name": "Andrés Iniesta",
        "era": "2006 - 2018",
        "country": "Spain",
        "position": "MF",
        "club": "Barcelona",
        "vector": [0.18, 0.42, 92.5, 3.4, 5.8, 1.7, 1.2, 14.8, 1.5, 0.18],
    },
    "Thierry Henry": {
        "name": "Thierry Henry",
        "era": "1998 - 2010",
        "country": "France",
        "position": "FW",
        "club": "Arsenal",
        "vector": [0.68, 0.42, 82.5, 2.8, 5.5, 0.6, 0.4, 7.8, 3.9, 0.62],
    },
    "Lev Yashin": {
        "name": "Lev Yashin",
        "era": "1958 - 1970",
        "country": "Soviet Union",
        "position": "GK",
        "club": "Dynamo Moscow",
        "vector": [0.0, 0.0, 68.0, 0.0, 0.1, 0.1, 0.1, 1.0, 0.0, 0.0],
    },
    "Gianluigi Buffon": {
        "name": "Gianluigi Buffon",
        "era": "1998 - 2014",
        "country": "Italy",
        "position": "GK",
        "club": "Juventus",
        "vector": [0.0, 0.01, 65.0, 0.0, 0.1, 0.1, 0.1, 1.0, 0.0, 0.0],
    },
    "Iker Casillas": {
        "name": "Iker Casillas",
        "era": "2002 - 2014",
        "country": "Spain",
        "position": "GK",
        "club": "Real Madrid",
        "vector": [0.0, 0.0, 72.0, 0.0, 0.1, 0.1, 0.1, 1.0, 0.0, 0.0],
    },
    "Manuel Neuer": {
        "name": "Manuel Neuer",
        "era": "2010 - 2022",
        "country": "Germany",
        "position": "GK",
        "club": "Bayern Munich",
        "vector": [0.0, 0.04, 78.0, 0.0, 0.3, 0.1, 0.1, 1.0, 0.0, 0.0],
    }
}


def get_player_vector_deterministically(name: str, position: str) -> list[float]:
    """Generate a highly realistic and consistent 10D profile vector based on player name hash."""
    # Seed using md5 hash of the player's name
    hasher = hashlib.md5(name.encode("utf-8"))
    seed = int(hasher.hexdigest(), 16) % 10000
    rng = np.random.default_rng(seed)
    
    # Establish realistic base metrics based on position
    if position == "FW":
        goals = rng.uniform(0.40, 0.95)
        assists = rng.uniform(0.15, 0.45)
        pass_pct = rng.uniform(73.0, 84.0)
        key_passes = rng.uniform(1.2, 2.8)
        prog_carries = rng.uniform(3.0, 5.5)
        tackles = rng.uniform(0.3, 1.0)
        interceptions = rng.uniform(0.1, 0.6)
        pressures = rng.uniform(6.0, 16.0)
        shots = rng.uniform(3.0, 5.0)
        xg = goals * rng.uniform(0.85, 1.1)
    elif position == "MF":
        goals = rng.uniform(0.10, 0.40)
        assists = rng.uniform(0.25, 0.70)
        pass_pct = rng.uniform(84.0, 93.0)
        key_passes = rng.uniform(2.5, 4.5)
        prog_carries = rng.uniform(4.0, 7.0)
        tackles = rng.uniform(1.2, 2.8)
        interceptions = rng.uniform(0.8, 2.2)
        pressures = rng.uniform(12.0, 24.0)
        shots = rng.uniform(1.0, 2.8)
        xg = goals * rng.uniform(0.9, 1.2)
    elif position == "DF":
        goals = rng.uniform(0.01, 0.15)
        assists = rng.uniform(0.02, 0.20)
        pass_pct = rng.uniform(82.0, 91.0)
        key_passes = rng.uniform(0.3, 1.5)
        prog_carries = rng.uniform(1.2, 3.5)
        tackles = rng.uniform(2.2, 4.5)
        interceptions = rng.uniform(1.8, 3.8)
        pressures = rng.uniform(10.0, 18.0)
        shots = rng.uniform(0.2, 1.1)
        xg = goals * rng.uniform(0.95, 1.2)
    else:  # GK or other
        goals = 0.0
        assists = rng.uniform(0.0, 0.05)
        pass_pct = rng.uniform(60.0, 75.0)
        key_passes = 0.0
        prog_carries = 0.1
        tackles = 0.1
        interceptions = 0.1
        pressures = 1.0
        shots = 0.0
        xg = 0.0

    # Specific overrides for superstar players in our mock squads
    if "Messi" in name:
        return [0.78, 0.85, 88.2, 5.1, 7.8, 0.6, 0.4, 6.2, 4.2, 0.72]
    elif "Mbappe" in name or "Mbappé" in name:
        return [0.92, 0.35, 82.1, 2.4, 6.8, 0.4, 0.2, 5.8, 4.8, 0.85]
    elif "Bellingham" in name:
        return [0.42, 0.38, 88.5, 2.8, 5.2, 2.4, 1.6, 20.2, 2.3, 0.38]
    elif "Haaland" in name:
        return [1.05, 0.12, 72.1, 0.8, 1.5, 0.3, 0.1, 8.4, 4.5, 0.98]
    elif "Yamal" in name:
        return [0.35, 0.58, 83.5, 3.6, 6.5, 1.2, 0.8, 14.2, 2.8, 0.30]
    elif "Ronaldo" in name and "Cristiano" in name:
        return [0.85, 0.20, 81.2, 1.8, 3.5, 0.4, 0.2, 4.8, 5.2, 0.80]

    return [
        round(goals, 2),
        round(assists, 2),
        round(pass_pct, 1),
        round(key_passes, 2),
        round(prog_carries, 2),
        round(tackles, 2),
        round(interceptions, 2),
        round(pressures, 2),
        round(shots, 2),
        round(xg, 2)
    ]


def calculate_cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two 10D vectors."""
    a = np.array(v1)
    b = np.array(v2)
    
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def get_position_penalty(pos1: str, pos2: str) -> float:
    """Return similarity penalty factor based on position mismatch."""
    if pos1 == pos2:
        return 1.0
    # Goalkeepers are completely isolated from outfield positions
    if pos1 == "GK" or pos2 == "GK":
        return 0.0
    # DF matching MF or vice versa (moderate compatibility)
    if (pos1 == "DF" and pos2 == "MF") or (pos1 == "MF" and pos2 == "DF"):
        return 0.7
    # MF matching FW or vice versa (moderate compatibility)
    if (pos1 == "MF" and pos2 == "FW") or (pos1 == "FW" and pos2 == "MF"):
        return 0.8
    # DF matching FW (very low compatibility)
    if (pos1 == "DF" and pos2 == "FW") or (pos1 == "FW" and pos2 == "DF"):
        return 0.4
    return 0.5


def find_similar_players(player_name: str, position: str = "FW") -> list[dict]:
    """Find top 5 closest historical analogues for an active player."""
    active_vector = get_player_vector_deterministically(player_name, position)
    
    similarities = []
    for hist_id, data in HISTORICAL_PLAYERS.items():
        sim_score = calculate_cosine_similarity(active_vector, data["vector"])
        penalty = get_position_penalty(position, data["position"])
        sim_score *= penalty
        
        if sim_score > 0:
            similarities.append({
                "name": data["name"],
                "era": data["era"],
                "country": data["country"],
                "position": data["position"],
                "club": data["club"],
                "vector": data["vector"],
                "similarity": round(sim_score, 4)
            })
        
    # Sort by similarity descending
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:5]


if __name__ == "__main__":
    # Self-test similarity finder
    print("== Testing Player Similarity Finder ==")
    matches = find_similar_players("Jude Bellingham", "MF")
    print("Top analogues for Jude Bellingham (MF):")
    for idx, m in enumerate(matches, start=1):
        print(f"  {idx}. {m['name']} ({m['country']}, {m['era']}) - Similarity: {m['similarity']*100:.2f}%")
    print("Done.")
