"""
model_shootout.py — Penalty Shootout Simulator

Simulates penalty shootouts using a Monte Carlo approach with
zone-based kicker accuracy and goalkeeper dive probabilities.

The simulator models:
- 9-zone goal grid (3 rows × 3 columns)
- Per-zone scoring probabilities
- Goalkeeper dive direction selection
- Full 5-round shootout with sudden-death extension
- Batch simulation (10 000 runs) for team success rates

No ML model is trained here — the simulator uses empirically
calibrated probability tables derived from real penalty data.
"""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# ── Zone definitions ─────────────────────────────────────────────
# Goal is divided into a 3×3 grid:
#
#   TL  TC  TR      (top row)
#   ML  MC  MR      (middle row)
#   BL  BC  BR      (bottom row)
#
# Zone indices (row, col) from kicker's perspective:
ZONES = {
    "TL": (0, 0), "TC": (0, 1), "TR": (0, 2),
    "ML": (1, 0), "MC": (1, 1), "MR": (1, 2),
    "BL": (2, 0), "BC": (2, 1), "BR": (2, 2),
}

# Base scoring probability per zone (kicker hits the target AND scores)
# Top corners are hardest to save but hardest to hit on target.
# Centre is easy to hit but the keeper often stays.
ZONE_SCORE_PROB = {
    "TL": 0.82, "TC": 0.70, "TR": 0.83,
    "ML": 0.78, "MC": 0.55, "MR": 0.79,
    "BL": 0.75, "BC": 0.62, "BR": 0.76,
}

# Probability the kicker *misses the frame entirely* per zone
ZONE_MISS_PROB = {
    "TL": 0.08, "TC": 0.12, "TR": 0.09,
    "ML": 0.03, "MC": 0.02, "MR": 0.03,
    "BL": 0.04, "BC": 0.05, "BR": 0.04,
}

# Keeper save probability boost when diving to the correct side
KEEPER_SAVE_BOOST = {
    "same_side": 0.30,
    "centre": 0.15,
    "wrong_side": 0.00,
}

# Probability distribution for keeper dive direction
# Keepers tend to dive L/R more than staying centre
KEEPER_DIVE_PROBS = {
    "L": 0.40,
    "C": 0.20,
    "R": 0.40,
}


# ── data structures ──────────────────────────────────────────────
@dataclass
class PenaltyResult:
    """Result of a single penalty kick."""
    kicker_zone: str
    keeper_dive: str
    scored: bool
    miss_frame: bool


@dataclass
class ShootoutResult:
    """Result of a full shootout."""
    team_a_score: int
    team_b_score: int
    winner: str  # "A" or "B"
    rounds: int
    penalties: list[PenaltyResult]


# ── core logic ───────────────────────────────────────────────────
def _get_keeper_column(dive: str) -> int:
    """Map keeper dive direction to column index."""
    return {"L": 0, "C": 1, "R": 2}[dive]


def simulate_penalty(
    kicker_zone: str,
    keeper_dive: str,
    rng: np.random.Generator,
) -> PenaltyResult:
    """Simulate a single penalty kick.

    Parameters
    ----------
    kicker_zone : str
        Target zone (e.g. "TL", "BC", "MR").
    keeper_dive : str
        Keeper dive direction: "L", "C", or "R".
    rng : np.random.Generator
        Random number generator.

    Returns
    -------
    PenaltyResult
    """
    zone = kicker_zone.upper()
    dive = keeper_dive.upper()

    # Check if kicker misses the frame entirely
    miss_prob = ZONE_MISS_PROB.get(zone, 0.05)
    if rng.random() < miss_prob:
        return PenaltyResult(
            kicker_zone=zone,
            keeper_dive=dive,
            scored=False,
            miss_frame=True,
        )

    # Shot is on target — does the keeper save it?
    base_score_prob = ZONE_SCORE_PROB.get(zone, 0.70)

    # Determine if keeper dived to the correct side
    zone_row, zone_col = ZONES[zone]
    keeper_col = _get_keeper_column(dive)

    if zone_col == keeper_col:
        save_boost = KEEPER_SAVE_BOOST["same_side"]
    elif dive == "C":
        save_boost = KEEPER_SAVE_BOOST["centre"]
    else:
        save_boost = KEEPER_SAVE_BOOST["wrong_side"]

    final_score_prob = max(0.05, base_score_prob - save_boost)
    scored = rng.random() < final_score_prob

    return PenaltyResult(
        kicker_zone=zone,
        keeper_dive=dive,
        scored=scored,
        miss_frame=False,
    )


def simulate_shootout(
    rng: np.random.Generator | None = None,
) -> ShootoutResult:
    """Simulate a full penalty shootout (5 rounds + sudden death).

    Both teams' kickers select zones randomly weighted by real-world
    tendencies.  Keepers dive randomly.

    Returns
    -------
    ShootoutResult
    """
    if rng is None:
        rng = np.random.default_rng()

    zone_names = list(ZONES.keys())
    # Kicker zone selection weights (favour low corners and centre)
    kicker_weights = np.array([
        0.08, 0.05, 0.08,  # top row (risky)
        0.12, 0.10, 0.12,  # middle row
        0.18, 0.09, 0.18,  # bottom row (most common)
    ])
    kicker_weights = kicker_weights / kicker_weights.sum()

    dive_options = list(KEEPER_DIVE_PROBS.keys())
    dive_weights = np.array(list(KEEPER_DIVE_PROBS.values()))

    penalties: list[PenaltyResult] = []
    score_a = 0
    score_b = 0
    rounds = 0

    # Regular 5 rounds
    for round_num in range(5):
        rounds = round_num + 1

        # Team A kicks
        zone = rng.choice(zone_names, p=kicker_weights)
        dive = rng.choice(dive_options, p=dive_weights)
        result = simulate_penalty(zone, dive, rng)
        penalties.append(result)
        if result.scored:
            score_a += 1

        # Team B kicks
        zone = rng.choice(zone_names, p=kicker_weights)
        dive = rng.choice(dive_options, p=dive_weights)
        result = simulate_penalty(zone, dive, rng)
        penalties.append(result)
        if result.scored:
            score_b += 1

        # Check if shootout is already decided
        remaining = 5 - rounds
        if score_a > score_b + remaining:
            break
        if score_b > score_a + remaining:
            break

    # Sudden death (up to 10 extra rounds)
    if score_a == score_b:
        for _ in range(10):
            rounds += 1

            zone = rng.choice(zone_names, p=kicker_weights)
            dive = rng.choice(dive_options, p=dive_weights)
            result_a = simulate_penalty(zone, dive, rng)
            penalties.append(result_a)
            if result_a.scored:
                score_a += 1

            zone = rng.choice(zone_names, p=kicker_weights)
            dive = rng.choice(dive_options, p=dive_weights)
            result_b = simulate_penalty(zone, dive, rng)
            penalties.append(result_b)
            if result_b.scored:
                score_b += 1

            if score_a != score_b:
                break

    winner = "A" if score_a >= score_b else "B"

    return ShootoutResult(
        team_a_score=score_a,
        team_b_score=score_b,
        winner=winner,
        rounds=rounds,
        penalties=penalties,
    )


def monte_carlo_shootout(
    n_simulations: int = 10_000,
    seed: int | None = None,
) -> dict:
    """Run N shootout simulations and return aggregate statistics.

    Parameters
    ----------
    n_simulations : int
        Number of shootout simulations to run.
    seed : int or None
        Random seed for reproducibility.

    Returns
    -------
    dict
        Contains ``team_a_win_rate``, ``team_b_win_rate``,
        ``avg_total_goals``, ``avg_rounds``,
        ``zone_score_rates`` (empirical per-zone conversion rates).
    """
    rng = np.random.default_rng(seed)

    a_wins = 0
    total_goals = 0
    total_rounds = 0
    zone_attempts: dict[str, int] = {z: 0 for z in ZONES}
    zone_goals: dict[str, int] = {z: 0 for z in ZONES}

    for _ in range(n_simulations):
        result = simulate_shootout(rng)
        if result.winner == "A":
            a_wins += 1
        total_goals += result.team_a_score + result.team_b_score
        total_rounds += result.rounds

        for pen in result.penalties:
            zone_attempts[pen.kicker_zone] += 1
            if pen.scored:
                zone_goals[pen.kicker_zone] += 1

    zone_rates = {}
    for z in ZONES:
        if zone_attempts[z] > 0:
            zone_rates[z] = round(zone_goals[z] / zone_attempts[z], 3)
        else:
            zone_rates[z] = 0.0

    return {
        "simulations": n_simulations,
        "team_a_win_rate": round(a_wins / n_simulations, 4),
        "team_b_win_rate": round(1 - a_wins / n_simulations, 4),
        "avg_total_goals": round(total_goals / n_simulations, 2),
        "avg_rounds": round(total_rounds / n_simulations, 2),
        "zone_score_rates": zone_rates,
    }


def simulate_single_kick(
    kicker_zone: str,
    keeper_dive: str,
    seed: int | None = None,
) -> dict:
    """Simulate a single penalty for the interactive UI.

    Returns
    -------
    dict
        ``{"scored": bool, "miss_frame": bool, "zone": str, "dive": str}``
    """
    rng = np.random.default_rng(seed)
    result = simulate_penalty(kicker_zone, keeper_dive, rng)
    return {
        "scored": result.scored,
        "miss_frame": result.miss_frame,
        "zone": result.kicker_zone,
        "dive": result.keeper_dive,
    }


# ── quick self-test ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("== Testing Penalty Shootout Simulator ==\n")

    # Single shootout
    result = simulate_shootout(rng=np.random.default_rng(42))
    print(f"Shootout: Team A {result.team_a_score} - {result.team_b_score} Team B")
    print(f"Winner: Team {result.winner}  ({result.rounds} rounds)\n")

    # Monte Carlo
    stats = monte_carlo_shootout(n_simulations=10_000, seed=42)
    print("Monte Carlo (10 000 simulations):")
    print(f"  Team A win rate: {stats['team_a_win_rate']:.1%}")
    print(f"  Team B win rate: {stats['team_b_win_rate']:.1%}")
    print(f"  Avg total goals: {stats['avg_total_goals']}")
    print(f"  Avg rounds:      {stats['avg_rounds']}")
    print(f"\n  Zone conversion rates:")
    for zone, rate in stats["zone_score_rates"].items():
        print(f"    {zone}: {rate:.1%}")

    # Single kick test
    kick = simulate_single_kick("BL", "R", seed=42)
    print(f"\nSingle kick (BL -> keeper R): {'GOAL!' if kick['scored'] else 'Saved/Missed'}")

    print("\nDone")
