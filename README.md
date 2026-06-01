# FIFA World Cup Analytics Suite

A premium, unified predictive dashboard for the FIFA World Cup. This application predicts match outcomes using a rolling Elo algorithm, evaluates shot qualities using an Expected Goals (xG) model trained on StatsBomb event data, and simulates penalty shootouts using a Monte Carlo simulator.

The UI is built with a high-fidelity **FIFA World Cup theme** (maroon gradients, metallic gold accents, and pitch green graphics) under a clean Glassmorphism design system.

---

## Key Features

1. **Match Predictor & Tournament Time Machine**:
   * Auto-tracks the 2026 fixtures (starting with the opening match, **Mexico vs. South Africa** on June 11, 2026).
   * A simulated date slider advances tournament time. As matches are completed, they are marked as **done** with simulated scorelines.
   * Ratings and upcoming forecasts are recalculated in a rolling feedback loop.
2. **Expected Goals (xG) Sandbox**:
   * Click-to-plot shot locator on an interactive SVG pitch.
   * Adjust shot type (foot/head) and pressure to calculate goal probabilities dynamically.
3. **Penalty Shootout Simulator**:
   * An interactive goal post grid where players select kicker targets and goalkeeper dive directions to run Monte Carlo simulations.

---

## Directory Structure

```
fifa/
├── backend/
│   ├── app.py                      # FastAPI API endpoints
│   ├── model_match.py             # Match predictor and Elo updates
│   ├── model_xg.py                # xG shot modeling
│   └── model_shootout.py          # Penalty shootout calculator
├── frontend/
│   ├── index.html                 # Main website template
│   ├── style.css                  # Custom World Cup themed styling
│   └── app.js                     # UI interactions & SVG rendering
├── data/
│   └── fixtures_2026.json         # 2026 World Cup Group A fixtures
├── PRD.md                         # Product Requirements Document
├── PROGRESS.md                    # Project checklist and timeline
├── run.py                         # Launches backend server and frontend UI
└── requirements.txt               # Python package requirements
```

---

## Getting Started

### Prerequisites
* Python 3.10+
* Google Chrome or any modern web browser

### Running the Suite
To set up the environment, download datasets, train the models, and launch the web server and UI, run:
```bash
python run.py
```
This script will:
1. Initialize a Python virtual environment.
2. Install dependencies listed in `requirements.txt`.
3. Feed the baseline historical dataset and StatsBomb event data to train the models.
4. Launch the FastAPI server.
5. Open your default web browser to the World Cup Analytics Suite dashboard.
