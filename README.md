# FIFA World Cup Analytics Suite (React Redesign)

A premium, high-fidelity analytics and predictive dashboard for the FIFA World Cup. This application predicts match outcomes using a rolling Elo algorithm, evaluates shot qualities using an Expected Goals (xG) model trained on StatsBomb event data, and simulates penalty shootouts using a Monte Carlo simulator.

The UI is built as a luxurious, responsive Single Page Application utilizing **React, TailwindCSS, Framer Motion, and Recharts**. It is themed after standard sports television broadcasts, incorporating glassmorphic layers, dark mesh gradients, and interactive canvas components.

---

## Key Features
1.  **Tournament Time Machine & Standings**: Syncs simulated dates with background API fetches to dynamically recalculate group standings and upcoming match predictions.
2.  **Match Predictor & Radar Compare**: Select any two teams to compare attributes (Attack, Defense, Elo, Form, Prestige) in an animated Radar chart, alongside comparative outcome probabilities.
3.  **Expected Goals (xG) Sandbox**: An isometric, 3D-shaded SVG pitch coordinate plotter showing radial probability gauge output.
4.  **Penalty Shootout Arena**: An interactive penalty game utilizing goalkeeper Framer Motion dive physics and an empirical zone-based success heat map.

---

## Directory Structure

```
fifa/
├── backend/
│   ├── app.py                      # FastAPI server & route handlers
│   ├── data_loader.py             # Parses & caches results datasets
│   ├── elo.py                     # Rolling Elo rating engine
│   ├── model_match.py             # Match predictor ML model
│   ├── model_xg.py                # xG shot modeling pipeline
│   ├── model_shootout.py          # Penalty shootout simulator
│   └── test_api.py                # API handler unit test suite
├── frontend/
│   ├── src/                       # React source files
│   │   ├── components/            # UI components (Sidebar, Pitch, Radar)
│   │   ├── App.jsx                # Layout orchestrator
│   │   └── main.jsx               # React DOM entrypoint
│   ├── vite.config.js             # Vite configuration and API proxy
│   ├── tailwind.config.js         # Custom HSL variables & typography specs
│   └── package.json               # Node packages
├── data/
│   ├── fixtures_2026.json         # 2026 World Cup Group schedules
│   ├── results.csv                # Cached historical matches
│   ├── shots_cache.csv            # Cached StatsBomb shot data
│   ├── model_match.pkl            # Serialized match outcome model
│   └── model_xg.pkl               # Serialized xG model
├── requirements.txt               # Python package dependencies
├── run.py                         # Launches backend server and frontend builder
└── PROGRESS.md                    # Roadmap checklist
```

---

## Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js (LTS version recommended)
*   Google Chrome or any modern web browser

### Running the Suite
To automatically build the React assets, train the ML models, start the FastAPI server, and launch the web interface, run:
```bash
python run.py
```
This script will:
1.  Verify the Python virtual environment and install backend requirements.
2.  Trigger model training if pickled parameters are missing.
3.  Verify Node.js is installed, install frontend dependencies listed in `package.json`, and execute the production build (`npm run build`).
4.  Launch the FastAPI server (which serves the compiled static React assets from `frontend/dist`).
5.  Open your browser pointing to `http://127.0.0.1:8000/`.

---

## Frontend Development Mode
To edit the frontend with active Hot Module Replacement (HMR):
1.  Start the FastAPI backend:
    ```bash
    venv\Scripts\python.exe -m uvicorn backend.app:app --reload
    ```
2.  Launch the Vite dev server in another terminal:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
3.  Open the dev server URL (usually `http://localhost:5173`). All API calls will be automatically proxied to the backend at port `8000`.
