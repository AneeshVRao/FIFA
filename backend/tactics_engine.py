"""
tactics_engine.py — Tactical Profile Embedding and Opponent Matching Engine

Calculates 10-dimensional tactical embeddings for teams and searches for historical
match analogues using pgvector (PostgreSQL) or a NumPy-based cosine similarity fallback.
"""

import os
import logging
import numpy as np
from sqlalchemy import create_engine, text
from backend.team_metadata import TEAM_METADATA, get_unified_elo

logger = logging.getLogger(__name__)

# Base database URL, default to empty to trigger NumPy fallback
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# 10D Tactical Dimensions:
# 0: Pressing Intensity (PPDA, 0-1)
# 1: Defensive Block Depth (Deep block vs High line, 0-1)
# 2: Possession Rate (0-1)
# 3: Directness of Play (Short passing vs Long balls, 0-1)
# 4: Squad Market Value (Log-normalized, 0-1)
# 5: Average Age (Normalized, 0-1)
# 6: Attacking Strength (Dixon-Coles Lambda approximation, 0-1)
# 7: Defensive Strength (Dixon-Coles Mu approximation, 0-1)
# 8: Crossing Density (0-1)
# 9: Counter-Attack Transition Speed (0-1)

def get_team_tactic_vector(team_name: str) -> np.ndarray:
    """Generate a reproducible, logically sound 10D tactical embedding vector for a team."""
    # Seed based on team name to ensure consistent random parameters for less prominent teams
    h = hash(team_name)
    rng = np.random.default_rng(abs(h) % 10000)
    
    # Base values derived from ELO / Squad Val / FIFA Rankings
    meta = TEAM_METADATA.get(team_name, {"squad_value": 80.0, "fifa_rank": 50})
    squad_val = meta["squad_value"]
    fifa_rank = meta["fifa_rank"]
    
    # 1. Normalize Value (log scale)
    val_norm = min(max(np.log10(squad_val + 1.0) / 3.2, 0.1), 0.99)
    
    # 2. Attacking & Defensive Strength
    unified_elo = get_unified_elo(team_name, 1500.0)
    strength = min(max((unified_elo - 1200.0) / 700.0, 0.1), 0.99)
    
    # Custom tactical signatures for top international teams
    # 0: Pressing, 1: Depth, 2: Possession, 3: Directness, 4: Value, 5: Age, 6: Att, 7: Def, 8: Cross, 9: Transition
    profiles = {
        "Spain": [0.85, 0.30, 0.92, 0.15, val_norm, 0.48, strength + 0.1, strength + 0.05, 0.40, 0.65],
        "Germany": [0.88, 0.35, 0.80, 0.25, val_norm, 0.52, strength + 0.08, strength, 0.45, 0.82],
        "Argentina": [0.78, 0.45, 0.72, 0.20, val_norm, 0.68, strength + 0.12, strength + 0.1, 0.35, 0.75],
        "England": [0.65, 0.48, 0.68, 0.30, val_norm, 0.50, strength + 0.05, strength + 0.08, 0.55, 0.68],
        "France": [0.60, 0.55, 0.62, 0.35, val_norm, 0.54, strength + 0.1, strength + 0.12, 0.50, 0.92],
        "Brazil": [0.72, 0.40, 0.75, 0.22, val_norm, 0.58, strength + 0.08, strength + 0.05, 0.38, 0.85],
        "Netherlands": [0.74, 0.42, 0.70, 0.32, val_norm, 0.51, strength + 0.02, strength + 0.02, 0.60, 0.76],
        "Italy": [0.68, 0.65, 0.58, 0.28, val_norm, 0.60, strength - 0.02, strength + 0.1, 0.42, 0.70],
        "Morocco": [0.82, 0.78, 0.42, 0.48, val_norm, 0.56, strength - 0.05, strength + 0.12, 0.38, 0.80],
        "Japan": [0.85, 0.50, 0.55, 0.30, val_norm, 0.46, strength, strength, 0.32, 0.90],
        "Croatia": [0.55, 0.58, 0.65, 0.25, val_norm, 0.72, strength - 0.02, strength + 0.08, 0.44, 0.58],
        "Switzerland": [0.62, 0.70, 0.48, 0.45, val_norm, 0.64, strength - 0.04, strength + 0.05, 0.50, 0.74],
    }
    
    if team_name in profiles:
        return np.array(profiles[team_name], dtype=float)
        
    # Generate structured random vector for other teams
    pressing = rng.uniform(0.4, 0.8)
    depth = rng.uniform(0.4, 0.8)
    possession = rng.uniform(0.35, 0.65)
    directness = rng.uniform(0.3, 0.7)
    age = rng.uniform(0.4, 0.7)
    crossing = rng.uniform(0.3, 0.7)
    transition = rng.uniform(0.5, 0.85)
    
    return np.array([
        pressing,
        depth,
        possession,
        directness,
        val_norm,
        age,
        strength,
        strength,
        crossing,
        transition
    ], dtype=float)

# List of classic historical matches representing matchup analogue seeds
HISTORICAL_ANALOGUES = [
    {"home": "Spain", "away": "Netherlands", "score": "1-0 (ET)", "tournament": "World Cup 2010 Final", "date": "2010-07-11"},
    {"home": "Germany", "away": "Brazil", "score": "7-1", "tournament": "World Cup 2014 Semifinal", "date": "2014-07-08"},
    {"home": "Argentina", "away": "France", "score": "3-3 (4-2 pens)", "tournament": "World Cup 2022 Final", "date": "2022-12-18"},
    {"home": "Spain", "away": "Switzerland", "score": "0-1", "tournament": "World Cup 2010 Group Stage", "date": "2010-06-16"},
    {"home": "England", "away": "Italy", "score": "1-1 (2-3 pens)", "tournament": "Euro 2020 Final", "date": "2021-07-11"},
    {"home": "France", "away": "Croatia", "score": "4-2", "tournament": "World Cup 2018 Final", "date": "2018-07-15"},
    {"home": "Belgium", "away": "Japan", "score": "3-2", "tournament": "World Cup 2018 Round of 16", "date": "2018-07-02"},
    {"home": "Morocco", "away": "Portugal", "score": "1-0", "tournament": "World Cup 2022 Quarterfinal", "date": "2022-12-10"},
    {"home": "Brazil", "away": "Germany", "score": "2-0", "tournament": "World Cup 2002 Final", "date": "2002-06-30"},
    {"home": "Argentina", "away": "Netherlands", "score": "2-2 (4-3 pens)", "tournament": "World Cup 2022 Quarterfinal", "date": "2022-12-09"},
    {"home": "England", "away": "Germany", "score": "2-0", "tournament": "Euro 2020 Round of 16", "date": "2021-06-29"},
    {"home": "France", "away": "Argentina", "score": "4-3", "tournament": "World Cup 2018 Round of 16", "date": "2018-06-30"}
]

def search_analogues_numpy(vec_h: np.ndarray, vec_a: np.ndarray) -> list[dict]:
    """Fallback search using NumPy cosine similarity over seed matches."""
    input_matchup_vec = np.concatenate([vec_h, vec_a]) # 20D Vector
    
    results = []
    for match in HISTORICAL_ANALOGUES:
        m_h_vec = get_team_tactic_vector(match["home"])
        m_a_vec = get_team_tactic_vector(match["away"])
        
        # 1. Option A matchup alignment
        matchup_vec_1 = np.concatenate([m_h_vec, m_a_vec])
        # 2. Option B matchup alignment (flipped order comparison)
        matchup_vec_2 = np.concatenate([m_a_vec, m_h_vec])
        
        # Calculate cosine similarities
        sim1 = np.dot(input_matchup_vec, matchup_vec_1) / (np.linalg.norm(input_matchup_vec) * np.linalg.norm(matchup_vec_1))
        sim2 = np.dot(input_matchup_vec, matchup_vec_2) / (np.linalg.norm(input_matchup_vec) * np.linalg.norm(matchup_vec_2))
        
        # We take the max similarity score (aligned matchup or flipped matchup analogue)
        best_sim = max(sim1, sim2)
        
        results.append({
            "home": match["home"],
            "away": match["away"],
            "score": match["score"],
            "tournament": match["tournament"],
            "date": match["date"],
            "similarity": float(best_sim)
        })
        
    # Sort by similarity descending
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:5]

def setup_postgres_vector_db():
    """Initializes the database and seeds historical matches if pgvector is active."""
    if not DATABASE_URL:
        return None
        
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # 1. Enable extension pgvector if not exists
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # 2. Create matchups table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS historical_matchups (
                    id SERIAL PRIMARY KEY,
                    home_team VARCHAR(100),
                    away_team VARCHAR(100),
                    score VARCHAR(50),
                    tournament VARCHAR(100),
                    match_date VARCHAR(50),
                    matchup_vector vector(20)
                );
            """))
            
            # 3. Check if table is empty, if so, seed
            res = conn.execute(text("SELECT COUNT(*) FROM historical_matchups;")).fetchone()
            if res[0] == 0:
                logger.info("Seeding pgvector historical matchups table...")
                for match in HISTORICAL_ANALOGUES:
                    m_h_vec = get_team_tactic_vector(match["home"])
                    m_a_vec = get_team_tactic_vector(match["away"])
                    vec = np.concatenate([m_h_vec, m_a_vec]).tolist()
                    
                    conn.execute(
                        text("""
                            INSERT INTO historical_matchups (home_team, away_team, score, tournament, match_date, matchup_vector)
                            VALUES (:home, :away, :score, :tourney, :m_date, :vec);
                        """),
                        {
                            "home": match["home"],
                            "away": match["away"],
                            "score": match["score"],
                            "tourney": match["tournament"],
                            "m_date": match["date"],
                            "vec": str(vec) # vector type accepts string format '[x1,x2,...]'
                        }
                    )
            conn.commit()
            return engine
    except Exception as e:
        logger.error("Failed to setup PostgreSQL pgvector DB: %s. Falling back to NumPy.", e)
        return None

# Perform Setup on load
db_engine = setup_postgres_vector_db()

def search_analogues(home_team: str, away_team: str) -> list[dict]:
    """Queries closest matchups from pgvector DB, falling back to NumPy matrix operations if needed."""
    vec_h = get_team_tactic_vector(home_team)
    vec_a = get_team_tactic_vector(away_team)
    
    if not DATABASE_URL or db_engine is None:
        return search_analogues_numpy(vec_h, vec_a)
        
    try:
        input_vector = np.concatenate([vec_h, vec_a]).tolist()
        
        # We query using the cosine distance operator <=> (or L2 distance <->)
        with db_engine.connect() as conn:
            query = text("""
                SELECT home_team, away_team, score, tournament, match_date,
                       (1 - (matchup_vector <=> :input_vec)) AS similarity
                FROM historical_matchups
                ORDER BY matchup_vector <=> :input_vec
                LIMIT 5;
            """)
            rows = conn.execute(query, {"input_vec": str(input_vector)}).fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "home": row[0],
                    "away": row[1],
                    "score": row[2],
                    "tournament": row[3],
                    "date": row[4],
                    "similarity": float(row[5])
                })
            return results
    except Exception as e:
        logger.error("Error executing pgvector query: %s. Falling back to NumPy.", e)
        return search_analogues_numpy(vec_h, vec_a)
