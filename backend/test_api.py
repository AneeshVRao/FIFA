"""
test_api.py — Backend API Verification Script

Directly tests the FastAPI endpoint handlers using the application lifespan
to ensure all models, standings calculations, predictions, xG outputs,
and penalty shootout simulations are correct.
"""

import asyncio
import logging
from backend.app import (
    app,
    lifespan,
    get_fixtures,
    get_predict,
    get_predict_live,
    get_xg,
    get_shootout,
    get_shootout_montecarlo,
    get_index,
    get_squad_endpoint,
    get_transfermarkt_stats,
    get_tactics_matchup,
    get_xt_heatmap,
    get_xp,
    get_similar_players,
)

logging.basicConfig(level=logging.WARNING)

async def run_tests():
    print("== Running API Verification Tests ==")
    
    async with lifespan(app):
        print("\n[Test 1] /api/fixtures (Tournament State at June 12, 2026)")
        # Call the endpoint handler
        response = await get_fixtures(date="2026-06-12")
        data = response.body.decode("utf-8")
        import json
        res_json = json.loads(data)
        
        # Verify simulated fixtures
        fixtures = res_json["fixtures"]
        completed = [f for f in fixtures if f["status"] == "completed"]
        upcoming = [f for f in fixtures if f["status"] == "upcoming"]
        
        print(f"  Total Fixtures: {len(fixtures)}")
        print(f"  Completed:      {len(completed)}")
        print(f"  Upcoming:       {len(upcoming)}")
        
        # We expect matches scheduled before June 12 to be completed.
        # Group A matches on June 11: Mexico vs South Africa, South Korea vs Czech Republic.
        # So we expect at least 2 completed matches.
        assert len(completed) >= 2, "Should have at least 2 completed matches by June 12"
        print("  [OK] Completed matches count is correct.")
        
        # Verify standings for Group A
        standings_a = res_json["standings"]["A"]
        print("  Group A Standings:")
        for team_stat in standings_a:
            print(f"    - {team_stat['team']}: Pts={team_stat['Pts']}, P={team_stat['P']}, GF={team_stat['GF']}, GD={team_stat['GD']}")
            
        assert len(standings_a) == 4, "Group A should have exactly 4 teams"
        print("  [OK] Group standings generated successfully.")
        
        print("\n[Test 2] /api/predict (Match outcome prediction)")
        # Test predict endpoint
        predict_res = await get_predict(home="Spain", away="Germany", date="2026-06-12")
        print(f"  Spain vs Germany Predict Result: {predict_res}")
        assert "elo_prediction" in predict_res, "Should contain Elo prediction keys"
        assert "ml_prediction" in predict_res, "Should contain ML prediction keys"
        print("  [OK] Match outcome prediction working.")
        
        print("\n[Test 3] /api/xg (Expected goals prediction)")
        # Test xG endpoint
        xg_res = await get_xg(x=108.0, y=40.0, is_header=False, under_pressure=False)
        print(f"  Penalty spot xG: {xg_res}")
        assert xg_res["xg"] == 0.76, "Penalty spot override should equal 0.76"
        
        xg_res_wide = await get_xg(x=90.0, y=10.0, is_header=False, under_pressure=True)
        print(f"  25y out wide under pressure xG: {xg_res_wide}")
        assert xg_res_wide["xg"] < 0.1, "Off-centre long-range pressured shot should have low xG"
        print("  [OK] Expected goals (xG) endpoints validated.")
        
        print("\n[Test 4] /api/shootout (Single-kick penalty simulation)")
        response_shootout = await get_shootout(kicker_zone="TL", keeper_dive="L")
        data_shootout = json.loads(response_shootout.body.decode("utf-8"))
        print(f"  Kicked TL, Keeper L result: {data_shootout}")
        assert "scored" in data_shootout, "Should return scored flag"
        print("  [OK] Single kick penalty simulation working.")
        
        print("\n[Test 5] /api/shootout/montecarlo (Shootout batch simulation)")
        response_mc = await get_shootout_montecarlo(simulations=500)
        data_mc = json.loads(response_mc.body.decode("utf-8"))
        print(f"  Monte Carlo (500 runs) win rate Team A: {data_mc['team_a_win_rate']}")
        assert 0.4 <= data_mc["team_a_win_rate"] <= 0.6, "Team A win rate should be around 50%"
        print("  [OK] Monte Carlo simulation validated.")
        
        print("\n[Test 7] Unified Elo Rating Boost")
        # Try to import team_metadata (will fail initially in RED phase)
        from backend.team_metadata import get_unified_elo, TEAM_METADATA
        england_meta = TEAM_METADATA["England"]
        print(f"  England metadata: {england_meta}")
        england_unified = get_unified_elo("England", 1838.5)
        print(f"  England Unified Elo: {england_unified}")
        # Expected boost: 0.1 * (1795 - 1500) + 0.05 * 1300 = 29.5 + 65.0 = 94.5. 1838.5 + 94.5 = 1933.0
        assert england_unified == 1933.0, "England Unified Elo should be exactly 1933.0"
        print("  [OK] Unified Elo rating calculations verified.")

        print("\n[Test 8] Best 3rd-place Selection & Knockout Generation")
        response_ko = await get_fixtures(date="2026-06-29")
        data_ko = json.loads(response_ko.body.decode("utf-8"))
        fixtures_ko = data_ko["fixtures"]
        
        # Round of 32 matches are scheduled from June 28 onwards
        r32_matches = [f for f in fixtures_ko if f.get("group") == "Round of 32"]
        print(f"  Total Round of 32 Matches: {len(r32_matches)}")
        assert len(r32_matches) == 16, "Should generate exactly 16 Round of 32 matches after group stage"
        
        # Verify that England is in the Round of 32 (Unified Elo should qualify them)
        england_r32 = [f for f in r32_matches if f["home"] == "England" or f["away"] == "England"]
        assert len(england_r32) > 0, "England should qualify for the Round of 32"
        print("  [OK] Best 3rd-place teams selected and Round of 32 matchups seeded successfully.")

        print("\n[Test 9] Knockout Match Extra Time & Penalties")
        response_final = await get_fixtures(date="2026-07-20")
        data_final = json.loads(response_final.body.decode("utf-8"))
        fixtures_final = data_final["fixtures"]
        
        # Verify knockout fixtures are simulated (completed) and have a winner
        knockout_groups = ["Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "3rd Place Match", "Final"]
        ko_fixtures = [f for f in fixtures_final if f.get("group") in knockout_groups]
        completed_ko = [f for f in ko_fixtures if f["status"] == "completed"]
        
        print(f"  Total Knockout matches simulated: {len(completed_ko)}")
        assert len(completed_ko) == 32, "Should simulate exactly 32 knockout matches by end of tournament"
        
        # Check that every completed knockout match has a winner and no draws
        for match in completed_ko:
            assert match.get("winner") is not None, f"Knockout Match {match['match_id']} must have a winner"
            if match.get("home_score") == match.get("away_score"):
                assert match.get("extra_time") is True or match.get("penalties") is True, "Tied matches must go to extra time/penalties"
                if match.get("penalties") is True:
                    assert "penalty_scores" in match, "Penalty shootout details must be recorded"
        print("  [OK] Knockout extra time and penalty deciders simulated and validated.")

        print("\n[Test 6] Static file routing")
        import os
        from pathlib import Path
        dist_dir = Path("frontend/dist")
        index_file = dist_dir / "index.html"
        created_mock = False
        if not index_file.exists():
            dist_dir.mkdir(parents=True, exist_ok=True)
            index_file.write_text("Mock index.html", encoding="utf-8")
            created_mock = True

        try:
            idx_res = await get_index()
            print(f"  Root route index.html path: {idx_res.path}")
            assert "index.html" in str(idx_res.path), "Should route index.html"
            print("  [OK] Static files verified.")
        finally:
            if created_mock:
                try:
                    index_file.unlink()
                    if dist_dir.exists() and not any(dist_dir.iterdir()):
                        dist_dir.rmdir()
                except Exception:
                    pass

        print("\n[Test 10] /api/squad (Team roster endpoint)")
        squad_response = await get_squad_endpoint(team="England")
        squad_data = json.loads(squad_response.body.decode("utf-8"))
        print(f"  England Roster Size: {len(squad_data['squad'])}")
        assert len(squad_data["squad"]) > 0, "Squad roster should not be empty"
        assert any(p["name"] == "Harry Kane" for p in squad_data["squad"]), "Harry Kane should be in England squad"
        print("  [OK] Roster endpoint verified.")
        
        print("\n[Test 11] /api/predict/live (Bayesian Prediction Fusion Engine)")
        # Spain vs Germany at minute 60, Spain leading 1-0 with 1.5 xG vs Germany's 0.4 xG
        response_live = await get_predict_live(
            home="Spain", away="Germany", time=60.0,
            goals_home=1, goals_away=0,
            xg_home=1.5, xg_away=0.4,
            red_cards_home=0, red_cards_away=0,
            date="2026-06-12"
        )
        data_live = json.loads(response_live.body.decode("utf-8"))
        print(f"  Live prediction at min 60 (Spain 1 - 0 Germany): {data_live['live_prediction']}")
        assert data_live["live_prediction"]["home_win"] > 0.70, "Spain should have a high win probability"
        
        # Germany gets a red card
        response_live_red = await get_predict_live(
            home="Spain", away="Germany", time=60.0,
            goals_home=1, goals_away=0,
            xg_home=1.5, xg_away=0.4,
            red_cards_home=0, red_cards_away=1,
            date="2026-06-12"
        )
        data_live_red = json.loads(response_live_red.body.decode("utf-8"))
        print(f"  Live prediction (Germany Red Card): {data_live_red['live_prediction']}")
        assert data_live_red["live_prediction"]["home_win"] > data_live["live_prediction"]["home_win"], "Spain win probability should increase after Germany red card"
        print("  [OK] Live Bayesian prediction updates verified.")
        
        print("\n[Test 12] /api/stats/transfermarkt (Scraped Statistics)")
        response_stats = await get_transfermarkt_stats(category="premier_league_top_goalscorers")
        data_stats = json.loads(response_stats.body.decode("utf-8"))
        print(f"  Scraped stat count: {len(data_stats['data'])}")
        assert len(data_stats["data"]) > 0, "Scraped statistical records list should not be empty"
        assert any(p.get("player") == "Erling Haaland" for p in data_stats["data"]), "Haaland should be in the top scorers list"
        print("  [OK] Transfermarkt stats endpoint verified.")
        
        print("\n[Test 13] /api/tactics/matchup (Playstyle Embeddings)")
        response_tactics = await get_tactics_matchup(home="Spain", away="Germany")
        data_tactics = json.loads(response_tactics.body.decode("utf-8"))
        print(f"  Spain tactic vector length: {len(data_tactics['home_vector'])}")
        print(f"  Closest analogue match similarity: {data_tactics['analogues'][0]['similarity']:.3f}")
        assert len(data_tactics["home_vector"]) == 10, "Tactic profile embedding must be 10D"
        assert len(data_tactics["analogues"]) == 5, "Must return exactly 5 closest analogues"
        print("  [OK] Tactics engine matchup endpoint verified.")

        print("\n[Test 14] /api/xt/heatmap (Expected Threat Heatmap)")
        response_xt = await get_xt_heatmap()
        data_xt = json.loads(response_xt.body.decode("utf-8"))
        print(f"  xT Heatmap Shape: {len(data_xt['heatmap'])}x{len(data_xt['heatmap'][0])}")
        assert len(data_xt["heatmap"]) == 12, "xT heatmap should have 12 rows"
        assert len(data_xt["heatmap"][0]) == 8, "xT heatmap should have 8 columns"
        print("  [OK] Expected Threat heatmap verified.")

        print("\n[Test 15] /api/xp (Pass Completion Probability)")
        response_xp = await get_xp(x_start=50, y_start=40, x_end=70, y_end=50, is_header=0, under_pressure=0)
        data_xp = json.loads(response_xp.body.decode("utf-8"))
        print(f"  Pass Completion Probability: {data_xp['probability']:.4f}")
        assert 0.0 <= data_xp["probability"] <= 1.0, "Probability must be between 0.0 and 1.0"
        print("  [OK] Pass completion probability verified.")

        print("\n[Test 16] /api/players/similar (Player Similarity Finder)")
        response_sim = await get_similar_players(player="Jude Bellingham", position="MF")
        data_sim = json.loads(response_sim.body.decode("utf-8"))
        print(f"  Bellingham Similar Players: {[p['name'] for p in data_sim['similar']]}")
        assert len(data_sim["similar"]) == 5, "Should return exactly 5 similar players"
        assert data_sim["similar"][0]["similarity"] >= 0.90, "Top similarity should be high"
        print("  [OK] Player similarity recruiter verified.")
        
    print("\nALL API ENDPOINTS VERIFIED AND WORKING SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
