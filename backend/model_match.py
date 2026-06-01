"""
model_match.py — Match Outcome Predictor Training Pipeline

Trains an XGBoost classifier with Platt scaling calibration (CalibratedClassifierCV)
on historical international results using 9 Elo and squad features.
Also fits a Dixon-Coles Poisson model to predict joint scorelines.

Features engineered per match
-----------------------------
- elo_diff            : Home Elo − Away Elo
- elo_sum             : (Home + Away) / 2  (match quality proxy)
- home_form           : Rolling 5-game point average for home team
- away_form           : Rolling 5-game point average for away team
- tournament_weight   : Higher weight for competitive fixtures
- squad_diff          : Home Squad Value - Away Squad Value
- rank_diff           : Away FIFA Rank - Home FIFA Rank
- squad_ratio         : Home Squad Value / (Away Squad Value + 1.0)
- form_diff           : Home Form - Away Form
"""

import logging
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy.optimize as opt
from scipy.stats import poisson
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
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
DIXON_COLES_PATH = DATA_DIR / "model_dixon_coles.pkl"


# ── Dixon-Coles Likelihood Helper ───────────────────────────────
def negative_log_likelihood(params, elo_diffs, squad_ratios, form_diffs, home_goals, away_goals):
    mu, a1, a2, a3, rho = params
    
    # Calculate lambda_H and lambda_A
    lambda_H = mu * np.exp(a1 * elo_diffs + a2 * squad_ratios + a3 * form_diffs)
    lambda_A = mu * np.exp(-a1 * elo_diffs - a2 * squad_ratios - a3 * form_diffs)
    
    lambda_H = np.clip(lambda_H, 0.05, 10.0)
    lambda_A = np.clip(lambda_A, 0.05, 10.0)
    
    # Compute tau (Dixon-Coles adjustment for low scores: 0-0, 1-0, 0-1, 1-1)
    tau = np.ones_like(home_goals, dtype=float)
    
    idx_00 = (home_goals == 0) & (away_goals == 0)
    idx_10 = (home_goals == 1) & (away_goals == 0)
    idx_01 = (home_goals == 0) & (away_goals == 1)
    idx_11 = (home_goals == 1) & (away_goals == 1)
    
    tau[idx_00] = 1 - lambda_H[idx_00] * lambda_A[idx_00] * rho
    tau[idx_10] = 1 + lambda_A[idx_10] * rho
    tau[idx_01] = 1 + lambda_H[idx_01] * rho
    tau[idx_11] = 1 - rho
    
    tau = np.clip(tau, 1e-6, 5.0)
    
    log_tau = np.log(tau)
    log_l = log_tau - lambda_H - lambda_A + home_goals * np.log(lambda_H) + away_goals * np.log(lambda_A)
    
    return -np.sum(log_l)


# ── Dixon-Coles Poisson Model ───────────────────────────────────
class DixonColesPoisson:
    def __init__(self):
        self.mu = 1.35
        self.a1 = 0.002
        self.a2 = 0.1
        self.a3 = 0.1
        self.rho = 0.05

    def fit(self, elo_diffs, squad_ratios, form_diffs, home_goals, away_goals):
        init_params = [self.mu, self.a1, self.a2, self.a3, self.rho]
        bounds = [
            (0.5, 3.0),      # mu
            (0.0, 0.02),     # a1
            (-0.5, 0.5),     # a2
            (-0.5, 0.5),     # a3
            (-0.15, 0.15)    # rho
        ]
        
        res = opt.minimize(
            negative_log_likelihood,
            init_params,
            args=(elo_diffs, squad_ratios, form_diffs, home_goals, away_goals),
            bounds=bounds,
            method="L-BFGS-B"
        )
        
        if res.success:
            self.mu, self.a1, self.a2, self.a3, self.rho = res.x
            logger.info("Dixon-Coles Poisson fitted: mu=%.4f, a1=%.4f, a2=%.4f, a3=%.4f, rho=%.4f", 
                        self.mu, self.a1, self.a2, self.a3, self.rho)
        else:
            logger.warning("Dixon-Coles optimization failed: %s. Using default parameters.", res.message)

    def predict_lambdas(self, elo_diff, squad_ratio, form_diff):
        lambda_H = self.mu * np.exp(self.a1 * elo_diff + self.a2 * squad_ratio + self.a3 * form_diff)
        lambda_A = self.mu * np.exp(-self.a1 * elo_diff - self.a2 * squad_ratio - self.a3 * form_diff)
        return float(np.clip(lambda_H, 0.05, 10.0)), float(np.clip(lambda_A, 0.05, 10.0))

    def predict_probs(self, elo_diff, squad_ratio, form_diff, max_goals=10):
        lambda_H, lambda_A = self.predict_lambdas(elo_diff, squad_ratio, form_diff)
        
        p_grid = np.zeros((max_goals + 1, max_goals + 1))
        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                p_x = poisson.pmf(x, lambda_H)
                p_y = poisson.pmf(y, lambda_A)
                
                tau = 1.0
                if x == 0 and y == 0:
                    tau = 1 - lambda_H * lambda_A * self.rho
                elif x == 1 and y == 0:
                    tau = 1 + lambda_A * self.rho
                elif x == 0 and y == 1:
                    tau = 1 + lambda_H * self.rho
                elif x == 1 and y == 1:
                    tau = 1 - self.rho
                
                p_grid[x, y] = max(0.0, tau * p_x * p_y)
                
        grid_sum = np.sum(p_grid)
        if grid_sum > 0:
            p_grid /= grid_sum
            
        home_win = np.sum(np.tril(p_grid, -1))
        draw = np.sum(np.diag(p_grid))
        away_win = np.sum(np.triu(p_grid, 1))
        
        return {
            "home_win": round(float(home_win), 4),
            "draw": round(float(draw), 4),
            "away_win": round(float(away_win), 4)
        }

    def sample_score(self, elo_diff, squad_ratio, form_diff, rng=None):
        if rng is None:
            rng = np.random.default_rng()
        
        lambda_H, lambda_A = self.predict_lambdas(elo_diff, squad_ratio, form_diff)
        
        max_goals = 10
        p_grid = np.zeros((max_goals + 1, max_goals + 1))
        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                p_x = poisson.pmf(x, lambda_H)
                p_y = poisson.pmf(y, lambda_A)
                
                tau = 1.0
                if x == 0 and y == 0:
                    tau = 1 - lambda_H * lambda_A * self.rho
                elif x == 1 and y == 0:
                    tau = 1 + lambda_A * self.rho
                elif x == 0 and y == 1:
                    tau = 1 + lambda_H * self.rho
                elif x == 1 and y == 1:
                    tau = 1 - self.rho
                
                p_grid[x, y] = max(0.0, tau * p_x * p_y)
                
        grid_sum = np.sum(p_grid)
        if grid_sum > 0:
            p_grid /= grid_sum
            
        flat_grid = p_grid.flatten()
        idx = rng.choice(len(flat_grid), p=flat_grid)
        return int(x), int(y)


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
    for key, weight in TOURNAMENT_WEIGHTS.items():
        if key.lower() in tournament.lower():
            return weight
    return 0.5


def _rolling_form(df: pd.DataFrame, window: int = 5) -> dict[str, list[float]]:
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

    form_by_idx: dict[str, dict[int, float]] = {}
    for team, history in team_history.items():
        form_by_idx[team] = {}
        pts_list = [p for _, p in history]
        for i, (original_idx, _) in enumerate(history):
            start = max(0, i - window)
            recent = pts_list[start:i] if i > 0 else [1.0]
            form_by_idx[team][original_idx] = sum(recent) / len(recent) if recent else 1.0

    return form_by_idx


def build_features(df: pd.DataFrame):
    df = df.sort_values("date").reset_index(drop=True)

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

        hs, aws = int(row["home_score"]), int(row["away_score"])
        expected_home = _expected_score(home_elo, away_elo)
        actual_home, actual_away = _actual_score(hs, aws)
        gd_mult = _goal_diff_multiplier(hs - aws)

        ratings[home] += K_FACTOR * gd_mult * (actual_home - expected_home)
        ratings[away] += K_FACTOR * gd_mult * (actual_away - (1 - expected_home))

    form = _rolling_form(df, window=5)
    home_forms = []
    away_forms = []
    for idx, row in df.iterrows():
        hf = form.get(row["home_team"], {}).get(idx, 1.0)
        af = form.get(row["away_team"], {}).get(idx, 1.0)
        home_forms.append(hf)
        away_forms.append(af)

    t_weights = [_tournament_weight(row.get("tournament", "Friendly")) for _, row in df.iterrows()]

    from backend.team_metadata import TEAM_METADATA
    squad_diffs = []
    rank_diffs = []
    squad_ratios = []
    form_diffs = []
    home_goals = []
    away_goals = []
    
    for idx, row in df.iterrows():
        h = row["home_team"]
        a = row["away_team"]
        h_meta = TEAM_METADATA.get(h, {"squad_value": 50.0, "fifa_rank": 80})
        a_meta = TEAM_METADATA.get(a, {"squad_value": 50.0, "fifa_rank": 80})
        squad_diffs.append(h_meta["squad_value"] - a_meta["squad_value"])
        rank_diffs.append(a_meta["fifa_rank"] - h_meta["fifa_rank"])
        squad_ratios.append(h_meta["squad_value"] / (a_meta["squad_value"] + 1.0))
        form_diffs.append(home_forms[idx] - away_forms[idx])
        home_goals.append(int(row["home_score"]))
        away_goals.append(int(row["away_score"]))

    X = np.column_stack([
        elo_diffs,
        elo_sums,
        home_forms,
        away_forms,
        t_weights,
        squad_diffs,
        rank_diffs,
        squad_ratios,
        form_diffs,
    ])

    labels = []
    for h_g, a_g in zip(home_goals, away_goals):
        if h_g > a_g:
            labels.append(2)   # home win
        elif h_g < a_g:
            labels.append(0)   # away win
        else:
            labels.append(1)   # draw

    y = np.array(labels)
    
    return X, y, np.array(elo_diffs), np.array(squad_ratios), np.array(form_diffs), np.array(home_goals), np.array(away_goals)


# ── training ─────────────────────────────────────────────────────
def train_model() -> Pipeline:
    logger.info("Loading historical data …")
    df = load_results()

    cutoff = df["date"].max() - pd.DateOffset(years=10)
    df = df[df["date"] >= cutoff].copy()
    logger.info("Training on %d matches (last 10 years)", len(df))

    X, y, elo_diffs, squad_ratios, form_diffs, home_goals, away_goals = build_features(df)

    # 1. Fit Calibrated XGBoost (Platt Scaling)
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", CalibratedClassifierCV(
            estimator=XGBClassifier(
                n_estimators=120,
                learning_rate=0.04,
                max_depth=3,
                random_state=42,
                eval_metric="mlogloss"
            ),
            method="sigmoid",  # Platt scaling
            cv=5
        )),
    ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
    logger.info("Cross-val accuracy (XGBoost + Platt): %.3f ± %.3f", scores.mean(), scores.std())

    pipeline.fit(X, y)

    y_pred = pipeline.predict(X)
    report = classification_report(
        y, y_pred, target_names=["away_win", "draw", "home_win"]
    )
    logger.info("XGBoost classification report:\n%s", report)

    # 2. Fit Dixon-Coles Poisson Model
    dixon_coles = DixonColesPoisson()
    dixon_coles.fit(elo_diffs, squad_ratios, form_diffs, home_goals, away_goals)

    # Save outputs
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    joblib.dump(dixon_coles, DIXON_COLES_PATH)
    logger.info("XGBoost pipeline saved to %s", MODEL_PATH)
    logger.info("Dixon-Coles Poisson saved to %s", DIXON_COLES_PATH)

    return pipeline


def load_model() -> Pipeline:
    if MODEL_PATH.exists():
        logger.info("Loading match model from %s", MODEL_PATH)
        return joblib.load(MODEL_PATH)
    logger.info("Model not found — training now …")
    return train_model()


def load_dixon_coles() -> DixonColesPoisson:
    if DIXON_COLES_PATH.exists():
        logger.info("Loading Dixon-Coles model from %s", DIXON_COLES_PATH)
        return joblib.load(DIXON_COLES_PATH)
    logger.info("Dixon-Coles not found — training to recover …")
    train_model()
    return joblib.load(DIXON_COLES_PATH)


# ── quick self-test ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("== Training Match Outcome Predictor with Dixon-Coles Poisson ==")
    # Route training through the imported namespace to prevent __main__ class serialization mismatch
    import backend.model_match
    backend.model_match.train_model()
    print("Done")
