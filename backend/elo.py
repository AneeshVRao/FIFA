"""
elo.py — Rolling Elo Rating Engine

Implements the standard international football Elo system with a
K-factor of 32 and home-advantage bonus of 100 points.  The engine
processes matches chronologically and updates ratings in-place.

Key public functions
--------------------
build_initial_elo(df)       -> dict[str, float]
    Compute baseline Elo ratings for every team from historical data.

update_elo(ratings, match)  -> dict
    Apply a single match result to the ratings dictionary.

recalculate_from_date(ratings, fixtures, date_str) -> tuple
    Re-run Elo from a simulated date, returning updated ratings
    and list of match dicts with outcomes attached.
"""

import copy
import math
import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────
DEFAULT_ELO = 1500.0
K_FACTOR = 32.0
HOME_ADVANTAGE = 100.0


def _expected_score(rating_a: float, rating_b: float) -> float:
    """Return the expected score (0–1) for team A against team B."""
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))


def _actual_score(home_goals: int, away_goals: int) -> tuple[float, float]:
    """Return (home_actual, away_actual) where 1 = win, 0.5 = draw."""
    if home_goals > away_goals:
        return (1.0, 0.0)
    if home_goals < away_goals:
        return (0.0, 1.0)
    return (0.5, 0.5)


def _goal_diff_multiplier(goal_diff: int) -> float:
    """FIFA-style goal-difference multiplier.

    Higher margins create bigger swings, capped for extreme blowouts.
    """
    diff = abs(goal_diff)
    if diff <= 1:
        return 1.0
    if diff == 2:
        return 1.5
    return (11 + diff) / 8.0


# ── public API ───────────────────────────────────────────────────
def build_initial_elo(
    df: pd.DataFrame, lookback_years: int = 8
) -> dict[str, float]:
    """Compute Elo ratings for every team in the historical dataset.

    Only the last ``lookback_years`` of matches are used so that the
    ratings reflect recent form rather than results from decades ago.

    Parameters
    ----------
    df : pd.DataFrame
        Historical results (must contain *date*, *home_team*,
        *away_team*, *home_score*, *away_score*, *neutral*).
    lookback_years : int
        Number of years of history to include.

    Returns
    -------
    dict[str, float]
        Mapping of team name → Elo rating.
    """
    cutoff = df["date"].max() - pd.DateOffset(years=lookback_years)
    recent = df[df["date"] >= cutoff].sort_values("date")

    ratings: dict[str, float] = {}

    for _, row in recent.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        is_neutral = bool(row.get("neutral", False))

        ratings.setdefault(home, DEFAULT_ELO)
        ratings.setdefault(away, DEFAULT_ELO)

        home_elo = ratings[home] + (0 if is_neutral else HOME_ADVANTAGE)
        away_elo = ratings[away]

        expected_home = _expected_score(home_elo, away_elo)
        expected_away = 1.0 - expected_home

        actual_home, actual_away = _actual_score(
            int(row["home_score"]), int(row["away_score"])
        )
        goal_diff = int(row["home_score"]) - int(row["away_score"])
        multiplier = _goal_diff_multiplier(goal_diff)

        ratings[home] += K_FACTOR * multiplier * (actual_home - expected_home)
        ratings[away] += K_FACTOR * multiplier * (actual_away - expected_away)

    logger.info(
        "Built Elo ratings for %d teams from %d matches",
        len(ratings),
        len(recent),
    )
    return ratings


def update_elo(
    ratings: dict[str, float],
    home_team: str,
    away_team: str,
    home_goals: int,
    away_goals: int,
    is_neutral: bool = True,
) -> dict[str, float]:
    """Apply a single match result and return the updated ratings dict.

    Parameters
    ----------
    ratings : dict
        Current Elo ratings (modified in-place **and** returned).
    home_team, away_team : str
        Team names.
    home_goals, away_goals : int
        Final score.
    is_neutral : bool
        Whether the match is on neutral ground (World Cup = True).

    Returns
    -------
    dict
        The same ``ratings`` dictionary after the update.
    """
    ratings.setdefault(home_team, DEFAULT_ELO)
    ratings.setdefault(away_team, DEFAULT_ELO)

    home_elo = ratings[home_team] + (0 if is_neutral else HOME_ADVANTAGE)
    away_elo = ratings[away_team]

    expected_home = _expected_score(home_elo, away_elo)
    expected_away = 1.0 - expected_home

    actual_home, actual_away = _actual_score(home_goals, away_goals)
    goal_diff = home_goals - away_goals
    multiplier = _goal_diff_multiplier(goal_diff)

    ratings[home_team] += K_FACTOR * multiplier * (actual_home - expected_home)
    ratings[away_team] += K_FACTOR * multiplier * (actual_away - expected_away)

    return ratings


def predict_match(
    ratings: dict[str, float],
    home_team: str,
    away_team: str,
    is_neutral: bool = True,
) -> dict[str, float]:
    """Return win/draw/loss probabilities using Elo difference.

    Uses a Poisson-style approximation for goal expectations to
    split draw probability from a simple expected-score value.

    Returns
    -------
    dict
        ``{"home_win": float, "draw": float, "away_win": float}``
        where values sum to ~1.0.
    """
    ratings.setdefault(home_team, DEFAULT_ELO)
    ratings.setdefault(away_team, DEFAULT_ELO)

    home_elo = ratings[home_team] + (0 if is_neutral else HOME_ADVANTAGE)
    away_elo = ratings[away_team]

    elo_diff = home_elo - away_elo

    # Derive expected goals from Elo difference
    avg_goals = 1.35  # average goals per team in WC
    home_xg = avg_goals * 10 ** (elo_diff / 800.0)
    away_xg = avg_goals * 10 ** (-elo_diff / 800.0)

    # Cap extreme values
    home_xg = min(max(home_xg, 0.2), 5.0)
    away_xg = min(max(away_xg, 0.2), 5.0)

    # Poisson draw probability
    draw_prob = 0.0
    for k in range(8):
        p_home_k = (home_xg ** k) * np.exp(-home_xg) / math.factorial(k)
        p_away_k = (away_xg ** k) * np.exp(-away_xg) / math.factorial(k)
        draw_prob += p_home_k * p_away_k

    # Remaining probability split by Elo expected score
    expected_home = _expected_score(home_elo, away_elo)
    remaining = 1.0 - draw_prob
    home_win = remaining * expected_home
    away_win = remaining * (1.0 - expected_home)

    return {
        "home_win": round(home_win, 4),
        "draw": round(draw_prob, 4),
        "away_win": round(away_win, 4),
    }


def simulate_score(
    ratings: dict[str, float],
    home_team: str,
    away_team: str,
    is_neutral: bool = True,
    rng: np.random.Generator | None = None,
) -> tuple[int, int]:
    """Simulate a single match scoreline using Poisson distributions.

    Parameters
    ----------
    ratings : dict
        Current Elo ratings.
    home_team, away_team : str
        Team names.
    is_neutral : bool
        True for World Cup matches.
    rng : np.random.Generator or None
        Seeded generator for reproducibility.

    Returns
    -------
    tuple[int, int]
        (home_goals, away_goals)
    """
    if rng is None:
        rng = np.random.default_rng()

    ratings.setdefault(home_team, DEFAULT_ELO)
    ratings.setdefault(away_team, DEFAULT_ELO)

    home_elo = ratings[home_team] + (0 if is_neutral else HOME_ADVANTAGE)
    away_elo = ratings[away_team]
    elo_diff = home_elo - away_elo

    avg_goals = 1.35
    home_xg = avg_goals * 10 ** (elo_diff / 800.0)
    away_xg = avg_goals * 10 ** (-elo_diff / 800.0)

    home_xg = min(max(home_xg, 0.2), 5.0)
    away_xg = min(max(away_xg, 0.2), 5.0)

    home_goals = int(rng.poisson(home_xg))
    away_goals = int(rng.poisson(away_xg))

    return (home_goals, away_goals)


# ── quick self-test ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from backend.data_loader import load_results

    print("== Testing Elo engine ==")
    df = load_results()
    ratings = build_initial_elo(df)

    # Show top 20 teams
    top = sorted(ratings.items(), key=lambda x: x[1], reverse=True)[:20]
    for rank, (team, elo) in enumerate(top, 1):
        print(f"  {rank:>2}. {team:<25s}  {elo:7.1f}")

    # Predict a sample match
    probs = predict_match(ratings, "Brazil", "Germany")
    print(f"\nBrazil vs Germany: {probs}")

    # Simulate a score
    score = simulate_score(ratings, "Brazil", "Germany", rng=np.random.default_rng(42))
    print(f"Simulated score: Brazil {score[0]} - {score[1]} Germany")
