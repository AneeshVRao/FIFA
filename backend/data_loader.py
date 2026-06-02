"""
data_loader.py — Historical Results Caching Parser

Downloads and parses the international football results dataset from
the martj42/international_results GitHub repository. Caches the CSV
locally in ``data/results.csv`` to avoid repeated downloads.

Columns returned:
    date, home_team, away_team, home_score, away_score, tournament, neutral
"""

import logging
import json
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_CSV = DATA_DIR / "results.csv"
FIXTURES_JSON = DATA_DIR / "fixtures_2026.json"
RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results"
    "/master/results.csv"
)

# ── team-name normalisation map ──────────────────────────────────
# The historical dataset sometimes uses variant spellings compared
# to the fixture list.  This map unifies them.
TEAM_NAME_MAP = {
    "Korea Republic": "South Korea",
    "Korea DPR": "North Korea",
    "Türkiye": "Turkey",
    "Czechia": "Czech Republic",
    "Cabo Verde": "Cape Verde",
    "Curaçao": "Curacao",
    "Côte d'Ivoire": "Ivory Coast",
    "IR Iran": "Iran",
    "Congo DR": "DR Congo",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "United States Virgin Islands": "US Virgin Islands",
}


def _normalise_team(name: str) -> str:
    """Return the canonical team name."""
    return TEAM_NAME_MAP.get(name, name)


def download_results(force: bool = False) -> Path:
    """Download results.csv from GitHub if it doesn't exist locally.

    Parameters
    ----------
    force : bool
        If True, re-download even when a cached copy exists.

    Returns
    -------
    Path
        The path to the local ``results.csv`` file.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if RESULTS_CSV.exists() and not force:
        logger.info("Using cached results.csv at %s", RESULTS_CSV)
        return RESULTS_CSV

    logger.info("Downloading results.csv from GitHub …")
    response = requests.get(RESULTS_URL, timeout=60)
    response.raise_for_status()
    RESULTS_CSV.write_bytes(response.content)
    logger.info("Saved results.csv (%d bytes)", len(response.content))
    return RESULTS_CSV


def load_results(cutoff_date: str = "2026-06-11") -> pd.DataFrame:
    """Load and return the historical results dataframe.

    Only rows *before* ``cutoff_date`` are included so that we never
    accidentally leak tournament results into the training set.

    Parameters
    ----------
    cutoff_date : str
        ISO-format date string (``YYYY-MM-DD``).  Defaults to the
        opening day of the 2026 World Cup.

    Returns
    -------
    pd.DataFrame
        Cleaned dataframe with normalised team names.
    """
    csv_path = download_results()
    df = pd.read_csv(csv_path)

    # Parse dates and filter
    df["date"] = pd.to_datetime(df["date"])
    cutoff = pd.Timestamp(cutoff_date)
    df = df[df["date"] < cutoff].copy()

    # Normalise team names
    df["home_team"] = df["home_team"].map(_normalise_team)
    df["away_team"] = df["away_team"].map(_normalise_team)

    # Drop rows with missing scores
    df = df.dropna(subset=["home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)

    logger.info(
        "Loaded %d historical matches (before %s)", len(df), cutoff_date
    )
    return df


def load_fixtures() -> list[dict]:
    """Load 2026 World Cup group-stage fixtures from the JSON seed.

    Returns
    -------
    list[dict]
        Each dict contains ``date``, ``group``, ``home``, ``away``, ``venue``.
    """
    with open(FIXTURES_JSON, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    fixtures = data["group_stage"]
    logger.info("Loaded %d group-stage fixtures", len(fixtures))
    return fixtures


def get_wc_teams() -> list[str]:
    """Return a sorted list of all 48 teams in the 2026 World Cup."""
    with open(FIXTURES_JSON, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    teams = set()
    for group_teams in data["groups"].values():
        teams.update(group_teams)

    return sorted(teams)


# ── quick self-test ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("-- Testing data_loader --")
    df = load_results()
    print(f"Historical results: {len(df)} rows")
    print(df.tail(3))

    fixtures = load_fixtures()
    print(f"\nWorld Cup fixtures: {len(fixtures)}")
    print(fixtures[0])

    teams = get_wc_teams()
    print(f"\nWC teams ({len(teams)}): {teams[:5]} …")
