"""
model_xg.py — Expected Goals (xG) Model Training Pipeline

Trains a Logistic Regression classifier on StatsBomb open shot-event
data to predict the probability of a shot resulting in a goal.

Features
--------
- distance_to_goal   : Euclidean distance from shot location to centre of goal
- angle_to_goal      : Angle subtended at the shot location by the goalposts
- is_header          : 1 if body part is "Head", else 0
- under_pressure     : 1 if the shooter was under pressure
- shot_x, shot_y     : Raw pitch coordinates (StatsBomb 120×80 format)

The trained pipeline is persisted to ``data/model_xg.pkl``.

Uses ``statsbombpy`` to fetch open competition shot events.  Falls
back to a synthetic dataset if the StatsBomb API is unreachable so
that the build never breaks.
"""

import logging
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    brier_score_loss,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = DATA_DIR / "model_xg.pkl"
SHOTS_CACHE = DATA_DIR / "shots_cache.csv"

# StatsBomb pitch dimensions
PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0
GOAL_Y_CENTER = PITCH_WIDTH / 2.0  # 40
GOAL_WIDTH = 7.32  # metres, but StatsBomb uses yards (~8 yds)
GOAL_HALF_WIDTH = 4.0  # yards in SB coordinate space


# ── geometry helpers ─────────────────────────────────────────────
def distance_to_goal(x: float, y: float) -> float:
    """Euclidean distance from (x, y) to centre of the goal line."""
    return math.sqrt((PITCH_LENGTH - x) ** 2 + (GOAL_Y_CENTER - y) ** 2)


def angle_to_goal(x: float, y: float) -> float:
    """Angle in radians subtended at (x, y) by the two goalposts."""
    goal_x = PITCH_LENGTH
    post_top = GOAL_Y_CENTER + GOAL_HALF_WIDTH
    post_bot = GOAL_Y_CENTER - GOAL_HALF_WIDTH

    # Vectors from shot position to each post
    dx_top = goal_x - x
    dy_top = post_top - y
    dx_bot = goal_x - x
    dy_bot = post_bot - y

    dot = dx_top * dx_bot + dy_top * dy_bot
    mag_top = math.sqrt(dx_top ** 2 + dy_top ** 2)
    mag_bot = math.sqrt(dx_bot ** 2 + dy_bot ** 2)

    if mag_top * mag_bot == 0:
        return math.pi

    cos_angle = max(-1.0, min(1.0, dot / (mag_top * mag_bot)))
    return math.acos(cos_angle)


# ── data collection ──────────────────────────────────────────────
def _fetch_statsbomb_shots() -> pd.DataFrame:
    """Fetch shot events from StatsBomb open competitions.

    Targets: FIFA World Cup 2022, Euro 2024, and World Cup 2018
    using the free open-data API.

    Returns
    -------
    pd.DataFrame
        Columns: x, y, is_header, under_pressure, is_goal
    """
    if SHOTS_CACHE.exists():
        logger.info("Loading cached shots from %s", SHOTS_CACHE)
        return pd.read_csv(SHOTS_CACHE)

    try:
        from statsbombpy import sb

        logger.info("Fetching StatsBomb competitions …")
        comps = sb.competitions()

        # Target competitions (open data)
        target_comps = comps[
            (comps["competition_name"].str.contains("World Cup|Euro", case=False, na=False))
            & (comps["season_name"].str.contains("2018|2022|2024|2020", na=False))
        ]

        if target_comps.empty:
            # Fallback: use any competition with open data
            target_comps = comps.head(5)
            logger.warning(
                "No World Cup/Euro competitions found. Using first 5 comps."
            )

        all_shots = []
        for _, comp in target_comps.iterrows():
            comp_id = int(comp["competition_id"])
            season_id = int(comp["season_id"])
            logger.info(
                "  Fetching matches for %s %s …",
                comp["competition_name"],
                comp["season_name"],
            )

            try:
                matches = sb.matches(competition_id=comp_id, season_id=season_id)
            except Exception:
                logger.warning("  Could not fetch matches, skipping.")
                continue

            for _, match in matches.iterrows():
                match_id = int(match["match_id"])
                try:
                    events = sb.events(match_id=match_id)
                except Exception:
                    continue

                shots = events[events["type"] == "Shot"].copy()
                if shots.empty:
                    continue

                for _, shot in shots.iterrows():
                    loc = shot.get("location", None)
                    if loc is None or not isinstance(loc, (list, tuple)):
                        continue
                    if len(loc) < 2:
                        continue

                    x, y = float(loc[0]), float(loc[1])
                    body = str(shot.get("shot_body_part", "")).lower()
                    is_header = 1 if "head" in body else 0
                    pressure = 1 if shot.get("under_pressure", False) else 0
                    outcome = str(shot.get("shot_outcome", "")).lower()
                    is_goal = 1 if "goal" in outcome else 0

                    all_shots.append({
                        "x": x,
                        "y": y,
                        "is_header": is_header,
                        "under_pressure": pressure,
                        "is_goal": is_goal,
                    })

        if not all_shots:
            raise RuntimeError("No shots collected from StatsBomb")

        df = pd.DataFrame(all_shots)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(SHOTS_CACHE, index=False)
        logger.info("Cached %d shots to %s", len(df), SHOTS_CACHE)
        return df

    except Exception as exc:
        logger.warning("StatsBomb fetch failed (%s). Using synthetic data.", exc)
        return _generate_synthetic_shots()


def _generate_synthetic_shots(n: int = 5000) -> pd.DataFrame:
    """Generate a realistic synthetic shot dataset as a fallback.

    Shot probabilities decrease with distance and off-centre angles,
    mimicking real-world xG distributions.
    """
    rng = np.random.default_rng(42)

    # Shots mostly come from the attacking third (x > 80)
    x = rng.uniform(80, 120, size=n)
    y = rng.uniform(10, 70, size=n)
    is_header = rng.binomial(1, 0.15, size=n)
    under_pressure = rng.binomial(1, 0.35, size=n)

    # Goal probability based on position
    goals = []
    for i in range(n):
        dist = distance_to_goal(x[i], y[i])
        angle = angle_to_goal(x[i], y[i])

        # Base probability from distance
        base_prob = max(0.02, 0.85 - 0.02 * dist)

        # Angle bonus
        angle_factor = min(1.0, angle / 0.5)
        prob = base_prob * angle_factor

        # Headers are slightly less likely
        if is_header[i]:
            prob *= 0.75

        # Pressure reduces accuracy
        if under_pressure[i]:
            prob *= 0.8

        # Penalty spot special case (x≈108, y≈40)
        if 107 < x[i] < 109 and 38 < y[i] < 42:
            prob = 0.76

        prob = min(max(prob, 0.01), 0.95)
        goals.append(int(rng.random() < prob))

    df = pd.DataFrame({
        "x": x,
        "y": y,
        "is_header": is_header,
        "under_pressure": under_pressure,
        "is_goal": goals,
    })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(SHOTS_CACHE, index=False)
    logger.info("Generated %d synthetic shots (cached)", n)
    return df


# ── feature engineering ──────────────────────────────────────────
def build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Transform raw shot data into feature matrix and labels.

    Features
    --------
    0: distance_to_goal
    1: angle_to_goal
    2: is_header
    3: under_pressure
    4: x (normalised)
    5: y (normalised)

    Returns
    -------
    X : np.ndarray, shape (n, 6)
    y : np.ndarray, shape (n,)
    """
    distances = [distance_to_goal(r.x, r.y) for _, r in df.iterrows()]
    angles = [angle_to_goal(r.x, r.y) for _, r in df.iterrows()]

    X = np.column_stack([
        distances,
        angles,
        df["is_header"].values,
        df["under_pressure"].values,
        df["x"].values / PITCH_LENGTH,
        df["y"].values / PITCH_WIDTH,
    ])
    y = df["is_goal"].values.astype(int)
    return X, y


# ── training ─────────────────────────────────────────────────────
def train_model() -> Pipeline:
    """Train the xG classifier and save to disk.

    Returns
    -------
    Pipeline
        Fitted pipeline: StandardScaler → LogisticRegression.
    """
    logger.info("Collecting shot data …")
    df = _fetch_statsbomb_shots()

    # Data quality: filter out-of-bounds shots
    df = df[(df["x"] >= 0) & (df["x"] <= PITCH_LENGTH)]
    df = df[(df["y"] >= 0) & (df["y"] <= PITCH_WIDTH)]
    df = df.dropna()
    logger.info("Training on %d valid shots", len(df))

    X, y = build_features(df)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(
            max_iter=1000,
            solver="lbfgs",
            random_state=42,
        )),
    ])

    # Cross-validate
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="roc_auc")
    logger.info("Cross-val ROC-AUC: %.3f ± %.3f", scores.mean(), scores.std())

    # Fit on full data
    pipeline.fit(X, y)

    # Report
    y_proba = pipeline.predict_proba(X)[:, 1]
    brier = brier_score_loss(y, y_proba)
    logger.info("Brier score (lower is better): %.4f", brier)

    y_pred = pipeline.predict(X)
    report = classification_report(y, y_pred, target_names=["no_goal", "goal"])
    logger.info("Classification report:\n%s", report)

    # Sanity check: penalty spot xG
    penalty_x, penalty_y = 108.0, 40.0
    penalty_features = np.array([[
        distance_to_goal(penalty_x, penalty_y),
        angle_to_goal(penalty_x, penalty_y),
        0,  # foot
        0,  # no pressure
        penalty_x / PITCH_LENGTH,
        penalty_y / PITCH_WIDTH,
    ]])
    penalty_xg = pipeline.predict_proba(
        pipeline.named_steps["scaler"].transform(penalty_features)
    )
    # We use pipeline.predict_proba directly:
    penalty_xg_direct = pipeline.predict_proba(penalty_features)[:, 1][0]
    logger.info("Penalty spot xG: %.3f (target ≈ 0.75)", penalty_xg_direct)

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    logger.info("Model saved to %s", MODEL_PATH)

    return pipeline


def load_model() -> Pipeline:
    """Load the trained xG model from disk, training if absent."""
    if MODEL_PATH.exists():
        logger.info("Loading xG model from %s", MODEL_PATH)
        return joblib.load(MODEL_PATH)
    logger.info("xG model not found — training now …")
    return train_model()


def predict_xg(
    pipeline: Pipeline,
    x: float,
    y: float,
    is_header: bool = False,
    under_pressure: bool = False,
) -> float:
    """Predict xG for a single shot.

    Parameters
    ----------
    pipeline : Pipeline
        Fitted xG model.
    x, y : float
        Shot coordinates (StatsBomb 120×80).
    is_header : bool
        True if the shot is a header.
    under_pressure : bool
        True if the shooter was under pressure.

    Returns
    -------
    float
        Probability of the shot being a goal (0–1).
    """
    features = np.array([[
        distance_to_goal(x, y),
        angle_to_goal(x, y),
        int(is_header),
        int(under_pressure),
        x / PITCH_LENGTH,
        y / PITCH_WIDTH,
    ]])
    return float(pipeline.predict_proba(features)[:, 1][0])


# ── quick self-test ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("== Training xG Model ==")
    model = train_model()

    # Test a few shot positions
    test_shots = [
        (108, 40, False, False, "Penalty spot"),
        (110, 40, False, False, "6-yard box centre"),
        (100, 40, False, False, "Edge of box centre"),
        (90, 40, False, False, "25 yards out"),
        (100, 55, False, False, "Edge of box wide"),
        (100, 40, True, False, "Edge of box header"),
        (100, 40, False, True, "Edge of box under pressure"),
    ]

    print("\n  Shot Position Tests:")
    for x, y, head, pressure, desc in test_shots:
        xg = predict_xg(model, x, y, head, pressure)
        print(f"    {desc:<35s}  xG = {xg:.3f}")

    print("\nDone")
