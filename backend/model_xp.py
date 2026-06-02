"""
model_xp.py — Pass Completion Probability (xP) Model Pipeline

Trains an XGBoost classifier on StatsBomb pass events using coordinates,
distance, angle, headers, and pressure status to predict pass success.
Saves model pipeline to data/model_xp.pkl.
"""

import logging
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
XP_MODEL_PATH = DATA_DIR / "model_xp.pkl"


def compute_pass_features(start_x: float, start_y: float, end_x: float, end_y: float, is_header: int, under_pressure: int) -> np.ndarray:
    """Helper to compute engineered features (distance and angle) and return in correct order."""
    dx = end_x - start_x
    dy = end_y - start_y
    distance = np.sqrt(dx**2 + dy**2)
    angle = np.arctan2(dy, dx)
    
    return np.array([
        start_x,
        start_y,
        end_x,
        end_y,
        distance,
        angle,
        float(is_header),
        float(under_pressure)
    ]).reshape(1, -1)


def _generate_synthetic_passes(n: int = 12000) -> pd.DataFrame:
    """Generates highly realistic pass data to train the model offline."""
    rng = np.random.default_rng(42)
    
    start_x = rng.uniform(0, 115, size=n)
    start_y = rng.uniform(5, 75, size=n)
    
    # Move forward or lateral
    dx = rng.normal(15, 12, size=n)
    dy = rng.normal(0, 15, size=n)
    
    end_x = np.clip(start_x + dx, 0.0, 120.0)
    end_y = np.clip(start_y + dy, 0.0, 80.0)
    
    is_header = rng.choice([0, 1], p=[0.92, 0.08], size=n)
    under_pressure = rng.choice([0, 1], p=[0.75, 0.25], size=n)
    
    # Calculate features for target generation
    dist = np.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    
    # Probability of completion: base rate 0.88, decreases with distance, pressure, headers, and forward direction
    # Defensive third has higher success rate
    success_rate = 0.90 - 0.007 * dist - 0.18 * under_pressure - 0.22 * is_header - 0.001 * (start_x)
    success_rate = np.clip(success_rate, 0.05, 0.98)
    
    success = (rng.random(size=n) < success_rate).astype(int)
    
    # Combine into DataFrame
    data = []
    for i in range(n):
        dx_val = end_x[i] - start_x[i]
        dy_val = end_y[i] - start_y[i]
        dist_val = np.sqrt(dx_val**2 + dy_val**2)
        angle_val = np.arctan2(dy_val, dx_val)
        
        data.append({
            "start_x": start_x[i],
            "start_y": start_y[i],
            "end_x": end_x[i],
            "end_y": end_y[i],
            "pass_distance": dist_val,
            "pass_angle": angle_val,
            "is_header": is_header[i],
            "under_pressure": under_pressure[i],
            "success": success[i]
        })
        
    return pd.DataFrame(data)


def train_xp_model() -> Pipeline:
    """Extract pass events from StatsBomb data, train XGBoost model, and serialize."""
    logger.info("Starting Pass Completion Probability (xP) training pipeline...")
    
    try:
        from statsbombpy import sb
        logger.info("Attempting to fetch real StatsBomb passes...")
        comps = sb.competitions()
        target_comps = comps[
            (comps["competition_name"].str.contains("World Cup", case=False, na=False))
            & (comps["season_name"].str.contains("2022", na=False))
        ]
        
        all_passes = []
        if not target_comps.empty:
            comp_id = int(target_comps.iloc[0]["competition_id"])
            season_id = int(target_comps.iloc[0]["season_id"])
            matches = sb.matches(competition_id=comp_id, season_id=season_id).head(8)
            
            for _, match in matches.iterrows():
                match_id = int(match["match_id"])
                events = sb.events(match_id=match_id)
                p_events = events[events["type"] == "Pass"].copy()
                
                for _, p in p_events.iterrows():
                    loc = p.get("location")
                    eloc = p.get("pass_end_location")
                    if loc and eloc and len(loc) >= 2 and len(eloc) >= 2:
                        outcome = p.get("pass_outcome")
                        success = 0 if pd.notna(outcome) else 1
                        
                        body = str(p.get("pass_body_part", "")).lower()
                        is_header = 1 if "head" in body else 0
                        pressure = 1 if p.get("under_pressure", False) else 0
                        
                        # Distance & Angle
                        dx = eloc[0] - loc[0]
                        dy = eloc[1] - loc[1]
                        dist = np.sqrt(dx**2 + dy**2)
                        angle = np.arctan2(dy, dx)
                        
                        all_passes.append({
                            "start_x": loc[0],
                            "start_y": loc[1],
                            "end_x": eloc[0],
                            "end_y": eloc[1],
                            "pass_distance": dist,
                            "pass_angle": angle,
                            "is_header": is_header,
                            "under_pressure": pressure,
                            "success": success
                        })
                        
        if len(all_passes) > 1000:
            df = pd.DataFrame(all_passes)
            logger.info("Loaded %d real pass events from StatsBomb for training", len(df))
        else:
            raise ValueError("Insufficient pass events fetched. Falling back to synthetic generator.")
            
    except Exception as exc:
        logger.warning("Could not fetch real StatsBomb passes (%s). Using high-fidelity synthetic generator.", exc)
        df = _generate_synthetic_passes()
        
    # Feature columns and labels
    feature_cols = [
        "start_x", "start_y", "end_x", "end_y",
        "pass_distance", "pass_angle", "is_header", "under_pressure"
    ]
    X = df[feature_cols].values
    y = df["success"].values
    
    # Construct Pipeline
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", XGBClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            random_state=42,
            eval_metric="logloss"
        ))
    ])
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
    logger.info("xP Cross-validation accuracy: %.3f ± %.3f", scores.mean(), scores.std())
    
    # Fit model
    pipeline.fit(X, y)
    
    # Save model
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, XP_MODEL_PATH)
    logger.info("Pass Completion Probability (xP) model saved to %s", XP_MODEL_PATH)
    
    return pipeline


def load_xp_model() -> Pipeline:
    """Load the trained xP pipeline, or train it if not cached."""
    if XP_MODEL_PATH.exists():
        return joblib.load(XP_MODEL_PATH)
    return train_xp_model()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("== Training Pass Completion Probability (xP) Model ==")
    pipe = train_xp_model()
    
    # Test prediction
    test_feat = compute_pass_features(50, 40, 70, 50, 0, 0)
    prob = pipe.predict_proba(test_feat)[0, 1]
    print(f"Test Pass Completion Prob (50,40 -> 70,50): {prob * 100:.2f}%")
    print("Done.")
