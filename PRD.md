# Product Requirements Document (PRD): FIFA World Cup Predictive Analytics Suite

## 1. Product Overview & Goals
The **FIFA World Cup Analytics Suite** is an elite, high-fidelity sports analytics and simulation dashboard. The system integrates predictive machine learning models, physics-based shootout simulations, and real-time tournament timeline tracking. 

The suite is wrapped in a prestigious **World Cup Television-Broadcast Theme** resembling a live sports console (deep burgundy-midnight mesh gradients, glowing gold elements, and modern typography).

---

## 2. Core Functional Requirements

### A. The Tournament Hub & Time Machine Slider
*   **Data Seed**: The system loads the official 2026 World Cup Group stage fixtures.
*   **Tournament Time Machine**: A timeline slider allows the user to simulate advancing the tournament date (from June 11th to July 19th, 2026).
*   **Rolling Elo Recalculation**:
    *   Completed matches display simulated scorelines generated dynamically by our models.
    *   Standings tables and team ratings are updated in real-time based on completed scores.
*   **Knockout Brackets**:
    *   Once all Group Stage fixtures are completed (after June 27th), the engine automatically determines final group standings and the 8 best 3rd-place teams.
    *   The engine dynamically builds the **Round of 32** pairings.
    *   As the time machine advances, subsequent rounds (**Round of 16**, **Quarterfinals**, **Semifinals**, **3rd-Place**, and **Final**) are simulated and updated.
    *   Knockout matches cannot end in draws; ties trigger simulated Extra Time (30 mins) and, if needed, Penalty Shootouts.

### B. Match Predictor & Team Radar Compare
*   **Side-by-Side Analysis**: Select any two teams to compare Elo ratings, form, squad values, and FIFA ranking details.
*   **Radar Charting**: Displays a comparative radar chart showing team metrics (Attack, Defense, Elo, Form, Prestige) with custom glassmorphic styling.
*   **Double Predictor Comparison**: Shows probability outputs from both the baseline Elo Poisson engine and the Gradient Boosting Classifier (9-feature ML model) using animated progress indicators.
*   **Squad Rosters**: Displays active player rosters (loaded from WorldCupAPI, football-data.org, or balldontlie API client fallbacks) for selected teams.

### C. Expected Goals (xG) Isometric Pitch Sandbox
*   **Isometric Pitch**: A styled, 3D-shaded isometric SVG pitch layout. Clicking on the pitch plots a glowing ball marker.
*   **Dynamic xG Gauge**: Adjust shot variables (Foot/Head, Under Pressure) to compute the goal probability using a Logistic Regression model, rendered in an animated radial wheel.

### D. Penalty Shootout Arena
*   **Granular Kick Modeling**: Calculates outcomes using a 3x3 goal zone matrix (TL, TC, TR, ML, MC, MR, BL, BC, BR) combined with goalkeeper dive directions (L, C, R).
*   **Goalkeeper Stance & Dive Physics**: Goalkeeper is represented as an animated silhouette diving with realistic spring velocity curves.
*   **Outcome Indicators**: Target zones glow green (Goal) or red (Save) with particle emission feedback.
*   **Monte Carlo Heat Map**: Displays a heat map overlay of the goal grid, showing save/goal success rates per zone based on 10,000 simulations.

### E. Prediction Fusion Engine
*   **Prior Probabilities**: Pre-match model outputs establish the prior state.
*   **Bayesian Updates**: As shots occur, the fusion engine updates live win/draw/loss probabilities, shifting the posterior with each shot's xG value alongside key match event logs (goals, cards, elapsed time).

---

## 3. Premium Visual & UX Standards

### A. Opener Intro Loader
*   A full-screen, high-end introductory loader that plays when first visiting the site.
*   Features a WebGL custom-shaded rotating gold soccer ball representing the trophy/theme.
*   Incorporates progress-bar metrics reflecting actual database/model load percentages and fades out smoothly via Framer Motion.

### B. High-End Visual Layout
*   **Background**: Radial-linear mesh gradient blending deep burgundy (`#120108`), midnight slate (`#050818`), and ambient gold spot lights.
*   **Colors**:
    *   *Team A Accent*: Teal Green (`#0D9488`)
    *   *Team B Accent*: Coral Red (`#F43F5E`)
    *   *Goals/Championship Accent*: Championship Gold (`#EAB308`)
    *   *Neutral/Draw Accent*: Slate/Gray (`#64748B`)
*   **Typography**: Montserrat (body elements) and Outfit (headers, titles) with Orbitron for scores and monospace for xG values.
*   **National Badges**: Circular gold-framed text abbreviation badges next to all team names.
*   **Glassmorphism**: High-blur background cards (`backdrop-blur-xl bg-white/5 border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`).
*   **Interactive Focus**: Features tactile scaling on button press (`active:scale-[0.98] transition-all`) and mouse-hover glare highlights.

---

## 4. Technology Stack

### Backend (Python API)
*   **Framework**: FastAPI.
*   **Libraries**: `pandas`, `numpy`, `scikit-learn` (Gradient Boosting Classifier, Logistic Regression), `joblib`, `requests`.
*   **APIs**: Ingests rosters from WorldCupAPI, football-data.org, or balldontlie.

### Frontend (React SPA)
*   **Framework**: Vite (React 18 + JavaScript).
*   **Styling**: TailwindCSS & Custom CSS.
*   **Animations**: Framer Motion (goalkeeper spring physics).
*   **Charts**: Recharts (radar charts, radial progress gauges).
*   **Icons**: Lucide Icons.
