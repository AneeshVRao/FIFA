"""
model_shootout.py — Machine Learning Penalty Shootout Simulator

Implements:
1. A calibrated kicker-GK Logistic Regression classifier predicting target-zone
   scoring rates based on shooter skill, keeper save skill, target location,
   and goalkeeper dive alignment.
2. A greedy kick-order optimizer that ranks roster players and assigns them to
   slots 1-5 to maximize win probabilities.
3. 10,000-run Monte Carlo simulation supporting squad-specific inputs.
"""

import logging
import math
from pathlib import Path
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = DATA_DIR / "model_shootout.pkl"

# ── Zone definitions ─────────────────────────────────────────────
# Goal is divided into a 3×3 grid:
#   TL  TC  TR      (top row)
#   ML  MC  MR      (middle row)
#   BL  BC  BR      (bottom row)
ZONES = {
    "TL": (0, 0), "TC": (0, 1), "TR": (0, 2),
    "ML": (1, 0), "MC": (1, 1), "MR": (1, 2),
    "BL": (2, 0), "BC": (2, 1), "BR": (2, 2),
}

KEEPER_DIVE_PROBS = {
    "L": 0.40,
    "C": 0.20,
    "R": 0.40,
}


# ── player skill catalogs ─────────────────────────────────────────
STAR_KICKERS = {
    # England
    "Harry Kane": 0.92,
    "Jude Bellingham": 0.85,
    "Bukayo Saka": 0.82,
    "Phil Foden": 0.80,
    "Declan Rice": 0.76,
    "John Stones": 0.68,
    "Kyle Walker": 0.62,
    # Argentina
    "Lionel Messi": 0.91,
    "Lautaro Martinez": 0.84,
    "Angel Di Maria": 0.86,
    "Alexis Mac Allister": 0.83,
    "Enzo Fernandez": 0.81,
    "Rodrigo De Paul": 0.72,
    "Cristian Romero": 0.65,
    # France
    "Kylian Mbappe": 0.88,
    "Antoine Griezmann": 0.87,
    "Ousmane Dembele": 0.78,
    "Aurelien Tchouameni": 0.75,
    "Eduardo Camavinga": 0.74,
    "William Saliba": 0.66,
    "Theo Hernandez": 0.70,
    # Brazil
    "Vinicius Junior": 0.82,
    "Rodrygo Goes": 0.84,
    "Raphinha": 0.80,
    "Bruno Guimaraes": 0.76,
    "Lucas Paqueta": 0.82,
    "Marquinhos Aoas": 0.70,
    "Eder Militao": 0.65,
    # Portugal
    "Cristiano Ronaldo": 0.93,
    "Rafael Leao": 0.78,
    "Bruno Fernandes": 0.91,
    "Bernardo Silva": 0.84,
    "Vitinha": 0.78,
    "Ruben Dias": 0.68,
    "Joao Cancelo": 0.72,
    # Spain
    "Alvaro Morata": 0.78,
    "Lamine Yamal": 0.81,
    "Nico Williams": 0.79,
    "Pedri Gonzalez": 0.78,
    "Rodri Hernandez": 0.82,
    "Dani Carvajal": 0.70,
    "Robin Le Normand": 0.62,
    # Germany
    "Kai Havertz": 0.84,
    "Jamal Musiala": 0.82,
    "Florian Wirtz": 0.83,
    "Ilkay Gundogan": 0.88,
    "Joshua Kimmich": 0.80,
    "Antonio Rudiger": 0.68,
    "Jonathan Tah": 0.64,
    # USA
    "Christian Pulisic": 0.85,
    "Folarin Balogun": 0.78,
    "Timothy Weah": 0.74,
    "Weston McKennie": 0.72,
    "Tyler Adams": 0.68,
    "Chris Richards": 0.62,
    "Antonee Robinson": 0.60,
    # Mexico
    "Santiago Gimenez": 0.80,
    "Hirving Lozano": 0.76,
    "Edson Alvarez": 0.74,
    "Luis Chavez": 0.78,
    "Orbelin Pineda": 0.72,
    "Cesar Montes": 0.65,
    "Johan Vasquez": 0.62,
    # Canada
    "Jonathan David": 0.84,
    "Cyle Larin": 0.78,
    "Alphonso Davies": 0.74,
    "Stephen Eustaquio": 0.76,
    "Ismael Kone": 0.70,
    "Alistair Johnston": 0.60,
    "Moise Bombito": 0.58,
}

STAR_KEEPERS = {
    "Emiliano Martinez": 0.38,
    "Diogo Costa": 0.35,
    "Mike Maignan": 0.34,
    "Jordan Pickford": 0.32,
    "Unai Simon": 0.31,
    "Alisson Becker": 0.30,
    "Marc-Andre ter Stegen": 0.29,
    "Maxime Crepeau": 0.28,
    "Matt Turner": 0.28,
    "Luis Malagon": 0.27,
}


def get_kicker_skill(player_name: str, position: str) -> float:
    """Return penalty taker conversion skill index (0.40 - 0.95)."""
    if player_name in STAR_KICKERS:
        return STAR_KICKERS[player_name]
    
    # Position base defaults
    pos = str(position).upper()
    if "FW" in pos or "ST" in pos:
        base = 0.78
    elif "MF" in pos or "AM" in pos or "DM" in pos:
        base = 0.74
    elif "DF" in pos or "CB" in pos or "LB" in pos or "RB" in pos:
        base = 0.64
    else:  # Goalkeeper
        base = 0.45
        
    # Stable hash-based player offset (-0.04 to +0.04) for diversity
    h = hash(player_name) % 100
    offset = (h - 50) / 1250.0
    return min(max(base + offset, 0.40), 0.95)


def get_gk_skill(gk_name: str) -> float:
    """Return goalkeeper penalty save skill index (0.20 - 0.40)."""
    if gk_name in STAR_KEEPERS:
        return STAR_KEEPERS[gk_name]
    
    # Stable hash-based generic offset
    h = hash(gk_name) % 100
    offset = (h - 50) / 2500.0
    return min(max(0.24 + offset, 0.20), 0.40)


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
    return {"L": 0, "C": 1, "R": 2}[dive.upper()]


# ── ML training ──────────────────────────────────────────────────
def train_model() -> Pipeline:
    """Generate synthetic penalty training dataset and train Logistic Regression."""
    logger.info("Generating penalty shootout synthetic training log data …")
    rng = np.random.default_rng(42)
    n_samples = 15000
    
    kicker_skills = rng.uniform(0.40, 0.95, size=n_samples)
    gk_skills = rng.uniform(0.20, 0.40, size=n_samples)
    
    zone_names = list(ZONES.keys())
    zones_chosen = rng.choice(zone_names, size=n_samples)
    gk_dives = rng.choice(["L", "C", "R"], size=n_samples, p=[0.4, 0.2, 0.4])
    
    is_corner = np.array([1 if z in ["TL", "TR"] else 0 for z in zones_chosen])
    is_high = np.array([1 if z in ["TL", "TC", "TR"] else 0 for z in zones_chosen])
    
    gk_dive_correct = []
    for z, d in zip(zones_chosen, gk_dives):
        z_col = ZONES[z][1]
        gk_col = _get_keeper_column(d)
        gk_dive_correct.append(1 if z_col == gk_col else 0)
    gk_dive_correct = np.array(gk_dive_correct)
    
    scored_labels = []
    for k_skill, g_skill, corner, high, dive_corr in zip(
        kicker_skills, gk_skills, is_corner, is_high, gk_dive_correct
    ):
        base_prob = 0.82
        skill_factor = 0.25 * (k_skill - 0.70)
        
        gk_factor = 0.0
        if dive_corr == 1:
            gk_factor = -1.2 * g_skill
            
        zone_factor = 0.0
        if corner == 1 and dive_corr == 0:
            zone_factor = 0.05
        elif high == 1 and dive_corr == 1:
            zone_factor = 0.03
            
        prob = base_prob + skill_factor + gk_factor + zone_factor
        prob = min(max(prob, 0.05), 0.98)
        scored_labels.append(1 if rng.random() < prob else 0)
        
    df = pd.DataFrame({
        "kicker_skill": kicker_skills,
        "gk_skill": gk_skills,
        "is_corner": is_corner,
        "is_high": is_high,
        "gk_dive_correct": gk_dive_correct,
        "scored": scored_labels
    })
    
    X = df[["kicker_skill", "gk_skill", "is_corner", "is_high", "gk_dive_correct"]].values
    y = df["scored"].values
    
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(random_state=42))
    ])
    pipeline.fit(X, y)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    logger.info("Persisted penalty model pipeline to %s", MODEL_PATH)
    return pipeline


def load_model() -> Pipeline:
    """Load the trained penalty model, training if absent."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return train_model()


# ── greedy kick order optimizer ──────────────────────────────────
def optimize_kick_order(squad: list[dict]) -> list[dict]:
    """Sort and order players to maximize overall shootout win probability.

    Assigns:
    - Slot 1: Second best taker (starts strong, handles basic pressure).
    - Slot 5: Best taker (anchors the deciding kick).
    - Slot 4: Third best taker (handles critical setup pressure).
    - Slot 3: Fourth best taker.
    - Slot 2: Fifth best taker.
    - Slots 6+: Sorted descending by skill for sudden death.
    """
    squad_with_skills = []
    for p in squad:
        p_copy = dict(p)
        p_copy["skill"] = get_kicker_skill(p.get("name", ""), p.get("position", ""))
        squad_with_skills.append(p_copy)
        
    sorted_players = sorted(squad_with_skills, key=lambda x: x["skill"], reverse=True)
    
    if len(sorted_players) < 5:
        return sorted_players
        
    best_5 = sorted_players[:5]
    remaining = sorted_players[5:]
    
    # 0 = Best, 1 = 2nd Best, 2 = 3rd Best, 3 = 4th Best, 4 = 5th Best
    ordered_5 = [
        best_5[1],  # Slot 1
        best_5[4],  # Slot 2
        best_5[3],  # Slot 3
        best_5[2],  # Slot 4
        best_5[0],  # Slot 5
    ]
    return ordered_5 + remaining


# ── simulation logic ─────────────────────────────────────────────
def simulate_penalty(
    kicker_zone: str,
    keeper_dive: str,
    kicker_skill: float = 0.75,
    gk_skill: float = 0.25,
    pressure: float = 0.0,
    rng: np.random.Generator | None = None,
) -> PenaltyResult:
    """Simulate a single penalty kick using the trained ML model.

    First calculates physical target miss probability, then runs the on-target
    prediction using the Logistic Regression model.
    """
    if rng is None:
        rng = np.random.default_rng()

    zone = kicker_zone.upper()
    dive = keeper_dive.upper()

    # 1. Determine if kicker misses the frame entirely
    base_miss_prob = 0.03
    if zone in ["TL", "TR"]:
        base_miss_prob += 0.06
    elif zone in ["TC"]:
        base_miss_prob += 0.09

    # Skill-based correction
    skill_impact = 0.15 * (0.75 - kicker_skill)
    miss_prob = max(0.01, min(0.35, base_miss_prob + skill_impact))

    if rng.random() < miss_prob:
        return PenaltyResult(
            kicker_zone=zone,
            keeper_dive=dive,
            scored=False,
            miss_frame=True,
        )

    # 2. Shot on target — execute ML classifier prediction
    pipeline = load_model()

    is_corner = 1 if zone in ["TL", "TR"] else 0
    is_high = 1 if zone in ["TL", "TC", "TR"] else 0
    
    z_col = ZONES[zone][1]
    gk_col = _get_keeper_column(dive)
    gk_dive_correct = 1 if z_col == gk_col else 0

    features = np.array([[
        kicker_skill,
        gk_skill,
        is_corner,
        is_high,
        gk_dive_correct
    ]])

    prob = float(pipeline.predict_proba(features)[:, 1][0])
    
    # Apply pressure decay (subtract up to 0.05 probability)
    prob = max(0.02, prob - 0.05 * pressure)

    scored = rng.random() < prob
    return PenaltyResult(
        kicker_zone=zone,
        keeper_dive=dive,
        scored=scored,
        miss_frame=False,
    )


def simulate_shootout(
    rng: np.random.Generator | None = None,
    team_a_name: str = "Team A",
    team_b_name: str = "Team B",
) -> ShootoutResult:
    """Simulate a full penalty shootout using team rosters and ML solver."""
    if rng is None:
        rng = np.random.default_rng()

    from backend.worldcup_api import get_squad
    squad_a = get_squad(team_a_name)
    squad_b = get_squad(team_b_name)
    
    gk_a_name = next((p["name"] for p in squad_a if p["position"] == "GK"), "Goalkeeper A")
    gk_b_name = next((p["name"] for p in squad_b if p["position"] == "GK"), "Goalkeeper B")
    
    gk_a_skill = get_gk_skill(gk_a_name)
    gk_b_skill = get_gk_skill(gk_b_name)
    
    order_a = optimize_kick_order(squad_a)
    order_b = optimize_kick_order(squad_b)

    zone_names = list(ZONES.keys())
    kicker_weights = np.array([
        0.08, 0.05, 0.08,
        0.12, 0.10, 0.12,
        0.18, 0.09, 0.18,
    ])
    kicker_weights = kicker_weights / kicker_weights.sum()

    dive_options = ["L", "C", "R"]
    dive_weights = np.array([0.40, 0.20, 0.40])

    penalties: list[PenaltyResult] = []
    score_a = 0
    score_b = 0
    rounds = 0

    # 5 Initial rounds
    for round_num in range(5):
        rounds = round_num + 1

        # Team A kicks (GK B defends)
        p_idx = round_num % len(order_a)
        player_a = order_a[p_idx]
        k_skill_a = player_a["skill"]
        
        pressure_a = float(round_num) / 5.0
        if score_a < score_b:
            pressure_a += 0.25
            
        zone = rng.choice(zone_names, p=kicker_weights)
        dive = rng.choice(dive_options, p=dive_weights)
        result = simulate_penalty(zone, dive, kicker_skill=k_skill_a, gk_skill=gk_b_skill, pressure=pressure_a, rng=rng)
        penalties.append(result)
        if result.scored:
            score_a += 1

        # Check early exit
        remaining_b = 5 - round_num
        remaining_a = 5 - rounds
        if score_a > score_b + remaining_b:
            break
        if score_b > score_a + remaining_a:
            break

        # Team B kicks (GK A defends)
        p_idx = round_num % len(order_b)
        player_b = order_b[p_idx]
        k_skill_b = player_b["skill"]
        
        pressure_b = float(round_num) / 5.0
        if score_b < score_a:
            pressure_b += 0.25

        zone = rng.choice(zone_names, p=kicker_weights)
        dive = rng.choice(dive_options, p=dive_weights)
        result = simulate_penalty(zone, dive, kicker_skill=k_skill_b, gk_skill=gk_a_skill, pressure=pressure_b, rng=rng)
        penalties.append(result)
        if result.scored:
            score_b += 1

        if score_a > score_b + remaining_a:
            break
        if score_b > score_a + remaining_a:
            break

    # Sudden Death
    if score_a == score_b:
        for extra_r in range(15):
            rounds += 1
            curr_idx = 5 + extra_r

            p_idx = curr_idx % len(order_a)
            player_a = order_a[p_idx]
            k_skill_a = player_a["skill"]
            
            zone = rng.choice(zone_names, p=kicker_weights)
            dive = rng.choice(dive_options, p=dive_weights)
            result_a = simulate_penalty(zone, dive, kicker_skill=k_skill_a, gk_skill=gk_b_skill, pressure=1.0, rng=rng)
            penalties.append(result_a)
            if result_a.scored:
                score_a += 1

            p_idx = curr_idx % len(order_b)
            player_b = order_b[p_idx]
            k_skill_b = player_b["skill"]
            
            zone = rng.choice(zone_names, p=kicker_weights)
            dive = rng.choice(dive_options, p=dive_weights)
            result_b = simulate_penalty(zone, dive, kicker_skill=k_skill_b, gk_skill=gk_a_skill, pressure=1.0, rng=rng)
            penalties.append(result_b)
            if result_b.scored:
                score_b += 1

            if score_a != score_b:
                break

    winner = "A" if score_a > score_b else "B"

    return ShootoutResult(
        team_a_score=score_a,
        team_b_score=score_b,
        winner=winner,
        rounds=rounds,
        penalties=penalties,
    )


def monte_carlo_shootout(
    n_simulations: int = 10000,
    seed: int | None = None,
    team_a_name: str = "Team A",
    team_b_name: str = "Team B",
) -> dict:
    """Run Monte Carlo shootout simulations for team success rates."""
    rng = np.random.default_rng(seed)

    a_wins = 0
    total_goals = 0
    total_rounds = 0
    zone_attempts = {z: 0 for z in ZONES}
    zone_goals = {z: 0 for z in ZONES}

    # Pre-load squads to make simulation faster
    for _ in range(n_simulations):
        result = simulate_shootout(rng, team_a_name, team_b_name)
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
    """Single kick simulation for UI interaction."""
    rng = np.random.default_rng(seed)
    result = simulate_penalty(kicker_zone, keeper_dive, kicker_skill=0.75, gk_skill=0.25, rng=rng)
    return {
        "scored": result.scored,
        "miss_frame": result.miss_frame,
        "zone": result.kicker_zone,
        "dive": result.keeper_dive,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("== Training Penalty ML Classifier ==")
    train_model()
    
    # Test MC
    stats = monte_carlo_shootout(n_simulations=1000, seed=42, team_a_name="Argentina", team_b_name="France")
    print(f"\nArgentina vs France MC Win Rates:")
    print(f"  Argentina: {stats['team_a_win_rate']:.1%}")
    print(f"  France:    {stats['team_b_win_rate']:.1%}")
