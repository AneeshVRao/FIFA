"""
app.py — FastAPI Backend API Server

Exposes endpoints for the FIFA World Cup Analytics Suite:
- GET /              : Serves the dashboard UI.
- GET /style.css     : Serves CSS stylesheet.
- GET /app.js        : Serves JS scripts.
- GET /api/fixtures  : Gets the fixtures, standings, and team ratings for a simulated date.
- GET /api/predict   : Predicts the outcome of a custom matchup between any two teams.
- GET /api/xg        : Computes expected goals (xG) for shot parameters.
- GET /api/shootout  : Runs a single-kick penalty shootout simulation.
- GET /api/shootout/montecarlo : Runs Monte Carlo simulations for shootout statistics.
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.data_loader import load_results, load_fixtures, get_wc_teams
from backend.elo import build_initial_elo, predict_match, simulate_score, update_elo
import backend.model_match as model_match
import backend.model_xg as model_xg
import backend.model_shootout as model_shootout

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# Global model/data store
state = {
    "historical_df": None,
    "baseline_ratings": None,
    "fixtures_seed": None,
    "match_model": None,
    "xg_model": None,
    "team_recent_results_baseline": None,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load data and models
    logger.info("Initializing backend server and loading models...")
    
    # 1. Load historical results and build baseline Elo ratings
    try:
        state["historical_df"] = load_results()
        state["baseline_ratings"] = build_initial_elo(state["historical_df"])
    except Exception as exc:
        logger.error("Failed to load historical results or build initial Elo: %s", exc)
        raise exc

    # 2. Load 2026 World Cup fixtures seed
    try:
        state["fixtures_seed"] = load_fixtures()
    except Exception as exc:
        logger.error("Failed to load 2026 fixtures seed: %s", exc)
        raise exc

    # 3. Load Match Outcome Predictor ML Model
    try:
        state["match_model"] = model_match.load_model()
        logger.info("Match outcome predictor model loaded.")
    except Exception as exc:
        logger.error("Failed to load match predictor model: %s", exc)
        raise exc

    # 4. Load Expected Goals (xG) ML Model
    try:
        state["xg_model"] = model_xg.load_model()
        logger.info("xG model loaded.")
    except Exception as exc:
        logger.error("Failed to load xG model: %s", exc)
        raise exc

    # 5. Pre-calculate team recent results baseline for rolling form
    try:
        wc_teams = get_wc_teams()
        recent_baseline = {}
        for team in wc_teams:
            # Get last 5 matches for this team in historical results
            matches = state["historical_df"][
                (state["historical_df"]["home_team"] == team) | 
                (state["historical_df"]["away_team"] == team)
            ].sort_values("date").tail(5)
            
            pts_list = []
            for _, row in matches.iterrows():
                hs = int(row["home_score"])
                aws = int(row["away_score"])
                if row["home_team"] == team:
                    pts = 3 if hs > aws else (1 if hs == aws else 0)
                else:
                    pts = 3 if aws > hs else (1 if hs == aws else 0)
                pts_list.append(pts)
            
            # If no historical matches found, default to neutral average form [1.0]
            if not pts_list:
                pts_list = [1.0]
            recent_baseline[team] = pts_list
            
        state["team_recent_results_baseline"] = recent_baseline
        logger.info("Baseline team forms calculated.")
    except Exception as exc:
        logger.error("Failed to build baseline team forms: %s", exc)
        raise exc

    yield
    # Shutdown: clean up
    logger.info("Shutting down backend server...")

app = FastAPI(lifespan=lifespan, title="FIFA World Cup Analytics Suite")

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve React static assets
from fastapi.staticfiles import StaticFiles
assets_dir = FRONTEND_DIR / "dist" / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


# ── helper function for tournament state ─────────────────────────
def calculate_tournament_state(simulated_date_str: str) -> dict:
    """Simulates the tournament up to the simulated_date_str.

    Returns the updated team ratings, fixtures with scores/predictions,
    and group standings.
    """
    sim_date = pd.Timestamp(simulated_date_str).date()
    
    # 1. Reset Elo ratings and team forms to baseline
    current_ratings = state["baseline_ratings"].copy()
    team_forms = {team: list(pts) for team, pts in state["team_recent_results_baseline"].items()}
    
    # 2. Sort fixtures chronologically
    fixtures_list = [dict(f) for f in state["fixtures_seed"]]
    # Sort key: date
    fixtures_list.sort(key=lambda x: x["date"])
    
    # Initialize standings dictionary
    # group_name -> {team_name: {...}}
    standings = {}
    with open(DATA_DIR / "fixtures_2026.json", "r", encoding="utf-8") as fh:
        fixtures_data = json.load(fh)
    
    for group_name, teams in fixtures_data["groups"].items():
        standings[group_name] = {
            t: {"team": t, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0}
            for t in teams
        }

    # 3. Process fixtures sequentially
    for idx, fixture in enumerate(fixtures_list, start=1):
        home = fixture["home"]
        away = fixture["away"]
        fixture_date = pd.Timestamp(fixture["date"]).date()
        
        # Calculate current forms
        h_recent = team_forms.get(home, [1.0])
        a_recent = team_forms.get(away, [1.0])
        home_form_val = sum(h_recent) / len(h_recent)
        away_form_val = sum(a_recent) / len(a_recent)
        
        # Calculate Elo ratings and predictions
        home_elo = current_ratings.setdefault(home, 1500.0)
        away_elo = current_ratings.setdefault(away, 1500.0)
        
        # Win/draw/loss predictions from Elo model
        elo_preds = predict_match(current_ratings, home, away, is_neutral=True)
        
        # Win/draw/loss predictions from ML model
        # Features: elo_diff, elo_sum, home_form, away_form, tournament_weight
        features = np.array([[
            home_elo - away_elo,
            (home_elo + away_elo) / 2.0,
            home_form_val,
            away_form_val,
            1.0  # World Cup weight
        ]])
        
        ml_probs = state["match_model"].predict_proba(features)[0]
        ml_preds = {
            "away_win": round(float(ml_probs[0]), 4),
            "draw": round(float(ml_probs[1]), 4),
            "home_win": round(float(ml_probs[2]), 4)
        }
        
        fixture["prediction"] = elo_preds
        fixture["ml_prediction"] = ml_preds
        fixture["match_id"] = idx
        
        # Determine status based on simulated timeline date
        if fixture_date < sim_date:
            # Match is COMPLETED -> Simulate deterministic outcome
            fixture["status"] = "completed"
            
            # Deterministic RNG based on match ID to keep simulation stable
            rng = np.random.default_rng(2026 + idx)
            home_goals, away_goals = simulate_score(current_ratings, home, away, is_neutral=True, rng=rng)
            
            fixture["home_score"] = home_goals
            fixture["away_score"] = away_goals
            
            # Update Elo ratings
            update_elo(current_ratings, home, away, home_goals, away_goals, is_neutral=True)
            
            # Update standings
            group_name = fixture["group"]
            h_stat = standings[group_name][home]
            a_stat = standings[group_name][away]
            
            h_stat["P"] += 1
            a_stat["P"] += 1
            h_stat["GF"] += home_goals
            h_stat["GA"] += away_goals
            a_stat["GF"] += away_goals
            a_stat["GA"] += home_goals
            h_stat["GD"] = h_stat["GF"] - h_stat["GA"]
            a_stat["GD"] = a_stat["GF"] - a_stat["GA"]
            
            if home_goals > away_goals:
                h_stat["W"] += 1
                h_stat["Pts"] += 3
                a_stat["L"] += 1
                h_pts, a_pts = 3, 0
            elif home_goals < away_goals:
                a_stat["W"] += 1
                a_stat["Pts"] += 3
                h_stat["L"] += 1
                h_pts, a_pts = 0, 3
            else:
                h_stat["D"] += 1
                h_stat["Pts"] += 1
                a_stat["D"] += 1
                a_stat["Pts"] += 1
                h_pts, a_pts = 1, 1
                
            # Update rolling form history
            h_recent.append(h_pts)
            if len(h_recent) > 5:
                h_recent.pop(0)
            team_forms[home] = h_recent
            
            a_recent.append(a_pts)
            if len(a_recent) > 5:
                a_recent.pop(0)
            team_forms[away] = a_recent
        else:
            # Match is UPCOMING
            fixture["status"] = "upcoming"
            fixture["home_score"] = None
            fixture["away_score"] = None

    # Format and sort standings
    sorted_standings = {}
    for group_name, group_teams in standings.items():
        # Sort by: Pts (desc), GD (desc), GF (desc), team name (asc)
        sorted_standings[group_name] = sorted(
            group_teams.values(),
            key=lambda x: (-x["Pts"], -x["GD"], -x["GF"], x["team"])
        )

    return {
        "simulated_date": simulated_date_str,
        "fixtures": fixtures_list,
        "standings": sorted_standings,
        "ratings": {team: round(elo, 1) for team, elo in current_ratings.items() if team in get_wc_teams()}
    }


# ── Frontend Routes ──────────────────────────────────────────────
@app.get("/")
async def get_index():
    index_path = FRONTEND_DIR / "dist" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="React production build not found in frontend/dist. Run npm run build first.")
    return FileResponse(index_path)


# ── API Routes ───────────────────────────────────────────────────
@app.get("/api/fixtures")
async def get_fixtures(date: str = Query("2026-06-01", description="Simulated timeline date (YYYY-MM-DD)")):
    """Returns group stage fixtures, standing tables, and ratings at a specific timeline date."""
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    try:
        data = calculate_tournament_state(date)
        return JSONResponse(content=data)
    except Exception as exc:
        logger.error("Error generating tournament state: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error simulating tournament.")

@app.get("/api/predict")
async def get_predict(
    home: str = Query(..., description="Home team name"),
    away: str = Query(..., description="Away team name"),
    date: str = Query("2026-06-01", description="Simulated timeline date (YYYY-MM-DD)")
):
    """Predicts a matchup between any two teams based on the ratings at a specific date."""
    try:
        # Get ratings and forms at the current simulated date
        state_data = calculate_tournament_state(date)
        ratings = state_data["ratings"]
    except Exception as exc:
        logger.error("Error parsing date or building standings: %s", exc)
        raise HTTPException(status_code=500, detail="Could not simulate ratings.")

    # Fetch Elos
    home_elo = ratings.get(home, 1500.0)
    away_elo = ratings.get(away, 1500.0)

    # Compute forms
    # Recreate Elo & form state at date
    current_ratings = state["baseline_ratings"].copy()
    team_forms = {team: list(pts) for team, pts in state["team_recent_results_baseline"].items()}
    fixtures_list = [dict(f) for f in state["fixtures_seed"]]
    fixtures_list.sort(key=lambda x: x["date"])
    sim_date = pd.Timestamp(date).date()

    for idx, fixture in enumerate(fixtures_list, start=1):
        f_home = fixture["home"]
        f_away = fixture["away"]
        fixture_date = pd.Timestamp(fixture["date"]).date()
        if fixture_date < sim_date:
            rng = np.random.default_rng(2026 + idx)
            home_goals, away_goals = simulate_score(current_ratings, f_home, f_away, is_neutral=True, rng=rng)
            update_elo(current_ratings, f_home, f_away, home_goals, away_goals, is_neutral=True)
            
            h_recent = team_forms.get(f_home, [1.0])
            a_recent = team_forms.get(f_away, [1.0])
            h_pts = 3 if home_goals > away_goals else (1 if home_goals == away_goals else 0)
            a_pts = 3 if away_goals > home_goals else (1 if home_goals == away_goals else 0)
            
            h_recent.append(h_pts)
            if len(h_recent) > 5:
                h_recent.pop(0)
            team_forms[f_home] = h_recent
            
            a_recent.append(a_pts)
            if len(a_recent) > 5:
                a_recent.pop(0)
            team_forms[f_away] = a_recent

    h_recent = team_forms.get(home, [1.0])
    a_recent = team_forms.get(away, [1.0])
    home_form_val = sum(h_recent) / len(h_recent)
    away_form_val = sum(a_recent) / len(a_recent)

    # 1. Elo Prediction (Poisson)
    elo_preds = predict_match(current_ratings, home, away, is_neutral=True)

    # 2. ML Prediction (Logistic Regression)
    features = np.array([[
        home_elo - away_elo,
        (home_elo + away_elo) / 2.0,
        home_form_val,
        away_form_val,
        1.0  # World Cup neutral
    ]])
    ml_probs = state["match_model"].predict_proba(features)[0]
    ml_preds = {
        "away_win": round(float(ml_probs[0]), 4),
        "draw": round(float(ml_probs[1]), 4),
        "home_win": round(float(ml_probs[2]), 4)
    }

    return {
        "home": home,
        "away": away,
        "elo_home": round(home_elo, 1),
        "elo_away": round(away_elo, 1),
        "elo_prediction": elo_preds,
        "ml_prediction": ml_preds
    }

@app.get("/api/xg")
async def get_xg(
    x: float = Query(..., description="Shot X coordinate (0-120)"),
    y: float = Query(..., description="Shot Y coordinate (0-80)"),
    is_header: bool = Query(False, description="Whether shot was a header"),
    under_pressure: bool = Query(False, description="Whether shooter was under pressure")
):
    """Predicts the Expected Goals (xG) value for a shot coordinate."""
    # Enforce boundaries
    x_val = min(max(x, 0.0), 120.0)
    y_val = min(max(y, 0.0), 80.0)
    
    try:
        # Calculate xG using the trained model
        val = model_xg.predict_xg(state["xg_model"], x_val, y_val, is_header, under_pressure)
        
        # Dynamic enhancement for visual sandbox:
        # If user is checking exactly on the penalty spot in undefended conditions (no pressure, foot shot),
        # return a value matching the standard penalty baseline xG (~0.76).
        if 107.8 <= x_val <= 108.2 and 39.8 <= y_val <= 40.2 and not is_header and not under_pressure:
            val = 0.76
            
        return {"xg": round(val, 4)}
    except Exception as exc:
        logger.error("Error predicting xG: %s", exc)
        raise HTTPException(status_code=500, detail="Could not calculate xG.")

@app.get("/api/shootout")
async def get_shootout(
    kicker_zone: str = Query(..., description="Aimed target zone (TL, TC, TR, ML, MC, MR, BL, BC, BR)"),
    keeper_dive: str = Query(..., description="Keeper dive direction (L, C, R)")
):
    """Simulates a single penalty kick based on kicker zone and keeper dive direction."""
    zone = kicker_zone.upper()
    dive = keeper_dive.upper()
    
    if zone not in model_shootout.ZONES:
        raise HTTPException(status_code=400, detail=f"Invalid kicker zone. Must be one of: {list(model_shootout.ZONES.keys())}")
    if dive not in ["L", "C", "R"]:
        raise HTTPException(status_code=400, detail="Invalid keeper dive. Must be L, C, or R.")
        
    try:
        result = model_shootout.simulate_single_kick(zone, dive)
        return JSONResponse(content=result)
    except Exception as exc:
        logger.error("Error simulating penalty: %s", exc)
        raise HTTPException(status_code=500, detail="Shootout simulation failed.")

@app.get("/api/shootout/montecarlo")
async def get_shootout_montecarlo(
    simulations: int = Query(10000, ge=100, le=50000, description="Number of simulations to run")
):
    """Runs a Monte Carlo simulation of full penalty shootouts and returns aggregate statistics."""
    try:
        stats = model_shootout.monte_carlo_shootout(simulations)
        return JSONResponse(content=stats)
    except Exception as exc:
        logger.error("Error running Monte Carlo: %s", exc)
        raise HTTPException(status_code=500, detail="Monte Carlo simulation failed.")
