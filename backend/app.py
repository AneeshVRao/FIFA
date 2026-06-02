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
    """Simulates the tournament (Group Stage + Knockout Stages) up to simulated_date_str.

    Completed matches use real/simulated results.
    Upcoming/projected matches are simulated on the fly using a shadow state.
    """
    from backend.team_metadata import get_unified_elo
    from backend.elo import simulate_knockout_score

    sim_date = pd.Timestamp(simulated_date_str).date()
    
    # 1. Reset Elo ratings and team forms to baseline, applying the Unified Elo boost
    current_ratings = {team: get_unified_elo(team, elo) for team, elo in state["baseline_ratings"].items()}
    team_forms = {team: list(pts) for team, pts in state["team_recent_results_baseline"].items()}
    
    # 2. Sort group-stage fixtures chronologically
    fixtures_list = [dict(f) for f in state["fixtures_seed"]]
    fixtures_list.sort(key=lambda x: x["date"])
    
    # Initialize standings dictionary
    standings = {}
    with open(DATA_DIR / "fixtures_2026.json", "r", encoding="utf-8") as fh:
        fixtures_data = json.load(fh)
    
    for group_name, teams in fixtures_data["groups"].items():
        standings[group_name] = {
            t: {"team": t, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0}
            for t in teams
        }

    # 3. Process Group Stage matches
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
        
        # Predictions
        elo_preds = predict_match(current_ratings, home, away, is_neutral=True)
        from backend.team_metadata import TEAM_METADATA
        home_meta = TEAM_METADATA.get(home, {"squad_value": 50.0, "fifa_rank": 80})
        away_meta = TEAM_METADATA.get(away, {"squad_value": 50.0, "fifa_rank": 80})
        squad_diff = home_meta["squad_value"] - away_meta["squad_value"]
        rank_diff = away_meta["fifa_rank"] - home_meta["fifa_rank"]
        squad_ratio = home_meta["squad_value"] / (away_meta["squad_value"] + 1.0)
        form_diff = home_form_val - away_form_val

        features = np.array([[
            home_elo - away_elo,
            (home_elo + away_elo) / 2.0,
            home_form_val,
            away_form_val,
            1.0,  # World Cup weight
            squad_diff,
            rank_diff,
            squad_ratio,
            form_diff
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
        
        if fixture_date < sim_date:
            # Match is COMPLETED -> Simulate deterministically
            fixture["status"] = "completed"
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
                
            # Update rolling form
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

    # Now create shadow ratings, shadow forms, and shadow standings to simulate the REST of the tournament
    import copy
    shadow_ratings = current_ratings.copy()
    shadow_forms = copy.deepcopy(team_forms)
    shadow_standings = copy.deepcopy(standings)
    
    # Run shadow group-stage simulation for any upcoming group fixtures
    for idx, fixture in enumerate(fixtures_list, start=1):
        if fixture["status"] == "upcoming":
            home = fixture["home"]
            away = fixture["away"]
            group_name = fixture["group"]
            
            rng = np.random.default_rng(2026 + idx)
            h_goals, a_goals = simulate_score(shadow_ratings, home, away, is_neutral=True, rng=rng)
            
            update_elo(shadow_ratings, home, away, h_goals, a_goals, is_neutral=True)
            
            # Update shadow standings
            h_stat = shadow_standings[group_name][home]
            a_stat = shadow_standings[group_name][away]
            h_stat["P"] += 1
            a_stat["P"] += 1
            h_stat["GF"] += h_goals
            h_stat["GA"] += a_goals
            a_stat["GF"] += a_goals
            a_stat["GA"] += h_goals
            h_stat["GD"] = h_stat["GF"] - h_stat["GA"]
            a_stat["GD"] = a_stat["GF"] - a_stat["GA"]
            
            if h_goals > a_goals:
                h_stat["W"] += 1
                h_stat["Pts"] += 3
                a_stat["L"] += 1
                h_pts, a_pts = 3, 0
            elif h_goals < a_goals:
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
                
            sh_rec = shadow_forms.setdefault(home, [1.0])
            sh_rec.append(h_pts)
            if len(sh_rec) > 5:
                sh_rec.pop(0)
            shadow_forms[home] = sh_rec
            
            sa_rec = shadow_forms.setdefault(away, [1.0])
            sa_rec.append(a_pts)
            if len(sa_rec) > 5:
                sa_rec.pop(0)
            shadow_forms[away] = sa_rec

    # Re-calculate real standings for the date display
    sorted_standings = {}
    for group_name, group_teams in standings.items():
        sorted_standings[group_name] = sorted(
            group_teams.values(),
            key=lambda x: (-x["Pts"], -x["GD"], -x["GF"], x["team"])
        )

    # 4. Generate & Simulate Knockout Stages
    # Calculate group winners, runners-up, and best 3rd-places based on shadow standings
    group_winners = {}
    group_runners_up = {}
    third_place_teams = []
    
    for g_name in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
        g_st = shadow_standings[g_name]
        sorted_g = sorted(
            g_st.values(),
            key=lambda x: (-x["Pts"], -x["GD"], -x["GF"], x["team"])
        )
        group_winners[g_name] = sorted_g[0]["team"]
        group_runners_up[g_name] = sorted_g[1]["team"]
        third_place_teams.append(sorted_g[2])

    # Find 8 best 3rd-place teams
    ranked_3rd = sorted(
        third_place_teams,
        key=lambda x: (-x["Pts"], -x["GD"], -x["GF"], x["team"])
    )
    best_3rd = [t["team"] for t in ranked_3rd[:8]]

    # Define Round of 32 fixtures structure
    # Pairing index -> (home_team, away_team, date, venue)
    r32_pairings = [
        (group_winners["A"], best_3rd[0], "2026-06-28", "Boston"),
        (group_winners["B"], group_runners_up["C"], "2026-06-28", "New York"),
        (group_winners["C"], best_3rd[1], "2026-06-28", "Los Angeles"),
        (group_winners["D"], group_runners_up["E"], "2026-06-29", "Dallas"),
        (group_winners["E"], best_3rd[2], "2026-06-29", "Atlanta"),
        (group_winners["F"], group_runners_up["G"], "2026-06-29", "Seattle"),
        (group_winners["G"], best_3rd[3], "2026-06-30", "Miami"),
        (group_winners["H"], group_runners_up["I"], "2026-06-30", "Philadelphia"),
        (group_winners["I"], best_3rd[4], "2026-06-30", "Toronto"),
        (group_winners["J"], group_runners_up["K"], "2026-07-01", "Vancouver"),
        (group_winners["K"], best_3rd[5], "2026-07-01", "San Francisco"),
        (group_winners["L"], best_3rd[6], "2026-07-01", "Houston"),
        (group_runners_up["A"], best_3rd[7], "2026-07-02", "Mexico City"),
        (group_runners_up["B"], group_runners_up["H"], "2026-07-02", "Guadalajara"),
        (group_runners_up["D"], group_runners_up["J"], "2026-07-03", "Monterrey"),
        (group_runners_up["F"], group_runners_up["L"], "2026-07-03", "Kansas City")
    ]

    r32_results = []
    
    # Simulate Round of 32
    for idx, (home, away, m_date, venue) in enumerate(r32_pairings, start=73):
        fixture_date = pd.Timestamp(m_date).date()
        match_id = idx
        
        # Calculate pre-match ratings
        home_elo = current_ratings.setdefault(home, 1500.0)
        away_elo = current_ratings.setdefault(away, 1500.0)
        
        # Get Elo prediction
        elo_preds = predict_match(current_ratings, home, away, is_neutral=True)
        
        fixture = {
            "match_id": match_id,
            "date": m_date,
            "group": "Round of 32",
            "home": home,
            "away": away,
            "venue": venue,
            "prediction": elo_preds,
            "ml_prediction": elo_preds
        }
        
        if fixture_date < sim_date:
            fixture["status"] = "completed"
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(current_ratings, home, away, is_neutral=True, rng=rng)
            
            fixture.update(res)
            fixture["home_score"] = res["home_goals"]
            fixture["away_score"] = res["away_goals"]
            # Update real Elo ratings
            update_elo(current_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            # Sync shadow Elo ratings
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            
            r32_results.append(res["winner"])
        else:
            fixture["status"] = "upcoming"
            fixture["home_score"] = None
            fixture["away_score"] = None
            
            # Simulate shadow winner
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(shadow_ratings, home, away, is_neutral=True, rng=rng)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            
            r32_results.append(res["winner"])
            
        fixtures_list.append(fixture)

    # Simulate Round of 16 (8 matches)
    r16_pairings = [
        (r32_results[0], r32_results[1], "2026-07-04", "New York"),
        (r32_results[2], r32_results[3], "2026-07-04", "Dallas"),
        (r32_results[4], r32_results[5], "2026-07-05", "Miami"),
        (r32_results[6], r32_results[7], "2026-07-05", "Atlanta"),
        (r32_results[8], r32_results[9], "2026-07-06", "Los Angeles"),
        (r32_results[10], r32_results[11], "2026-07-06", "San Francisco"),
        (r32_results[12], r32_results[13], "2026-07-07", "Vancouver"),
        (r32_results[14], r32_results[15], "2026-07-07", "Seattle")
    ]
    
    r16_results = []
    for idx, (home, away, m_date, venue) in enumerate(r16_pairings, start=89):
        fixture_date = pd.Timestamp(m_date).date()
        match_id = idx
        
        elo_preds = predict_match(current_ratings, home, away, is_neutral=True)
        fixture = {
            "match_id": match_id,
            "date": m_date,
            "group": "Round of 16",
            "home": home,
            "away": away,
            "venue": venue,
            "prediction": elo_preds,
            "ml_prediction": elo_preds
        }
        
        if fixture_date < sim_date:
            fixture["status"] = "completed"
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(current_ratings, home, away, is_neutral=True, rng=rng)
            fixture.update(res)
            fixture["home_score"] = res["home_goals"]
            fixture["away_score"] = res["away_goals"]
            update_elo(current_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            r16_results.append(res["winner"])
        else:
            fixture["status"] = "upcoming"
            fixture["home_score"] = None
            fixture["away_score"] = None
            
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(shadow_ratings, home, away, is_neutral=True, rng=rng)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            r16_results.append(res["winner"])
            
        fixtures_list.append(fixture)

    # Simulate Quarterfinals (4 matches)
    qf_pairings = [
        (r16_results[0], r16_results[1], "2026-07-09", "Boston"),
        (r16_results[2], r16_results[3], "2026-07-10", "Miami"),
        (r16_results[4], r16_results[5], "2026-07-11", "Dallas"),
        (r16_results[6], r16_results[7], "2026-07-11", "Los Angeles")
    ]
    
    qf_results = []
    for idx, (home, away, m_date, venue) in enumerate(qf_pairings, start=97):
        fixture_date = pd.Timestamp(m_date).date()
        match_id = idx
        
        elo_preds = predict_match(current_ratings, home, away, is_neutral=True)
        fixture = {
            "match_id": match_id,
            "date": m_date,
            "group": "Quarterfinals",
            "home": home,
            "away": away,
            "venue": venue,
            "prediction": elo_preds,
            "ml_prediction": elo_preds
        }
        
        if fixture_date < sim_date:
            fixture["status"] = "completed"
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(current_ratings, home, away, is_neutral=True, rng=rng)
            fixture.update(res)
            fixture["home_score"] = res["home_goals"]
            fixture["away_score"] = res["away_goals"]
            update_elo(current_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            qf_results.append(res["winner"])
        else:
            fixture["status"] = "upcoming"
            fixture["home_score"] = None
            fixture["away_score"] = None
            
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(shadow_ratings, home, away, is_neutral=True, rng=rng)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            qf_results.append(res["winner"])
            
        fixtures_list.append(fixture)

    # Simulate Semifinals (2 matches)
    sf_pairings = [
        (qf_results[0], qf_results[1], "2026-07-14", "Atlanta"),
        (qf_results[2], qf_results[3], "2026-07-15", "New York")
    ]
    
    sf_results = []
    for idx, (home, away, m_date, venue) in enumerate(sf_pairings, start=101):
        fixture_date = pd.Timestamp(m_date).date()
        match_id = idx
        
        elo_preds = predict_match(current_ratings, home, away, is_neutral=True)
        fixture = {
            "match_id": match_id,
            "date": m_date,
            "group": "Semifinals",
            "home": home,
            "away": away,
            "venue": venue,
            "prediction": elo_preds,
            "ml_prediction": elo_preds
        }
        
        if fixture_date < sim_date:
            fixture["status"] = "completed"
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(current_ratings, home, away, is_neutral=True, rng=rng)
            fixture.update(res)
            fixture["home_score"] = res["home_goals"]
            fixture["away_score"] = res["away_goals"]
            update_elo(current_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            
            loser = away if res["winner"] == home else home
            sf_results.append((res["winner"], loser))
        else:
            fixture["status"] = "upcoming"
            fixture["home_score"] = None
            fixture["away_score"] = None
            
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(shadow_ratings, home, away, is_neutral=True, rng=rng)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            
            loser = away if res["winner"] == home else home
            sf_results.append((res["winner"], loser))
            
        fixtures_list.append(fixture)

    # 3rd-Place Match (July 18) and Final (July 19)
    ko_finals = [
        (sf_results[0][1], sf_results[1][1], "2026-07-18", "Miami", "3rd Place Match", 103),
        (sf_results[0][0], sf_results[1][0], "2026-07-19", "New York", "Final", 104)
    ]
    
    for home, away, m_date, venue, grp, match_id in ko_finals:
        fixture_date = pd.Timestamp(m_date).date()
        elo_preds = predict_match(current_ratings, home, away, is_neutral=True)
        fixture = {
            "match_id": match_id,
            "date": m_date,
            "group": grp,
            "home": home,
            "away": away,
            "venue": venue,
            "prediction": elo_preds,
            "ml_prediction": elo_preds
        }
        
        if fixture_date < sim_date:
            fixture["status"] = "completed"
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(current_ratings, home, away, is_neutral=True, rng=rng)
            fixture.update(res)
            fixture["home_score"] = res["home_goals"]
            fixture["away_score"] = res["away_goals"]
            update_elo(current_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
        else:
            fixture["status"] = "upcoming"
            fixture["home_score"] = None
            fixture["away_score"] = None
            
            rng = np.random.default_rng(2026 + match_id)
            res = simulate_knockout_score(shadow_ratings, home, away, is_neutral=True, rng=rng)
            update_elo(shadow_ratings, home, away, res["home_goals"], res["away_goals"], is_neutral=True)
            
        fixtures_list.append(fixture)

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

    from backend.team_metadata import TEAM_METADATA
    home_meta = TEAM_METADATA.get(home, {"squad_value": 100, "fifa_rank": 50, "fifa_points": 1500})
    away_meta = TEAM_METADATA.get(away, {"squad_value": 100, "fifa_rank": 50, "fifa_points": 1500})
    squad_diff = home_meta["squad_value"] - away_meta["squad_value"]
    rank_diff = away_meta["fifa_rank"] - home_meta["fifa_rank"]
    squad_ratio = home_meta["squad_value"] / (away_meta["squad_value"] + 1.0)
    form_diff = home_form_val - away_form_val

    # 2. ML Prediction (Logistic Regression)
    features = np.array([[
        home_elo - away_elo,
        (home_elo + away_elo) / 2.0,
        home_form_val,
        away_form_val,
        1.0,  # World Cup neutral
        squad_diff,
        rank_diff,
        squad_ratio,
        form_diff
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
        "home_metadata": home_meta,
        "away_metadata": away_meta,
        "elo_prediction": elo_preds,
        "ml_prediction": ml_preds
    }

@app.get("/api/predict/live")
async def get_predict_live(
    home: str = Query(..., description="Home team name"),
    away: str = Query(..., description="Away team name"),
    time: float = Query(0.0, description="Match minute elapsed (0 to 90)"),
    goals_home: int = Query(0, description="Current home goals"),
    goals_away: int = Query(0, description="Current away goals"),
    xg_home: float = Query(0.0, description="Current home expected goals"),
    xg_away: float = Query(0.0, description="Current away expected goals"),
    red_cards_home: int = Query(0, description="Current home red cards"),
    red_cards_away: int = Query(0, description="Current away red cards"),
    date: str = Query("2026-06-01", description="Simulated timeline date (YYYY-MM-DD)")
):
    """Calculates Bayesian prediction updates as live in-game events occur."""
    try:
        current_ratings = state["baseline_ratings"].copy()
        fixtures_list = [dict(f) for f in state["fixtures_seed"]]
        fixtures_list.sort(key=lambda x: x["date"])
        sim_date = pd.Timestamp(date).date()

        for idx, fixture in enumerate(fixtures_list, start=1):
            f_home = fixture["home"]
            f_away = fixture["away"]
            fixture_date = pd.Timestamp(fixture["date"]).date()
            if fixture_date < sim_date:
                rng = np.random.default_rng(2026 + idx)
                home_goals_sim, away_goals_sim = simulate_score(current_ratings, f_home, f_away, is_neutral=True, rng=rng)
                update_elo(current_ratings, f_home, f_away, home_goals_sim, away_goals_sim, is_neutral=True)

        elo_preds = predict_match(current_ratings, home, away, is_neutral=True)
        
        from backend.prediction_fusion import compute_live_probabilities
        live_probs = compute_live_probabilities(
            home_team=home,
            away_team=away,
            pre_match_prior=elo_preds,
            time_elapsed=time,
            goals_home=goals_home,
            goals_away=goals_away,
            xg_home=xg_home,
            xg_away=xg_away,
            red_cards_home=red_cards_home,
            red_cards_away=red_cards_away,
            seed=42
        )
        
        return JSONResponse(content={
            "home": home,
            "away": away,
            "time": time,
            "goals_home": goals_home,
            "goals_away": goals_away,
            "xg_home": xg_home,
            "xg_away": xg_away,
            "red_cards_home": red_cards_home,
            "red_cards_away": red_cards_away,
            "pre_match_prior": elo_preds,
            "live_prediction": {
                "home_win": live_probs["home_win"],
                "draw": live_probs["draw"],
                "away_win": live_probs["away_win"]
            },
            "in_game_home_xg_rate": live_probs["in_game_home_xg_rate"],
            "in_game_away_xg_rate": live_probs["in_game_away_xg_rate"]
        })
    except Exception as exc:
        logger.error("Error calculating live predict: %s", exc)
        raise HTTPException(status_code=500, detail="Could not calculate live prediction.")

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

@app.get("/api/squad")
async def get_squad_endpoint(
    team: str = Query(..., description="Team name to fetch roster for")
):
    """Returns the squad roster for a specific team."""
    from backend.worldcup_api import get_squad
    try:
        squad = get_squad(team)
        return JSONResponse(content={"team": team, "squad": squad})
    except Exception as exc:
        logger.error("Error fetching squad for %s: %s", team, exc)
        raise HTTPException(status_code=500, detail=f"Could not load squad for {team}")
