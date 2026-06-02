"""
prediction_fusion.py — Bayesian Prediction Fusion Engine

Computes live in-game match outcome probabilities (Home Win, Draw, Away Win)
by updating pre-match priors (from Dixon-Coles and ELO ratings) with in-game
performance metrics: time elapsed, goals scored, red cards, and cumulative expected goals (xG).
"""
import numpy as np
def compute_live_probabilities(
    home_team: str,
    away_team: str,
    pre_match_prior: dict,  # {"home_win": float, "draw": float, "away_win": float}
    time_elapsed: float,    # minute (0 to 90)
    goals_home: int,
    goals_away: int,
    xg_home: float,
    xg_away: float,
    red_cards_home: int = 0,
    red_cards_away: int = 0,
    n_simulations: int = 5000,
    seed: int | None = None
) -> dict:
    """Calculate dynamic win/draw/loss probabilities using a conjugate Gamma-Poisson Bayesian update.

    Parameters
    ----------
    home_team, away_team : str
        Team names.
    pre_match_prior : dict
        W/D/L probabilities from the pre-match ELO/ML classifiers.
    time_elapsed : float
        Elapsed match time in minutes (0 - 90).
    goals_home, goals_away : int
        Current in-game goals scored.
    xg_home, xg_away : float
        Cumulative expected goals generated up to time_elapsed.
    red_cards_home, red_cards_away : int
        Current red cards issued.
    n_simulations : int
        Number of Monte Carlo simulations to run for the remaining time.
    seed : int or None
        Random seed for reproducibility.

    Returns
    -------
    dict
        Updated probabilities: ``{"home_win": float, "draw": float, "away_win": float}``.
    """
    # 1. Edge Case: Full Time reached
    if time_elapsed >= 90.0:
        if goals_home > goals_away:
            return {"home_win": 1.0, "draw": 0.0, "away_win": 0.0}
        elif goals_home < goals_away:
            return {"home_win": 0.0, "draw": 0.0, "away_win": 1.0}
        else:
            return {"home_win": 0.0, "draw": 1.0, "away_win": 0.0}

    # 2. Establish Pre-Match expected goals (lambdas)
    # We can infer the pre-match expected goals using the priors.
    # Standard international match average goals = 2.6.
    # We approximate the prior attack rates from the prior win ratios.
    p_h = max(0.01, pre_match_prior.get("home_win", 0.40))
    p_a = max(0.01, pre_match_prior.get("away_win", 0.35))
    
    # Estimate lambda prior based on ELO-based strength ratios
    lambda_h_prior = 1.35 * (p_h / p_a) ** 0.5
    lambda_a_prior = 1.35 * (p_a / p_h) ** 0.5
    
    lambda_h_prior = min(max(lambda_h_prior, 0.2), 4.5)
    lambda_a_prior = min(max(lambda_a_prior, 0.2), 4.5)

    # 3. Bayesian Update using Gamma-Poisson Conjugacy
    # Time fraction of match completed
    t_frac = time_elapsed / 90.0
    t_rem = 1.0 - t_frac

    # Prior strength weight (weight equivalent to e.g. 1.5 full matches of evidence)
    prior_weight = 1.5

    # Posterior parameters for goals rate:
    # Prior: Gamma(alpha = lambda_prior * weight, beta = weight)
    # In-game observation: xG generated over t_frac time fraction
    # Posterior: Gamma(alpha + xG_observed, beta + t_frac)
    alpha_h = lambda_h_prior * prior_weight + xg_home
    beta_h = prior_weight + t_frac
    
    alpha_a = lambda_a_prior * prior_weight + xg_away
    beta_a = prior_weight + t_frac

    # Remaining goal-scoring rate parameters (posterior mean * remaining time fraction)
    lambda_h_rem = (alpha_h / beta_h) * t_rem
    lambda_a_rem = (alpha_a / beta_a) * t_rem

    # 4. Adjust for Red Cards (squad strength decay)
    # A red card reduces the team's remaining rate by 25% and boosts the opponent's by 15%
    if red_cards_home > 0:
        lambda_h_rem *= (0.75 ** red_cards_home)
        lambda_a_rem *= (1.15 ** red_cards_home)
    if red_cards_away > 0:
        lambda_a_rem *= (0.75 ** red_cards_away)
        lambda_h_rem *= (1.15 ** red_cards_away)

    # 5. Run Monte Carlo Simulation for the remaining time
    rng = np.random.default_rng(seed)
    goals_rem_h = rng.poisson(lambda_h_rem, size=n_simulations)
    goals_rem_a = rng.poisson(lambda_a_rem, size=n_simulations)

    final_h = goals_home + goals_rem_h
    final_a = goals_away + goals_rem_a

    h_wins = np.sum(final_h > final_a)
    draws = np.sum(final_h == final_a)
    a_wins = np.sum(final_h < final_a)

    return {
        "home_win": round(float(h_wins / n_simulations), 4),
        "draw": round(float(draws / n_simulations), 4),
        "away_win": round(float(a_wins / n_simulations), 4),
        "in_game_home_xg_rate": round(float(alpha_h / beta_h), 3),
        "in_game_away_xg_rate": round(float(alpha_a / beta_a), 3),
    }
