# Project Progress: FIFA World Cup Analytics Suite

This document tracks the current state of implementation for the FIFA World Cup Analytics Suite.

---

## Roadmap & Checklist

- [x] **Phase 1: Project Setup & Dependencies**
  - [x] Initialize Python Virtual Environment.
  - [x] Write `requirements.txt` containing `fastapi`, `uvicorn`, `pandas`, `numpy`, `scikit-learn`, `statsbombpy`, `requests`.
  - [x] Configure `run.py` launch orchestrator script.

- [x] **Phase 2: Data Pipeline & Model Training**
  - [x] Implement historical results caching parser (`data_loader.py` — downloads and caches `results.csv`, normalises team names).
  - [x] Build baseline Elo calculation pipeline (`elo.py` — rolling Elo with Poisson prediction and score simulation).
  - [x] Write Match Outcome Predictor training pipeline (`model_match.py` — LogisticRegression, 52.3% 3-class accuracy).
  - [x] Fetch StatsBomb open shot-event data and train xG model (`model_xg.py` — 5-fold Stratified CV ROC-AUC: 0.792).
  - [x] Implement Shootout simulator logic (`model_shootout.py` — 9-zone Monte Carlo, verified 50/50 split).

- [ ] **Phase 3: Backend API Server**
  - [ ] Setup FastAPI server in `app.py`.
  - [ ] Implement `/api/fixtures` with sequential rolling Elo updater.
  - [ ] Implement `/api/predict` for match outcome forecasts.
  - [ ] Implement `/api/xg` shot calculations.
  - [ ] Implement `/api/shootout` Monte Carlo simulations.

- [ ] **Phase 4: Frontend Development (Single Page Website)**
  - [ ] Create HTML structure (`index.html`) using semantic tags.
  - [ ] Style the dashboard (`style.css`) using custom HSL World Cup theme (maroon/gold glassmorphism).
  - [ ] Implement JS interactions (`app.js`):
    - [ ] Tab switching with fade transitions.
    - [ ] SVG Soccer Pitch click-to-plot shot locator.
    - [ ] SVG Penalty Shootout Goal Target grid.
    - [ ] Timeline slider synced with `/api/fixtures`.

- [ ] **Phase 5: Verification & Launch**
  - [ ] Perform API endpoint unit testing.
  - [ ] Conduct visual manual check of the date slider (verifying the opening match Mexico vs. South Africa updates to completed and standings adjust).
  - [ ] Perform validation of calculated values (e.g. penalty spot xG ≈ 0.75).
