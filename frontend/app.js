/**
 * FIFA World Cup 2026 - SPA Dashboard Logic (app.js)
 * Implements interactive SVGs, state-based tab transitions,
 * dynamic timeline fetches, and prediction charts.
 */

class WorldCupApp {
    constructor() {
        // App State
        this.state = {
            currentDate: "2026-06-11",
            activeTab: "tournament-hub",
            tournamentData: null,
            teamsList: [],
            // xG Sandbox State
            xgState: {
                x: 108.0,
                y: 40.0,
                isHeader: false,
                underPressure: false
            },
            // Penalty Shootout State
            penaltyState: {
                attempts: 0,
                goals: 0,
                saves: 0,
                isLock: false
            }
        };

        // DOM Elements Cache
        this.dom = {
            tabs: document.querySelectorAll(".nav-btn"),
            panels: document.querySelectorAll(".tab-panel"),
            timeSlider: document.getElementById("time-slider"),
            simDateBadge: document.getElementById("current-sim-date"),
            groupSelect: document.getElementById("group-select"),
            standingsTbody: document.getElementById("standings-tbody"),
            fixturesContainer: document.getElementById("fixtures-container"),
            filterBtns: document.querySelectorAll(".filter-btn"),
            
            // Match Predictor
            homeTeamSelect: document.getElementById("home-team-select"),
            awayTeamSelect: document.getElementById("away-team-select"),
            homeRating: document.getElementById("home-rating"),
            awayRating: document.getElementById("away-rating"),
            predictBtn: document.getElementById("predict-btn"),
            predictorResults: document.getElementById("predictor-results"),
            resultsContent: document.querySelector("#predictor-results .results-content"),
            emptyState: document.querySelector("#predictor-results .empty-state"),
            resHomeName: document.getElementById("result-home-name"),
            resAwayName: document.getElementById("result-away-name"),
            resHomeElo: document.getElementById("result-home-elo"),
            resAwayElo: document.getElementById("result-away-elo"),
            
            // Predictor Bars
            eloHomeBar: document.getElementById("elo-home-bar"),
            eloDrawBar: document.getElementById("elo-draw-bar"),
            eloAwayBar: document.getElementById("elo-away-bar"),
            eloHomePct: document.getElementById("elo-home-pct"),
            eloDrawPct: document.getElementById("elo-draw-pct"),
            eloAwayPct: document.getElementById("elo-away-pct"),
            
            mlHomeBar: document.getElementById("ml-home-bar"),
            mlDrawBar: document.getElementById("ml-draw-bar"),
            mlAwayBar: document.getElementById("ml-away-bar"),
            mlHomePct: document.getElementById("ml-home-pct"),
            mlDrawPct: document.getElementById("ml-draw-pct"),
            mlAwayPct: document.getElementById("ml-away-pct"),

            // xG Sandbox
            pitchSvg: document.getElementById("pitch-svg"),
            shotMarker: document.getElementById("shot-marker"),
            coordX: document.getElementById("coord-x"),
            coordY: document.getElementById("coord-y"),
            btnFoot: document.getElementById("btn-foot"),
            btnHead: document.getElementById("btn-head"),
            btnNoPressure: document.getElementById("btn-no-pressure"),
            btnPressure: document.getElementById("btn-pressure"),
            xgVal: document.getElementById("xg-val"),
            xgGaugeBar: document.getElementById("xg-gauge-bar"),
            xgDesc: document.getElementById("xg-desc"),

            // Penalty Simulator
            goalkeeper: document.getElementById("goalkeeper"),
            gridZones: document.querySelectorAll(".grid-zone"),
            resetShootoutBtn: document.getElementById("reset-shootout-btn"),
            shootoutAttempts: document.getElementById("shootout-attempts"),
            shootoutGoals: document.getElementById("shootout-goals"),
            shootoutSaves: document.getElementById("shootout-saves"),
            kickLogs: document.getElementById("kick-logs"),
            runMcBtn: document.getElementById("run-mc-btn"),
            mcResults: document.getElementById("mc-results"),
            mcRateA: document.getElementById("mc-rate-a"),
            mcRateB: document.getElementById("mc-rate-b"),
            mcRounds: document.getElementById("mc-rounds")
        };

        this.init();
    }

    init() {
        this.registerEvents();
        this.fetchTournamentState();
        this.updateXGDisplay();
    }

    // ── Register Event Listeners ─────────────────────────────────
    registerEvents() {
        // Tab switching
        this.dom.tabs.forEach(btn => {
            btn.addEventListener("click", () => this.switchTab(btn.dataset.tab));
        });

        // Time slider timeline change
        this.dom.timeSlider.addEventListener("input", (e) => {
            const date = this.indexToDate(e.target.value);
            this.state.currentDate = date;
            this.dom.simDateBadge.innerText = this.formatDateDisplay(date);
        });
        
        this.dom.timeSlider.addEventListener("change", () => {
            this.fetchTournamentState();
        });

        // Group Standings Select dropdown
        this.dom.groupSelect.addEventListener("change", () => {
            this.renderStandings();
        });

        // Fixtures filter buttons
        this.dom.filterBtns.forEach(btn => {
            btn.addEventListener("click", (e) => {
                this.dom.filterBtns.forEach(b => b.classList.remove("active"));
                e.target.classList.add("active");
                this.renderFixtures(e.target.dataset.filter);
            });
        });

        // Match Predictor Team Dropdown changes (update rating badge)
        this.dom.homeTeamSelect.addEventListener("change", () => this.syncPredictorRatings());
        this.dom.awayTeamSelect.addEventListener("change", () => this.syncPredictorRatings());

        // Match prediction trigger
        this.dom.predictBtn.addEventListener("click", () => this.calculateMatchupPrediction());

        // xG Pitch Click plotting
        this.dom.pitchSvg.addEventListener("click", (e) => this.handlePitchClick(e));

        // xG parameter toggles
        this.dom.btnFoot.addEventListener("click", () => this.toggleXGBodyPart(false));
        this.dom.btnHead.addEventListener("click", () => this.toggleXGBodyPart(true));
        this.dom.btnNoPressure.addEventListener("click", () => this.toggleXGPressure(false));
        this.dom.btnPressure.addEventListener("click", () => this.toggleXGPressure(true));

        // Penalty Shot zones
        this.dom.gridZones.forEach(zone => {
            zone.addEventListener("click", () => this.handlePenaltyShot(zone.dataset.zone));
        });

        // Penalty Reset
        this.dom.resetShootoutBtn.addEventListener("click", () => this.resetPenaltySession());

        // Run Monte Carlo Shootout
        this.dom.runMcBtn.addEventListener("click", () => this.runShootoutMonteCarlo());
    }

    // ── Tab Navigation Fades ─────────────────────────────────────
    switchTab(tabId) {
        if (this.state.activeTab === tabId) return;

        this.dom.tabs.forEach(btn => {
            btn.classList.toggle("active", btn.dataset.tab === tabId);
        });

        this.dom.panels.forEach(panel => {
            if (panel.id === `panel-${tabId}`) {
                panel.classList.add("active");
                this.state.activeTab = tabId;
            } else {
                panel.classList.remove("active");
            }
        });
    }

    // ── Date Conversion Logic ────────────────────────────────────
    indexToDate(index) {
        // Starts June 11, 2026 (index 0) up to July 11, 2026 (index 30)
        const base = new Date(2026, 5, 11);
        base.setDate(base.getDate() + parseInt(index));
        return base.toISOString().split("T")[0];
    }

    formatDateDisplay(dateStr) {
        const date = new Date(dateStr + "T00:00:00");
        return date.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
    }

    // ── Fetch Main API State ──────────────────────────────────────
    async fetchTournamentState() {
        try {
            const res = await fetch(`/api/fixtures?date=${this.state.currentDate}`);
            if (!res.ok) throw new Error("Network response failed");
            
            const data = await res.json();
            this.state.tournamentData = data;
            
            this.renderStandings();
            
            const activeFilter = document.querySelector(".filter-btn.active").dataset.filter;
            this.renderFixtures(activeFilter);
            
            this.populatePredictorDropdowns();
        } catch (err) {
            console.error("Error loading tournament fixtures:", err);
        }
    }

    // ── Render Group Standings ───────────────────────────────────
    renderStandings() {
        if (!this.state.tournamentData) return;
        
        const group = this.dom.groupSelect.value;
        const groupTeams = this.state.tournamentData.standings[group] || [];
        
        let html = "";
        groupTeams.forEach((team, idx) => {
            html += `
                <tr>
                    <td>${idx + 1}</td>
                    <td class="text-left">${team.team}</td>
                    <td>${team.P}</td>
                    <td>${team.W}</td>
                    <td>${team.D}</td>
                    <td>${team.L}</td>
                    <td>${team.GD > 0 ? "+" + team.GD : team.GD}</td>
                    <td style="font-weight: 800; color: var(--color-gold);">${team.Pts}</td>
                </tr>
            `;
        });
        
        this.dom.standingsTbody.innerHTML = html;
    }

    // ── Render Fixtures ──────────────────────────────────────────
    renderFixtures(filter = "all") {
        if (!this.state.tournamentData) return;
        
        const fixtures = this.state.tournamentData.fixtures;
        let html = "";
        
        fixtures.forEach(fix => {
            if (filter === "completed" && fix.status !== "completed") return;
            if (filter === "upcoming" && fix.status !== "upcoming") return;
            
            const isCompleted = fix.status === "completed";
            const homeScore = isCompleted ? fix.home_score : "";
            const awayScore = isCompleted ? fix.away_score : "";
            
            // Build prediction visual percentage tags
            const elo = fix.prediction;
            const predHtml = isCompleted 
                ? `<span class="fixture-status completed">Final</span>`
                : `<div class="prob-split">
                     <span class="success-color">H: ${(elo.home_win * 100).toFixed(0)}%</span>
                     <span class="info-color">D: ${(elo.draw * 100).toFixed(0)}%</span>
                     <span class="fail-color">A: ${(elo.away_win * 100).toFixed(0)}%</span>
                   </div>`;
                   
            html += `
                <div class="fixture-card">
                    <div class="fixture-meta">
                        <span>Group ${fix.group} • ${this.formatDateDisplay(fix.date)}</span>
                        <span>${fix.venue}</span>
                    </div>
                    
                    <div class="scoreboard-row">
                        <div class="team-item home">${fix.home}</div>
                        <div class="score-box">${homeScore}</div>
                        <div class="vs-divider" style="font-size: 14px;">-</div>
                        <div class="score-box">${awayScore}</div>
                        <div class="team-item away">${fix.away}</div>
                    </div>
                    
                    <div class="fixture-prediction-meta">
                        <div class="prediction-badge-grid">
                            <span class="pred-tag">${isCompleted ? "Completed Result" : "Elo Odds Forecast"}</span>
                            ${predHtml}
                        </div>
                    </div>
                </div>
            `;
        });
        
        this.dom.fixturesContainer.innerHTML = html || `<p class="empty-log" style="text-align: center; margin-top: 50px;">No matches fit this filter.</p>`;
    }

    // ── Populate Predictor Teams ─────────────────────────────────
    populatePredictorDropdowns() {
        if (!this.state.tournamentData) return;
        
        // Cache team list
        const ratings = this.state.tournamentData.ratings;
        const teams = Object.keys(ratings).sort();
        
        if (this.state.teamsList.length === teams.length) {
            // Already populated, just update displayed ratings
            this.syncPredictorRatings();
            return;
        }
        
        this.state.teamsList = teams;
        
        let homeOptions = "";
        let awayOptions = "";
        
        teams.forEach(team => {
            // Seed defaults: Home = Spain, Away = Germany
            const homeSelected = team === "Spain" ? "selected" : "";
            const awaySelected = team === "Germany" ? "selected" : "";
            homeOptions += `<option value="${team}" ${homeSelected}>${team}</option>`;
            awayOptions += `<option value="${team}" ${awaySelected}>${team}</option>`;
        });
        
        this.dom.homeTeamSelect.innerHTML = homeOptions;
        this.dom.awayTeamSelect.innerHTML = awayOptions;
        
        this.syncPredictorRatings();
    }

    syncPredictorRatings() {
        if (!this.state.tournamentData) return;
        
        const ratings = this.state.tournamentData.ratings;
        const homeTeam = this.dom.homeTeamSelect.value;
        const awayTeam = this.dom.awayTeamSelect.value;
        
        const homeElo = ratings[homeTeam] || 1500;
        const awayElo = ratings[awayTeam] || 1500;
        
        this.dom.homeRating.innerText = `Elo: ${homeElo.toFixed(0)}`;
        this.dom.awayRating.innerText = `Elo: ${awayElo.toFixed(0)}`;
    }

    // ── Predict Custom Matchup API ────────────────────────────────
    async calculateMatchupPrediction() {
        const home = this.dom.homeTeamSelect.value;
        const away = this.dom.awayTeamSelect.value;
        
        if (home === away) {
            alert("Please select two different teams.");
            return;
        }
        
        this.dom.predictBtn.innerText = "Simulating...";
        this.dom.predictBtn.disabled = true;
        
        try {
            const res = await fetch(`/api/predict?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}&date=${this.state.currentDate}`);
            if (!res.ok) throw new Error("Prediction API call failed");
            
            const data = await res.json();
            
            // Show outcomes
            this.dom.emptyState.classList.add("hidden");
            this.dom.resultsContent.classList.remove("hidden");
            
            this.dom.resHomeName.innerText = data.home;
            this.dom.resAwayName.innerText = data.away;
            this.dom.resHomeElo.innerText = `Elo: ${data.elo_home}`;
            this.dom.resAwayElo.innerText = `Elo: ${data.elo_away}`;
            
            // Elo Progress bars
            const elo = data.elo_prediction;
            this.animateBar(this.dom.eloHomeBar, this.dom.eloHomePct, elo.home_win);
            this.animateBar(this.dom.eloDrawBar, this.dom.eloDrawPct, elo.draw);
            this.animateBar(this.dom.eloAwayBar, this.dom.eloAwayPct, elo.away_win);
            
            // ML Progress bars
            const ml = data.ml_prediction;
            this.animateBar(this.dom.mlHomeBar, this.dom.mlHomePct, ml.home_win);
            this.animateBar(this.dom.mlDrawBar, this.dom.mlDrawPct, ml.draw);
            this.animateBar(this.dom.mlAwayBar, this.dom.mlAwayPct, ml.away_win);
            
        } catch (err) {
            console.error("Match prediction failed:", err);
            alert("Could not load match forecast. Please try again.");
        } finally {
            this.dom.predictBtn.innerText = "Simulate Matchup";
            this.dom.predictBtn.disabled = false;
        }
    }

    animateBar(barEl, labelEl, value) {
        const pct = (value * 100).toFixed(1);
        barEl.style.width = `${pct}%`;
        labelEl.innerText = `${pct}%`;
    }

    // ── xG Pitch Click Handler ───────────────────────────────────
    handlePitchClick(event) {
        const svg = this.dom.pitchSvg;
        const pt = svg.createSVGPoint();
        pt.x = event.clientX;
        pt.y = event.clientY;
        
        // Convert screen coordinates to SVG viewBox coordinate system
        const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());
        
        // Boundaries are restricted to the attacking third in viewBox (60 to 120x, 0 to 80y)
        const x = Math.min(Math.max(svgP.x, 60.0), 120.0);
        const y = Math.min(Math.max(svgP.y, 0.0), 80.0);
        
        this.state.xgState.x = parseFloat(x.toFixed(1));
        this.state.xgState.y = parseFloat(y.toFixed(1));
        
        this.dom.shotMarker.setAttribute("cx", x);
        this.dom.shotMarker.setAttribute("cy", y);
        this.dom.shotMarker.classList.remove("hidden");
        
        this.dom.coordX.innerText = this.state.xgState.x.toFixed(1);
        this.dom.coordY.innerText = this.state.xgState.y.toFixed(1);
        
        this.updateXGDisplay();
    }

    toggleXGBodyPart(isHeader) {
        this.state.xgState.isHeader = isHeader;
        this.dom.btnFoot.classList.toggle("active", !isHeader);
        this.dom.btnHead.classList.toggle("active", isHeader);
        this.updateXGDisplay();
    }

    toggleXGPressure(underPressure) {
        this.state.xgState.underPressure = underPressure;
        this.dom.btnNoPressure.classList.toggle("active", !underPressure);
        this.dom.btnPressure.classList.toggle("active", underPressure);
        this.updateXGDisplay();
    }

    async updateXGDisplay() {
        const { x, y, isHeader, underPressure } = this.state.xgState;
        
        try {
            const res = await fetch(`/api/xg?x=${x}&y=${y}&is_header=${isHeader}&under_pressure=${underPressure}`);
            if (!res.ok) throw new Error("xG API error");
            const data = await res.json();
            const xgVal = data.xg;
            
            this.dom.xgVal.innerText = xgVal.toFixed(2);
            this.dom.xgGaugeBar.style.width = `${xgVal * 100}%`;
            
            // Build dynamic text comments
            let comment = "";
            if (xgVal >= 0.70) {
                comment = "Championship Penalty Grade. An exceptionally high-probability opportunity. Highly likely to score.";
            } else if (xgVal >= 0.35) {
                comment = "High-quality shot inside the goal box. Excellent converting chance.";
            } else if (xgVal >= 0.15) {
                comment = "Moderate opportunity. Common conversion rate from within the penalty box under pressure.";
            } else if (xgVal >= 0.05) {
                comment = "Low-probability conversion attempt. Typical long-range shot or angled header.";
            } else {
                comment = "Speculative attempt. Very small likelihood of scoring from this distance and angle.";
            }
            
            this.dom.xgDesc.innerText = comment;
        } catch (err) {
            console.error("Failed to fetch xG values:", err);
        }
    }

    // ── Penalty Shootout Arena ───────────────────────────────────
    async handlePenaltyShot(zone) {
        if (this.state.penaltyState.isLock) return;
        this.state.penaltyState.isLock = true;
        
        // Random Goalkeeper Dive selection
        const dives = ["L", "C", "R"];
        const dive = dives[Math.floor(Math.random() * 3)];
        
        // Trigger Goalkeeper Dive animation
        this.dom.goalkeeper.className = `goalkeeper dive-${dive}`;
        
        // Visual indicator on target zone
        const clickedZoneBtn = document.getElementById(`zone-${zone}`);
        
        try {
            const res = await fetch(`/api/shootout?kicker_zone=${zone}&keeper_dive=${dive}`);
            if (!res.ok) throw new Error("Shootout API error");
            const data = await res.json();
            
            this.state.penaltyState.attempts++;
            
            // Wait for dive animation center swing (approx 400ms)
            setTimeout(() => {
                let statusText = "";
                if (data.scored) {
                    this.state.penaltyState.goals++;
                    clickedZoneBtn.classList.add("scored");
                    statusText = "GOAL! Shot flew past the goalkeeper's reach.";
                    this.addKickLog(this.state.penaltyState.attempts, zone, dive, "Scored", "success-color");
                } else {
                    this.state.penaltyState.saves++;
                    clickedZoneBtn.classList.add("saved");
                    statusText = data.miss_frame ? "MISSED! Shot flew wide off the goalposts." : "SAVED! Goalkeeper blocked the target zone.";
                    this.addKickLog(this.state.penaltyState.attempts, zone, dive, data.miss_frame ? "Missed" : "Saved", "fail-color");
                }
                
                this.updatePenaltyCounters();
            }, 400);

            // Reset goalkeeper stance after delay
            setTimeout(() => {
                this.dom.goalkeeper.className = "goalkeeper";
                this.dom.gridZones.forEach(z => {
                    z.classList.remove("scored", "saved");
                });
                this.state.penaltyState.isLock = false;
            }, 2600);
            
        } catch (err) {
            console.error("Penalty simulator failed:", err);
            this.state.penaltyState.isLock = false;
            this.dom.goalkeeper.className = "goalkeeper";
        }
    }

    updatePenaltyCounters() {
        this.dom.shootoutAttempts.innerText = this.state.penaltyState.attempts;
        this.dom.shootoutGoals.innerText = this.state.penaltyState.goals;
        this.dom.shootoutSaves.innerText = this.state.penaltyState.saves;
    }

    addKickLog(round, zone, dive, result, styleClass) {
        const emptyMsg = this.dom.kickLogs.querySelector(".empty-log");
        if (emptyMsg) emptyMsg.remove();
        
        const row = document.createElement("p");
        row.className = "log-row";
        row.innerHTML = `Shot #${round}: Amed <strong>${zone}</strong>, Goalie dived <strong>${dive}</strong> &rarr; <span class="${styleClass}">${result}</span>`;
        this.dom.kickLogs.prepend(row);
    }

    resetPenaltySession() {
        this.state.penaltyState.attempts = 0;
        this.state.penaltyState.goals = 0;
        this.state.penaltyState.saves = 0;
        this.dom.goalkeeper.className = "goalkeeper";
        this.dom.gridZones.forEach(z => {
            z.classList.remove("scored", "saved");
        });
        this.updatePenaltyCounters();
        this.dom.kickLogs.innerHTML = `<p class="empty-log">No kicks taken yet in this session.</p>`;
    }

    // ── Run Monte Carlo Simulation (10K rounds) ──────────────────
    async runShootoutMonteCarlo() {
        this.dom.runMcBtn.innerText = "Running Simulations...";
        this.dom.runMcBtn.disabled = true;
        
        try {
            const res = await fetch("/api/shootout/montecarlo?simulations=10000");
            if (!res.ok) throw new Error("Monte Carlo API failure");
            const data = await res.json();
            
            this.dom.mcResults.classList.remove("hidden");
            this.dom.mcRateA.innerText = `${(data.team_a_win_rate * 100).toFixed(1)}%`;
            this.dom.mcRateB.innerText = `${(data.team_b_win_rate * 100).toFixed(1)}%`;
            this.dom.mcRounds.innerText = data.avg_rounds.toFixed(2);
        } catch (err) {
            console.error("Monte Carlo simulations failed:", err);
            alert("Monte Carlo simulation failed. Please try again.");
        } finally {
            this.dom.runMcBtn.innerText = "Run 10K Simulation";
            this.dom.runMcBtn.disabled = false;
        }
    }
}

// Instantiate on load
window.addEventListener("DOMContentLoaded", () => {
    window.app = new WorldCupApp();
});
