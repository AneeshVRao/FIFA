"""
model_match.py — Match Outcome Predictor Training Pipeline

Trains a Logistic Regression classifier on historical international
football results using Elo-derived features.  The model predicts
three classes: home_win, draw, away_win.

Features engineered per match
-----------------------------
- elo_diff            : Home Elo − Away Elo
- elo_sum             : (Home + Away) / 2  (match quality proxy)
- home_form           : Rolling 5-game point average for home team
- away_form           : Rolling 5-game point average for away team
- tournament_weight   : Higher weight for competitive fixtures

The trained model and scaler are persisted to ``data/model_match.pkl``
via joblib so that the FastAPI server can load them at startup.

Follows the scikit-learn skill's Pipeline best-practice to prevent
data leakage during cross-validation.
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
from sklearn.metrics import classification_report

from backend.data_loader import load_results
from backend.elo import (
    DEFAULT_ELO,
    HOME_ADVANTAGE,
    K_FACTOR,
    _expected_score,
    _goal_diff_multiplier,
    _actual_score,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = DATA_DIR / "model_match.pkl"


# ── feature engineering ──────────────────────────────────────────
TOURNAMENT_WEIGHTS = {
    "FIFA World Cup": 1.0,
    "FIFA World Cup qualification": 0.8,
    "UEFA Euro": 0.9,
    "UEFA Euro qualification": 0.7,
    "Copa América": 0.9,
    "African Cup of Nations": 0.85,
    "AFC Asian Cup": 0.8,
    "CONCACAF Gold Cup": 0.75,
    "UEFA Nations League": 0.7,
    "Confederations Cup": 0.7,
    "Friendly": 0.4,
}


def _tournament_weight(tournament: str) -> float:
    """Return importance weight for a given tournament type."""
    for key, weight in TOURNAMENT_WEIGHTS.items():
        if key.lower() in tournament.lower():
            return weight
    return 0.5


def _rolling_form(df: pd.DataFrame, window: int = 5) -> dict[str, list[float]]:
    """Compute rolling form (avg points in last N games) for every team.

    Returns a dict mapping team → list of form values aligned to
    the team's chronological match indices.
    """
    team_history: dict[str, list[tuple[int, float]]] = {}

    for idx, row in df.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        hs, aws = int(row["home_score"]), int(row["away_score"])

        if hs > aws:
            home_pts, away_pts = 3.0, 0.0
        elif hs < aws:
            home_pts, away_pts = 0.0, 3.0
        else:
            home_pts, away_pts = 1.0, 1.0

        team_history.setdefault(home, []).append((idx, home_pts))
        team_history.setdefault(away, []).append((idx, away_pts))

    # Build rolling averages
    form_by_idx: dict[str, dict[int, float]] = {}
    for team, history in team_history.items():
        form_by_idx[team] = {}
        pts_list = [p for _, p in history]
        for i, (original_idx, _) in enumerate(history):
            start = max(0, i - window)
            recent = pts_list[start:i] if i > 0 else [1.0]
            form_by_idx[team][original_idx] = (
                sum(recent) / len(recent) if recent else 1.0
            )

    return form_by_idx


def build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Transform the historical results into feature matrix X and label y.

    Labels:  0 = away_win, 1 = draw, 2 = home_win

    Returns
    -------
    X : np.ndarray, shape (n_matches, 5)
    y : np.ndarray, shape (n_matches,)
    """
    df = df.sort_values("date").reset_index(drop=True)

    # Build running Elo for each match
    ratings: dict[str, float] = {}
    elo_diffs = []
    elo_sums = []

    for _, row in df.iterrows():
        home = row["home_team"]
        away = row["away_team"]

        ratings.setdefault(home, DEFAULT_ELO)
        ratings.setdefault(away, DEFAULT_ELO)

        is_neutral = bool(row.get("neutral", False))
        home_elo = ratings[home] + (0 if is_neutral else HOME_ADVANTAGE)
        away_elo = ratings[away]

        elo_diffs.append(home_elo - away_elo)
        elo_sums.append((ratings[home] + ratings[away]) / 2.0)

        # Update ratings after recording the pre-match values
        hs, aws = int(row["home_score"]), int(row["away_score"])
        expected_home = _expected_score(home_elo, away_elo)
        actual_home, actual_away = _actual_score(hs, aws)
        gd_mult = _goal_diff_multiplier(hs - aws)

        ratings[home] += K_FACTOR * gd_mult * (actual_home - expected_home)
        ratings[away] += K_FACTOR * gd_mult * (actual_away - (1 - expected_home))

    # Rolling form
    form = _rolling_form(df, window=5)
    home_forms = []
    away_forms = []
    for idx, row in df.iterrows():
        hf = form.get(row["home_team"], {}).get(idx, 1.0)
        af = form.get(row["away_team"], {}).get(idx, 1.0)
        home_forms.append(hf)
        away_forms.append(af)

    # Tournament weight
    t_weights = [_tournament_weight(row.get("tournament", "Friendly")) for _, row in df.iterrows()]

    X = np.column_stack([
        elo_diffs,
        elo_sums,
        home_forms,
        away_forms,
        t_weights,
    ])

    # Labels
    labels = []
    for _, row in df.iterrows():
        hs, aws = int(row["home_score"]), int(row["away_score"])
        if hs > aws:
            labels.append(2)   # home win
        elif hs < aws:
            labels.append(0)   # away win
        else:
            labels.append(1)   # draw

    y = np.array(labels)
    return X, y


# ── training ─────────────────────────────────────────────────────
def train_model() -> Pipeline:
    """Train the match outcome classifier and save to disk.

    Uses scikit-learn Pipeline (StandardScaler → LogisticRegression)
    with 5-fold stratified cross-validation for evaluation.

    Returns
    -------
    Pipeline
        The fitted sklearn Pipeline.
    """
    logger.info("Loading historical data …")
    df = load_results()

    # Use only the last 10 years for more relevant training
    cutoff = df["date"].max() - pd.DateOffset(years=10)
    df = df[df["date"] >= cutoff].copy()
    logger.info("Training on %d matches (last 10 years)", len(df))

    X, y = build_features(df)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(
            max_iter=1000,
            solver="lbfgs",
            random_state=42,
            class_weight="balanced",
        )),
    ])

    # Cross-validate
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
    logger.info(
        "Cross-val accuracy: %.3f ± %.3f",
        scores.mean(),
        scores.std(),
    )

    # Fit on full training set
    pipeline.fit(X, y)

    # Report
    y_pred = pipeline.predict(X)
    report = classification_report(
        y, y_pred, target_names=["away_win", "draw", "home_win"]
    )
    logger.info("Classification report on training data:\n%s", report)

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    logger.info("Model saved to %s", MODEL_PATH)

    return pipeline


def load_model() -> Pipeline:
    """Load the trained model from disk, training if absent."""
    if MODEL_PATH.exists():
        logger.info("Loading match model from %s", MODEL_PATH)
        return joblib.load(MODEL_PATH)
    logger.info("Model not found — training now …")
    return train_model()


# ── quick self-test ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("== Training Match Outcome Predictor ==")
    train_model()
    print("Done")
