# Product Requirements Document (PRD): FIFA World Cup Analytics Suite

## 1. Product Overview & Goals
The **FIFA World Cup Analytics Suite** is an interactive, unified web dashboard that integrates three distinct machine learning predictions and sports analytics tools:
1. **Match Outcome Predictor**: Calculates outcome probabilities (Win/Draw/Loss) for any international match-up.
2. **Expected Goals (xG) Model**: Evaluates shot quality dynamically based on coordinates and game conditions.
3. **Penalty Shootout Predictor**: Simulates shootout outcomes based on kicker performance, target zones, and goalkeeper actions.

The suite is wrapped in a premium, immersive **FIFA World Cup theme** (maroon, gold, field green styling) designed as a single-page website dashboard.

---

## 2. Core Functional Requirements

### A. The Tournament Hub & Time Machine Slider
* **Data Seed**: The system loads the official 2026 World Cup Group A fixtures (e.g. Mexico vs. South Africa on June 11, 2026).
* **Current Timeline State**: Since the local date is June 1, 2026, all matches are initially marked as "Upcoming."
* **Tournament Time Machine**: A slider on the UI allows the user to simulate advancing the current tournament date (from June 1st to July 20th, 2026).
* **Auto-Tracking & Done Status**:
  * Any match scheduled *before* the simulated date is automatically marked as **Completed (done)**.
  * Completed matches display a simulated final scoreline (generated dynamically by our predictive models).
  * Standings tables and team statistics are updated in real-time based on these completed scores.

### B. Rolling Elo Recalculation Engine
* **Initial State**: All teams are assigned a baseline Elo rating calculated from historical international matches up to June 2026.
* **Rolling Update Loop**:
  1. As matches are marked "done", the backend processes them chronologically.
  2. The Elo rating of each team is updated sequentially based on the simulated scoreline.
  3. The team's recent form (goals scored, goal differential) is recalculated.
* **Adaptive Forecasts**: All future (unplayed) matches are re-predicted instantly using the updated ratings, showing how team advancement probabilities adjust dynamically as the tournament progresses.

### C. Expected Goals (xG) Sandbox
* **Interactive Pitch**: A styled SVG soccer pitch. Clicking on the pitch plots a shot marker.
* **Parameters**: User can configure shot conditions (Body Part: Foot/Head, Under Pressure: Yes/No).
* **Real-time Prediction**: Displays an updated xG gauge showing the probability of the shot scoring based on its distance and angle to the goal.

### D. Penalty Shootout Simulator
* **Interactive Goal Grid**: Users select where the kicker aims (grid sections: top-left, bottom-right, etc.) and where the goalkeeper dives.
* **Monte Carlo Simulation**: Runs 10,000 simulations to calculate overall team shootout success rates, showing animations for individual kicker vs. goalkeeper matchups.

---

## 3. Technology Stack & Design System

### Backend (Python API)
* **Framework**: FastAPI (clean REST endpoints).
* **Libraries**: `pandas`, `numpy`, `scikit-learn` (classifier models), `statsbombpy` (raw event-level shot training data).

### Frontend (Single Page Website)
* **Tech**: Vanilla HTML5, Vanilla CSS3 (custom responsive layouts), ES6 JavaScript.
* **Branding Theme**:
  * Background: Deep charcoal-maroon gradient (`linear-gradient(135deg, #13030a, #200412)`).
  * Highlights & Borders: Championship gold (`#d4af37`).
  * Field Accents: Grass field green (`#2ecc71`).
  * Micro-animations: Glassmorphism tabs transitions, fade-in scoreboard stats, and sliding score tickers.

---

## 4. Agent Skills Matrix & Standards
To ensure the highest engineering standards, the following specialized local agent skills will be invoked across all project phases:

### A. Architectural & API Design
* **`backend-architect`**: Establishes clean directory separation, single-responsibility files, and robust package routing.
* **`api-design-principles`**: Governs the design of FastAPI endpoints (`/api/fixtures`, `/api/predict`, etc.) ensuring standardized response structures and clean parameter bindings.
* **`ux-flow`**: Maps out chronological state tracking for the dynamic Tournament Time Machine slider.

### B. Machine Learning & Mathematics
* **`scikit-learn`**: Powers data processing, feature scaling, model selection, and logistic regression training.
* **`statsmodels`**: Directs mathematical formulations (distance-to-goal and goal-angle trigonometry) and guides Poisson probability calculations for match score simulations.

### C. Clean Coding & Frontend Taste
* **`clean-code`**: Enforces strict code formatting, meaningful variable naming, and avoidance of global states.
* **`python-fastapi-development`**: Orchestrates fast async backend path definitions.
* **`modern-javascript-patterns`**: Guides the frontend implementation (ES6 classes, modular event listeners, and fetch state management) to avoid framework bloat.
* **`high-end-visual-design` & `uxui-principles`**: Shapes the premium tournament-broadcast style, defining the glassmorphism CSS grid, scoreboard animations, and interactive SVG widgets.

### D. Quality Assurance & Auditing
* **`data-quality-frameworks`**: Sanitizes StatsBomb event streams, filtering out missing values or out-of-bound shot coordinates.
* **`test-driven-development`**: Sets up the backend unit test suite to verify Elo calculations and score limits prior to integration.
* **`verification-before-completion`** & **`systematic-debugging`**: Ensures all visual components, charts, and mathematical models are verified against baseline data before wrapping up development phases.

---

## 5. Git & GitHub Workflow Constraints
To follow optimal collaborative practices, the development team must adhere to the following workflow for every task listed in `PROGRESS.md`:

1. **Remote Repository**: Sourced and synced with `https://github.com/AneeshVRao/FIFA`.
2. **Branching Strategy**: For each task (e.g., Task 1: Environment Setup), the agent will spin up a descriptive feature branch:
   `git checkout -b feature/task-name`
3. **Commit Incrementally**: Upon completing a task, verify the changes and commit them:
   `git add .`
   `git commit -m "feat: complete task description"`
4. **Publish Branch**: Push the feature branch to the remote repository.
5. **Pull Requests**:
   * Open a Pull Request (PR) on GitHub from `feature/task-name` into `main`.
   * **Wait for Merge**: Halt further development, ask the user to merge the PR, and wait for confirmation.
6. **Main Synchronization**: Once the PR is merged by the user:
   * Switch back to the local `main` branch.
   * Pull the updated main: `git pull origin main`.
   * Delete the local feature branch and spin up the next feature branch.


