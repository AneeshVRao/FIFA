# Product Requirements Document (PRD): FIFA World Cup Analytics Suite (React Redesign)

## 1. Product Overview & Goals
The **FIFA World Cup Analytics Suite** is an interactive, premium web dashboard that integrates three distinct machine learning predictions and sports analytics tools:
1.  **Match Outcome Predictor**: Calculates outcome probabilities (Win/Draw/Loss) for any international matchup, rendering side-by-side comparative forecasts and a team attribute radar chart.
2.  **Expected Goals (xG) Model**: Evaluates shot quality dynamically based on coordinates on an interactive, isometric 3D-shaded SVG pitch, rendering outputs in a radial gauge.
3.  **Penalty Shootout Predictor**: Simulates shootout outcomes based on kicker placement and keeper dive directions using smooth Framer Motion goalkeeper physics, with an interactive Monte Carlo success rate heat map.

The suite is wrapped in a highly immersive, prestigious **World Cup Television-Broadcast Theme** styled with modern React-based components.

---

## 2. Core Functional Requirements

### A. The Tournament Hub & Time Machine Slider
*   **Data Seed**: The system loads the official 2026 World Cup Group stage fixtures.
*   **Tournament Time Machine**: A timeline slider on the UI allows the user to simulate advancing the tournament date (from June 11th to July 11th, 2026).
*   **Rolling Elo Recalculation**:
    *   Any match scheduled *before* the simulated date is automatically marked as **Completed**.
    *   Completed matches display simulated scorelines generated dynamically by our models.
    *   Standings tables and team ratings are updated in real-time based on these completed scores.
    *   All upcoming matches are predicted instantly using the updated ratings, showing how advancement probabilities shift.

### B. Match Predictor & Team Radar Compare
*   **Dropdown Selection**: Select any two teams to see dynamic outcome probabilities, Elo ratings, and form metrics.
*   **Radar Charting**: Displays a comparative radar chart showing team metrics (Attack, Defense, Elo, Form, Prestige) side-by-side to visualize strengths and weaknesses.
*   **Double Predictor Comparison**: Shows probability outputs from both the baseline Elo Poisson engine and the Logistic Regression ML model using animated progress indicators.

### C. Expected Goals (xG) Isometric Pitch Sandbox
*   **Isometric Pitch**: A styled, 3D-shaded isometric SVG pitch. Clicking on the pitch plots a glowing ball marker.
*   **Dynamic xG Gauge**: Adjust shot variables (Foot/Head, Under Pressure) to compute the goal probability, rendered in an animated radial wheel.

### D. Penalty Shootout Simulator
*   **Goalkeeper Stance & Dive Physics**: Goalkeeper is represented as an animated silhouette diving with realistic velocity curves.
*   **Outcome Indicators**: Target zones glow green (Goal) or red (Save) with particle emission feedback.
*   **Monte Carlo Heat Map**: Displays a heat map overlay of the goal grid, showing save/goal success rates per zone based on 10,000 simulations.

---

## 3. Technology Stack & Design System

### Backend (Python API)
*   **Framework**: FastAPI.
*   **Libraries**: `pandas`, `numpy`, `scikit-learn` (classifier models), `joblib`.

### Frontend (React SPA)
*   **Framework**: Vite (React + TypeScript / JavaScript).
*   **Styling**: TailwindCSS (utility classes and theme tokens).
*   **Animations**: Framer Motion (for liquid-smooth transitions, layout shifts, list cascades).
*   **Charts**: Recharts (for SVG-based Radar charts and Radial progress gauges).
*   **Theme Palette**:
    *   Background Mesh: Linear gradient mixing Deep Charcoal-Maroon (`#120108`), slate midnight (`#050818`), and focal gold points.
    *   Card Containers: High-opacity glass cards (`backdrop-blur-xl bg-white/5 border border-gold/15`).
    *   Highlights & Text: Championship gold (`#d4af37`), neon field green (`#2ecc71`).
    *   Typography: **Orbitron** (for headers and scoreboard scores) and **Inter** (for UI controls, stats, and text).

---

## 4. Agent Skills Matrix & Standards
To ensure the highest engineering standards, the following specialized local agent skills will be invoked across all project phases:
*   **`backend-architect`**: Coordinates directory structures and routes.
*   **`api-design-principles`**: Governs FastAPI REST responses.
*   **`modern-javascript-patterns`**: Guides ES6 and React hooks code formatting.
*   **`high-end-visual-design` & `uxui-principles`**: Shapes layouts, gradients, borders, font weights, and spacing tokens.
*   **`clean-code`**: Directs structural clean code, avoiding copy-paste bloat and global state mutability.
*   **`test-driven-development`** & **`verification-before-completion`**: Directs verification tests.
