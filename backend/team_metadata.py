"""
team_metadata.py — Squad Values & FIFA Rankings Points

Contains data-backed metrics for the 48 qualified World Cup 2026 teams.
Used to calculate the Unified Power Ratings and boost historical Elo ratings.
"""

TEAM_METADATA = {
    "England": {"squad_value": 1300, "fifa_rank": 4, "fifa_points": 1795},
    "France": {"squad_value": 1200, "fifa_rank": 2, "fifa_points": 1840},
    "Portugal": {"squad_value": 1000, "fifa_rank": 6, "fifa_points": 1748},
    "Brazil": {"squad_value": 950, "fifa_rank": 5, "fifa_points": 1785},
    "Spain": {"squad_value": 900, "fifa_rank": 3, "fifa_points": 1815},
    "Argentina": {"squad_value": 850, "fifa_rank": 1, "fifa_points": 1860},
    "Germany": {"squad_value": 750, "fifa_rank": 16, "fifa_points": 1645},
    "Netherlands": {"squad_value": 700, "fifa_rank": 7, "fifa_points": 1742},
    "Belgium": {"squad_value": 550, "fifa_rank": 8, "fifa_points": 1720},
    "Uruguay": {"squad_value": 480, "fifa_rank": 11, "fifa_points": 1665},
    "Norway": {"squad_value": 450, "fifa_rank": 47, "fifa_points": 1470},
    "United States": {"squad_value": 350, "fifa_rank": 13, "fifa_points": 1650},
    "Morocco": {"squad_value": 350, "fifa_rank": 12, "fifa_points": 1660},
    "Croatia": {"squad_value": 350, "fifa_rank": 9, "fifa_points": 1710},
    "Turkey": {"squad_value": 320, "fifa_rank": 40, "fifa_points": 1495},
    "Scotland": {"squad_value": 200, "fifa_rank": 39, "fifa_points": 1506},
    "Sweden": {"squad_value": 300, "fifa_rank": 28, "fifa_points": 1530},
    "Ivory Coast": {"squad_value": 300, "fifa_rank": 38, "fifa_points": 1500},
    "Switzerland": {"squad_value": 280, "fifa_rank": 19, "fifa_points": 1618},
    "Japan": {"squad_value": 280, "fifa_rank": 18, "fifa_points": 1620},
    "Austria": {"squad_value": 250, "fifa_rank": 25, "fifa_points": 1560},
    "Senegal": {"squad_value": 250, "fifa_rank": 17, "fifa_points": 1625},
    "Ecuador": {"squad_value": 220, "fifa_rank": 31, "fifa_points": 1518},
    "Mexico": {"squad_value": 200, "fifa_rank": 15, "fifa_points": 1648},
    "South Korea": {"squad_value": 180, "fifa_rank": 23, "fifa_points": 1572},
    "Ghana": {"squad_value": 180, "fifa_rank": 64, "fifa_points": 1380},
    "Canada": {"squad_value": 180, "fifa_rank": 49, "fifa_points": 1460},
    "Czech Republic": {"squad_value": 150, "fifa_rank": 36, "fifa_points": 1505},
    "Algeria": {"squad_value": 140, "fifa_rank": 43, "fifa_points": 1485},
    "Paraguay": {"squad_value": 130, "fifa_rank": 56, "fifa_points": 1420},
    "Egypt": {"squad_value": 120, "fifa_rank": 36, "fifa_points": 1502},
    "DR Congo": {"squad_value": 110, "fifa_rank": 61, "fifa_points": 1390},
    "Bosnia and Herzegovina": {"squad_value": 90, "fifa_rank": 74, "fifa_points": 1330},
    "Tunisia": {"squad_value": 60, "fifa_rank": 41, "fifa_points": 1490},
    "Australia": {"squad_value": 50, "fifa_rank": 24, "fifa_points": 1568},
    "Iran": {"squad_value": 50, "fifa_rank": 20, "fifa_points": 1610},
    "Uzbekistan": {"squad_value": 35, "fifa_rank": 66, "fifa_points": 1375},
    "Saudi Arabia": {"squad_value": 30, "fifa_rank": 53, "fifa_points": 1440},
    "Cape Verde": {"squad_value": 30, "fifa_rank": 65, "fifa_points": 1378},
    "South Africa": {"squad_value": 25, "fifa_rank": 59, "fifa_points": 1405},
    "Qatar": {"squad_value": 20, "fifa_rank": 35, "fifa_points": 1507},
    "New Zealand": {"squad_value": 20, "fifa_rank": 104, "fifa_points": 1200},
    "Panama": {"squad_value": 20, "fifa_rank": 45, "fifa_points": 1475},
    "Curacao": {"squad_value": 15, "fifa_rank": 90, "fifa_points": 1260},
    "Haiti": {"squad_value": 15, "fifa_rank": 85, "fifa_points": 1275},
    "Iraq": {"squad_value": 15, "fifa_rank": 58, "fifa_points": 1410},
    "Jordan": {"squad_value": 15, "fifa_rank": 71, "fifa_points": 1340},
    "Indonesia": {"squad_value": 15, "fifa_rank": 134, "fifa_points": 1100}
}

def get_unified_elo(team_name: str, baseline_elo: float) -> float:
    """Calculate the data-backed Unified Elo rating for a team."""
    if team_name in TEAM_METADATA:
        meta = TEAM_METADATA[team_name]
        boost = 0.1 * (meta["fifa_points"] - 1500) + 0.05 * meta["squad_value"]
        # Ensure ratings are floated precisely
        return round(float(baseline_elo + boost), 1)
    return round(float(baseline_elo), 1)
