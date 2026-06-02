# FIFA World Cup Analytics Suite

A prestigious, television-broadcast styled analytics and predictive dashboard for the FIFA World Cup. This application predicts match outcomes using a rolling Elo algorithm combined with a 9-feature Gradient Boosting Classifier, evaluates shot qualities using a three-level spatial Expected Goals (xG/xGOT) model trained on StatsBomb event data, simulates penalty shootouts using a kicker-GK Logistic Regression classifier with goalkeeper physics, and fuses match statistics in real-time using a conjugate Gamma-Poisson Bayesian update model.

The UI is built as a luxurious, responsive Single Page Application utilizing **Vite, React 18, TailwindCSS, Framer Motion, Recharts, and Lucide Icons**.

---

## Core Modules
1.  **Tournament Time Machine & Standings**: Syncs simulated dates via the FastAPI backend to dynamically recalculate group standings and upcoming match predictions as dates advance from June 11 to July 19, 2026.
2.  **Knockout Bracket Tree**: Simulates and visualizes the entire knockout stage (Round of 32 down to the Final) dynamically. Highlights winner paths on hover using animated Bezier curves. Supports extra-time and sudden-death penalty deciders.
3.  **Unified Power Ratings**: Blends historical rolling Elo with squad market valuations and official FIFA rankings to calculate boosted competitive ratings.
4.  **Match Predictor & Radar Compare**: Select any two teams to compare tactical attributes in an animated Radar chart, alongside comparative outcome probabilities and squad listings.
5.  **Multi-Source Roster Integration**: Fetches official team rosters using a fallback client wrapper connecting to WorldCupAPI, football-data.org, or balldontlie, with a local squad database fallback.
6.  **Expected Goals (xG/xGOT) Sandbox**: An isometric, 3D-shaded vector pitch coordinate plotter showing radial probability gauge output based on a spatial baseline, pre-shot XGBoost (360° freeze frames), and post-shot xGOT models.
7.  **Penalty Shootout Arena**: An interactive penalty game using zone selection, animated goalkeeper spring dive physics, a kicker-GK Logistic Regression model, a greedy kick-order optimizer, and a Monte Carlo heatmap.
8.  **Prediction Fusion Engine**: Uses a conjugate Gamma-Poisson Bayesian update to update ELO pre-match priors with in-game minutes, goals, red cards, and cumulative xG.
9.  **Intro Loader Opener**: A full-screen entrance animation featuring a custom WebGL shaded golden sphere loader synced with backend model initialization.

---

## Directory Structure

```
fifa/
├── backend/
│   ├── app.py                      # FastAPI server, endpoints & tournament simulator
│   ├── data_loader.py             # Downloads, normalises, and caches results
│   ├── elo.py                     # Elo calculations, Poisson ratings, and KO simulators
│   ├── team_metadata.py           # Squad values, FIFA ranks, and Unified Elo calculation
│   ├── worldcup_api.py            # External roster API client (3 endpoints fallback)
│   ├── model_match.py             # Gradient Boosting Classifier training pipeline
│   ├── model_xg.py                # xG/xGOT modeling pipeline (spatial, 360°, post-shot)
│   ├── model_shootout.py          # Kicker-GK Logistic Regression penalty shootout model
│   ├── prediction_fusion.py       # Bayesian Gamma-Poisson conjugate fusion engine
│   └── test_api.py                # TDD unit test suites 1-11
├── frontend/
│   ├── src/                       # React source files
│   │   ├── components/            # UI components (Sidebar, Pitch, Radar, Bracket, Loader)
│   │   │   ├── KnockoutBracket.jsx
│   │   │   ├── MatchPredictor.jsx
│   │   │   ├── OpenerLoader.jsx
│   │   │   ├── ShootoutArena.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── TimeMachine.jsx
│   │   │   ├── TournamentHub.jsx
│   │   │   └── XgSandbox.jsx
│   │   ├── App.jsx                # Layout orchestrator & live stats ticker
│   │   └── main.jsx               # React DOM entrypoint
│   ├── vite.config.js             # Vite configuration and API proxy
│   └── package.json               # Node packages
├── data/
│   ├── fixtures_2026.json         # 2026 World Cup Group schedules
│   ├── results.csv                # Cached historical matches
│   ├── shots_cache.csv            # Cached StatsBomb shot data
│   ├── model_match.pkl            # Serialized match outcome model
│   └── model_xg.pkl               # Serialized xG model
├── requirements.txt               # Python package dependencies
├── run.py                         # Launches backend server, builds frontend, trains models
├── PROGRESS.md                    # Detailed roadmap checklist
└── PRD.md                         # Product Requirements Document
```

---

## Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js (LTS version recommended)
*   Google Chrome or any modern web browser

### API Integration (Optional)
To enable live rosters and players from external sources, create a `.env` file in the root directory:
```env
WORLDCUP_API_KEY=your_worldcupapi_key_here
FOOTBALL_DATA_API_KEY=your_football_data_org_key_here
BALLDONTLIE_API_KEY=your_balldontlie_key_here
```
If no keys are provided, the application will automatically fall back to local mock squad data.

### Running the Suite
To automatically build the React assets, train the ML models, start the FastAPI server, and launch the web interface, run the orchestrator:
```bash
python run.py
```
This script will install Python dependencies, compile frontend packages, launch the FastAPI server, and open `http://127.0.0.1:8000/`.

### Running Verification Tests
To run the automated unit test suite and verify endpoints, standings, ELO boosts, best 3rd-places, knockout stages, and roster retrievals:
```bash
venv\Scripts\python -m backend.test_api
```
