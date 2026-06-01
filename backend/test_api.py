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
    get_xg,
    get_shootout,
    get_shootout_montecarlo,
    get_index,
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
        
        print("\n[Test 6] Static file routing")
        idx_res = await get_index()
        print(f"  Root route index.html path: {idx_res.path}")
        assert "index.html" in str(idx_res.path), "Should route index.html"
        print("  [OK] Static files verified.")
        
    print("\nALL API ENDPOINTS VERIFIED AND WORKING SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
