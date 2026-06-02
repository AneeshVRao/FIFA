"""
model_xg.py — Expected Goals (xG) Model Training Pipeline

Trains three models for shot quality evaluation:
1. Logistic Regression Baseline : Spatial features only.
2. XGBoost Pre-Shot Model      : Incorporates spatial features and StatsBomb 360°
                                 freeze frame data (player densities, GK positioning).
3. XGBoost Post-Shot Model     : Predicts goals after shot execution based on target
                                 placement and GK-to-placement distance (xGOT).

Features
--------
Pre-shot (10 features):
- distance_to_goal
- angle_to_goal
- is_header
- under_pressure
- x, y (normalised)
- num_defenders
- num_teammates
- gk_distance_to_goal
- gk_distance_to_shooter

Post-shot (4 features):
- pre_shot_xg
- placement_y_diff
- placement_z
- gk_distance_to_placement
"""

import logging
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = DATA_DIR / "model_xg.pkl"
SHOTS_CACHE = DATA_DIR / "shots_cache.csv"

PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0
GOAL_Y_CENTER = PITCH_WIDTH / 2.0  # 40
GOAL_HALF_WIDTH = 4.0  # yards in StatsBomb space


# ── geometry helpers ─────────────────────────────────────────────
def distance_to_goal(x: float, y: float) -> float:
    return math.sqrt((PITCH_LENGTH - x) ** 2 + (GOAL_Y_CENTER - y) ** 2)


def angle_to_goal(x: float, y: float) -> float:
    goal_x = PITCH_LENGTH
    post_top = GOAL_Y_CENTER + GOAL_HALF_WIDTH
    post_bot = GOAL_Y_CENTER - GOAL_HALF_WIDTH

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
    if SHOTS_CACHE.exists():
        logger.info("Loading cached shots from %s", SHOTS_CACHE)
        return pd.read_csv(SHOTS_CACHE)

    try:
        from statsbombpy import sb

        logger.info("Fetching StatsBomb competitions …")
        comps = sb.competitions()

        target_comps = comps[
            (comps["competition_name"].str.contains("World Cup|Euro", case=False, na=False))
            & (comps["season_name"].str.contains("2018|2022|2024|2020", na=False))
        ]

        if target_comps.empty:
            target_comps = comps.head(5)
            logger.warning("No World Cup/Euro competitions found. Using first 5 comps.")

        all_shots = []
        for _, comp in target_comps.iterrows():
            comp_id = int(comp["competition_id"])
            season_id = int(comp["season_id"])
            logger.info("  Fetching matches for %s %s …", comp["competition_name"], comp["season_name"])

            try:
                matches = sb.matches(competition_id=comp_id, season_id=season_id)
            except Exception:
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
                    if loc is None or not isinstance(loc, (list, tuple)) or len(loc) < 2:
                        continue

                    x, y = float(loc[0]), float(loc[1])
                    body = str(shot.get("shot_body_part", "")).lower()
                    is_header = 1 if "head" in body else 0
                    pressure = 1 if shot.get("under_pressure", False) else 0
                    outcome = str(shot.get("shot_outcome", "")).lower()
                    is_goal = 1 if "goal" in outcome else 0

                    # 360° freeze frame parsing
                    freeze_frame = shot.get("shot_freeze_frame", None)
                    num_defenders = 0
                    num_teammates = 0
                    gk_x, gk_y = 119.0, 40.0

                    if freeze_frame and isinstance(freeze_frame, list):
                        for p in freeze_frame:
                            pos_name = p.get("position", {}).get("name", "")
                            is_teammate = p.get("teammate", False)

                            if pos_name == "Goalkeeper":
                                p_loc = p.get("location", [119.0, 40.0])
                                gk_x, gk_y = float(p_loc[0]), float(p_loc[1])
                            elif is_teammate:
                                num_teammates += 1
                            else:
                                num_defenders += 1

                    # Post-shot target placement tracking
                    end_loc = shot.get("shot_end_location", None)
                    on_target = 0
                    placement_y = 40.0
                    placement_z = 0.0
                    if end_loc and isinstance(end_loc, list) and len(end_loc) >= 2:
                        if any(term in outcome for term in ["goal", "saved", "post", "bar"]):
                            on_target = 1
                            placement_y = float(end_loc[1])
                            if len(end_loc) >= 3:
                                placement_z = float(end_loc[2])

                    all_shots.append({
                        "x": x,
                        "y": y,
                        "is_header": is_header,
                        "under_pressure": pressure,
                        "num_defenders": num_defenders,
                        "num_teammates": num_teammates,
                        "gk_x": gk_x,
                        "gk_y": gk_y,
                        "on_target": on_target,
                        "placement_y": placement_y,
                        "placement_z": placement_z,
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
    rng = np.random.default_rng(42)

    x = rng.uniform(80, 120, size=n)
    y = rng.uniform(10, 70, size=n)
    is_header = rng.binomial(1, 0.15, size=n)
    under_pressure = rng.binomial(1, 0.35, size=n)

    num_defenders = rng.poisson(lam=2.0, size=n)
    num_teammates = rng.poisson(lam=1.2, size=n)
    
    gk_x = rng.uniform(117.0, 119.9, size=n)
    gk_y = rng.uniform(37.0, 43.0, size=n)
    
    on_target = rng.binomial(1, 0.45, size=n)
    placement_y = rng.uniform(36.5, 43.5, size=n)
    placement_z = rng.uniform(0.0, 2.4, size=n)

    goals = []
    for i in range(n):
        dist = distance_to_goal(x[i], y[i])
        angle = angle_to_goal(x[i], y[i])

        base_prob = max(0.02, 0.85 - 0.02 * dist)
        angle_factor = min(1.0, angle / 0.5)
        prob = base_prob * angle_factor

        if is_header[i]:
            prob *= 0.75
        if under_pressure[i]:
            prob *= 0.8
        
        if 107 < x[i] < 109 and 38 < y[i] < 42:
            prob = 0.76

        prob = min(max(prob, 0.01), 0.95)
        is_g = int(rng.random() < prob)
        goals.append(is_g)
        
        if is_g == 1:
            on_target[i] = 1

    df = pd.DataFrame({
        "x": x,
        "y": y,
        "is_header": is_header,
        "under_pressure": under_pressure,
        "num_defenders": num_defenders,
        "num_teammates": num_teammates,
        "gk_x": gk_x,
        "gk_y": gk_y,
        "on_target": on_target,
        "placement_y": placement_y,
        "placement_z": placement_z,
        "is_goal": goals,
    })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(SHOTS_CACHE, index=False)
    logger.info("Generated %d synthetic shots (cached)", n)
    return df


# ── feature engineering ──────────────────────────────────────────
def build_features_baseline(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    distances = [distance_to_goal(x, y) for x, y in zip(df["x"].values, df["y"].values)]
    angles = [angle_to_goal(x, y) for x, y in zip(df["x"].values, df["y"].values)]

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


def build_features_main(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    distances = [distance_to_goal(x, y) for x, y in zip(df["x"].values, df["y"].values)]
    angles = [angle_to_goal(x, y) for x, y in zip(df["x"].values, df["y"].values)]

    gk_dist_goal = [distance_to_goal(gx, gy) for gx, gy in zip(df["gk_x"].values, df["gk_y"].values)]
    gk_dist_shooter = [math.sqrt((gx - sx)**2 + (gy - sy)**2) for gx, gy, sx, sy in zip(
        df["gk_x"].values, df["gk_y"].values, df["x"].values, df["y"].values
    )]

    X = np.column_stack([
        distances,
        angles,
        df["is_header"].values,
        df["under_pressure"].values,
        df["x"].values / PITCH_LENGTH,
        df["y"].values / PITCH_WIDTH,
        df["num_defenders"].values,
        df["num_teammates"].values,
        gk_dist_goal,
        gk_dist_shooter,
    ])
    y = df["is_goal"].values.astype(int)
    return X, y


# ── training ─────────────────────────────────────────────────────
def train_model():
    logger.info("Collecting shot data …")
    df = _fetch_statsbomb_shots()

    df = df[(df["x"] >= 0) & (df["x"] <= PITCH_LENGTH)]
    df = df[(df["y"] >= 0) & (df["y"] <= PITCH_WIDTH)]
    df = df.dropna()
    logger.info("Training on %d valid shots", len(df))

    # 1. Train Logistic Baseline (6 spatial features)
    X_base, y_base = build_features_baseline(df)
    from sklearn.linear_model import LogisticRegression
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    base_scores = cross_val_score(lr_pipeline, X_base, y_base, cv=cv, scoring="roc_auc")
    logger.info("Baseline Spatial LR CV ROC-AUC: %.3f ± %.3f", base_scores.mean(), base_scores.std())
    lr_pipeline.fit(X_base, y_base)

    # 2. Train XGBoost Main Model (10 features)
    X_main, y_main = build_features_main(df)
    xgb_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", XGBClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            random_state=42,
            eval_metric="logloss"
        )),
    ])
    main_scores = cross_val_score(xgb_pipeline, X_main, y_main, cv=cv, scoring="roc_auc")
    logger.info("Main Pre-Shot XGBoost CV ROC-AUC: %.3f ± %.3f", main_scores.mean(), main_scores.std())
    xgb_pipeline.fit(X_main, y_main)

    # 3. Train Post-Shot Model (xGOT)
    # Fit only on shots that are on target
    df_ontarget = df[df["on_target"] == 1].copy()
    logger.info("Training Post-Shot xGOT model on %d on-target shots", len(df_ontarget))
    
    # Calculate pre-shot xG for each of these shots
    pre_shot_xg = xgb_pipeline.predict_proba(X_main[df["on_target"] == 1])[:, 1]
    
    placement_y_diff = np.abs(df_ontarget["placement_y"].values - GOAL_Y_CENTER)
    placement_z = df_ontarget["placement_z"].values
    
    gk_dist_placement = []
    for gx, gy, py, pz in zip(
        df_ontarget["gk_x"].values, df_ontarget["gk_y"].values,
        df_ontarget["placement_y"].values, df_ontarget["placement_z"].values
    ):
        dist = math.sqrt((gx - PITCH_LENGTH)**2 + (gy - py)**2 + (0.0 - pz)**2)
        gk_dist_placement.append(dist)
        
    X_post = np.column_stack([
        pre_shot_xg,
        placement_y_diff,
        placement_z,
        gk_dist_placement
    ])
    y_post = df_ontarget["is_goal"].values.astype(int)
    
    post_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", XGBClassifier(
            n_estimators=80,
            learning_rate=0.05,
            max_depth=3,
            random_state=42,
            eval_metric="logloss"
        )),
    ])
    post_scores = cross_val_score(post_pipeline, X_post, y_post, cv=cv, scoring="roc_auc")
    logger.info("Post-Shot xGOT XGBoost CV ROC-AUC: %.3f ± %.3f", post_scores.mean(), post_scores.std())
    post_pipeline.fit(X_post, y_post)

    # Persist all 3 models in a dictionary
    save_dict = {
        "logistic_baseline": lr_pipeline,
        "xgboost_main": xgb_pipeline,
        "post_shot_model": post_pipeline
    }
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(save_dict, MODEL_PATH)
    logger.info("Persisted all three xG models to %s", MODEL_PATH)
    return save_dict


def load_model() -> Pipeline:
    """Return the main pre-shot XGBoost pipeline for backward compatibility."""
    if MODEL_PATH.exists():
        logger.info("Loading xG model dictionary from %s", MODEL_PATH)
        data = joblib.load(MODEL_PATH)
        if isinstance(data, dict):
            return data["xgboost_main"]
        return data
    logger.info("xG models not found — training now …")
    data = train_model()
    return data["xgboost_main"]


def load_all_models() -> dict:
    """Return the entire model dictionary containing baseline, main, and post-shot models."""
    if MODEL_PATH.exists():
        logger.info("Loading all xG models from %s", MODEL_PATH)
        data = joblib.load(MODEL_PATH)
        if isinstance(data, dict):
            return data
        # If legacy format, wrap it
        return {
            "logistic_baseline": data,
            "xgboost_main": data,
            "post_shot_model": data
        }
    logger.info("xG models not found — training now …")
    return train_model()


def predict_xg(
    pipeline: Pipeline,
    x: float,
    y: float,
    is_header: bool = False,
    under_pressure: bool = False,
    num_defenders: int = 2,
    num_teammates: int = 1,
    gk_x: float = 119.0,
    gk_y: float = 40.0
) -> float:
    """Predict pre-shot xG using the main XGBoost model and positional features."""
    dist = distance_to_goal(x, y)
    angle = angle_to_goal(x, y)
    gk_dist_goal = distance_to_goal(gk_x, gk_y)
    gk_dist_shooter = math.sqrt((gk_x - x)**2 + (gk_y - y)**2)

    features = np.array([[
        dist,
        angle,
        int(is_header),
        int(under_pressure),
        x / PITCH_LENGTH,
        y / PITCH_WIDTH,
        num_defenders,
        num_teammates,
        gk_dist_goal,
        gk_dist_shooter
    ]])
    return float(pipeline.predict_proba(features)[:, 1][0])


def predict_baseline_xg(
    pipeline: Pipeline,
    x: float,
    y: float,
    is_header: bool = False,
    under_pressure: bool = False
) -> float:
    """Predict pre-shot xG using the baseline Logistic Regression model (6 spatial features)."""
    dist = distance_to_goal(x, y)
    angle = angle_to_goal(x, y)

    features = np.array([[
        dist,
        angle,
        int(is_header),
        int(under_pressure),
        x / PITCH_LENGTH,
        y / PITCH_WIDTH,
    ]])
    return float(pipeline.predict_proba(features)[:, 1][0])


def predict_post_shot_xg(
    post_pipeline: Pipeline,
    pre_shot_xg: float,
    placement_y: float,
    placement_z: float,
    gk_x: float,
    gk_y: float
) -> float:
    """Predict post-shot xGOT based on target placement and GK distance."""
    placement_y_diff = abs(placement_y - GOAL_Y_CENTER)
    gk_dist_placement = math.sqrt((gk_x - PITCH_LENGTH)**2 + (gk_y - placement_y)**2 + (0.0 - placement_z)**2)
    
    features = np.array([[
        pre_shot_xg,
        placement_y_diff,
        placement_z,
        gk_dist_placement
    ]])
    return float(post_pipeline.predict_proba(features)[:, 1][0])


# ── quick self-test ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("== Training Expected Goals (xG & xGOT) Pipeline ==")
    models = train_model()

    print("\n  Pre-Shot xG Prediction (Penalty Spot, undefended):")
    main_model = models["xgboost_main"]
    val = predict_xg(main_model, 108, 40, False, False, num_defenders=0, num_teammates=0, gk_x=119.0, gk_y=40.0)
    print(f"    xG = {val:.4f}")

    print("\n  Post-Shot xGOT Prediction (Low corner, keeper out-of-position):")
    post_model = models["post_shot_model"]
    post_val = predict_post_shot_xg(post_model, val, placement_y=37.5, placement_z=0.2, gk_x=119.0, gk_y=43.0)
    print(f"    xGOT = {post_val:.4f}")

    print("\nDone")
