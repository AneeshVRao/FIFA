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

### C. Expected Goals (xG & xGOT) Isometric Pitch Sandbox
*   **Isometric Pitch**: A styled, 3D-shaded isometric SVG pitch layout. Clicking on the pitch plots a glowing ball marker.
*   **Three-Level Modeling**:
    *   *Spatial Baseline*: Logistic Regression using shot coordinates, angle, and distance.
    *   *Pre-Shot Model*: 10-feature XGBoost incorporating StatsBomb 360° freeze-frame geometry (goalkeeper positioning, defender pressure, teammates count).
    *   *Post-Shot Model (xGOT)*: 4-feature XGBoost predicting goals after execution based on target placement and goalkeeper-to-placement distance.
*   **Dynamic xG Gauge**: Rendered in an animated radial wheel showing actual ML predictions.

### D. Penalty Shootout Arena
*   **Logistic Regression Classifier**: Calculates outcomes using a kicker-GK Logistic Regression model mapping the 9-zone goal matrix (TL, TC, TR, ML, MC, MR, BL, BC, BR) and keeper dive direction (L, C, R) combined with roster skill attributes.
*   **Greedy Kick-Order Optimizer**: Sorts and ranks squad roster players to place the highest-skilled takers in optimal pressure slots (Slots 1-5).
*   **Goalkeeper Stance & Dive Physics**: Goalkeeper is represented as an animated silhouette diving with realistic spring velocity curves.
*   **Monte Carlo Heat Map**: Runs 10,000 simulations using squad-specific kicker skills and GK save skills to generate conversion rate heatmaps.

### E. Prediction Fusion Engine
*   **Conjugate Bayesian In-game Updates**: As live incidents occur, the engine updates ELO priors using a conjugate Gamma-Poisson Bayesian update.
*   **In-game State Tracking**: Home and away win probabilities shift dynamically in real-time based on goals, elapsed time, red cards (squad fatigue/strength decay), and cumulative expected goals (xG).

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
