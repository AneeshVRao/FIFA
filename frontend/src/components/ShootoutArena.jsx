import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Target, RotateCcw, Activity } from "lucide-react";

export function ShootoutArena() {
  const [session, setSession] = useState({
    attempts: 0,
    goals: 0,
    saves: 0,
    logs: []
  });

  const [gameState, setGameState] = useState({
    keeperDive: "C", // L, C, R
    activeZone: null, // clicked zone
    shotOutcome: null, // "scored" or "saved"
    isLock: false
  });

  const [mcResults, setMcResults] = useState(null);
  const [mcLoading, setMcLoading] = useState(false);

  const zones = ["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"];

  const handleZoneClick = async (zone) => {
    if (gameState.isLock) return;
    setGameState((prev) => ({ ...prev, isLock: true, activeZone: zone }));

    const dives = ["L", "C", "R"];
    const chosenDive = dives[Math.floor(Math.random() * 3)];

    // Trigger goalie animation
    setGameState((prev) => ({ ...prev, keeperDive: chosenDive }));

    try {
      const res = await fetch(
        `/api/shootout?kicker_zone=${zone}&keeper_dive=${chosenDive}`
      );
      if (!res.ok) throw new Error("Shootout API error");
      const data = await res.json();

      // Wait for dive animation midpoint to show score result (400ms)
      setTimeout(() => {
        const isGoal = data.scored;
        const outcome = isGoal ? "scored" : "saved";
        const resultLabel = isGoal ? "Scored" : data.miss_frame ? "Missed" : "Saved";

        setGameState((prev) => ({
          ...prev,
          shotOutcome: outcome
        }));

        setSession((prev) => {
          const nextAttempts = prev.attempts + 1;
          const nextGoals = isGoal ? prev.goals + 1 : prev.goals;
          const nextSaves = !isGoal ? prev.saves + 1 : prev.saves;
          const logEntry = {
            id: nextAttempts,
            zone,
            dive: chosenDive,
            result: resultLabel,
            success: isGoal
          };
          return {
            attempts: nextAttempts,
            goals: nextGoals,
            saves: nextSaves,
            logs: [logEntry, ...prev.logs]
          };
        });
      }, 400);

      // Reset goalkeeper and grids after delay
      setTimeout(() => {
        setGameState({
          keeperDive: "C",
          activeZone: null,
          shotOutcome: null,
          isLock: false
        });
      }, 2500);

    } catch (err) {
      console.error(err);
      setGameState((prev) => ({ ...prev, isLock: false, keeperDive: "C", activeZone: null }));
    }
  };

  const resetSession = () => {
    setSession({
      attempts: 0,
      goals: 0,
      saves: 0,
      logs: []
    });
    setGameState({
      keeperDive: "C",
      activeZone: null,
      shotOutcome: null,
      isLock: false
    });
  };

  const runMonteCarlo = async () => {
    setMcLoading(true);
    try {
      const res = await fetch("/api/shootout/montecarlo?simulations=10000");
      if (!res.ok) throw new Error("Monte Carlo API failure");
      const json = await res.json();
      setMcResults(json);
    } catch (err) {
      console.error(err);
      alert("Monte Carlo simulation failed. Please try again.");
    } finally {
      setMcLoading(false);
    }
  };

  // Framer Motion dive transforms
  const getGoalieAnimation = () => {
    switch (gameState.keeperDive) {
      case "L":
        return { x: -130, y: 30, rotate: -75, scale: 0.95 };
      case "R":
        return { x: 130, y: 30, rotate: 75, scale: 0.95 };
      case "C":
        // Only jump if a shot is active, else stay idle
        return gameState.activeZone 
          ? { x: 0, y: -20, scale: 1.1, rotate: 0 }
          : { x: 0, y: 0, scale: 1, rotate: 0 };
      default:
        return { x: 0, y: 0, scale: 1, rotate: 0 };
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-6 mt-6">
      
      {/* ── Goal Arena Column ── */}
      <div className="glass-panel rounded-2xl p-6 border border-gold/15 flex flex-col gap-4">
        <div className="pb-2">
          <h3 className="text-white text-lg font-bold font-heading">
            Penalty Shootout Arena
          </h3>
          <p className="text-gray-light/80 text-xs mt-1">
            Shoot at any goal grid zone. The goalkeeper will dynamically dive based on physical probabilities.
          </p>
        </div>

        {/* Goal Canvas */}
        <div className="bg-gradient-to-b from-[#1b2f20] to-[#0c150e] border-2 border-gold/10 rounded-2xl p-8 flex justify-center items-end min-h-[380px] shadow-[inset_0_0_30px_rgba(0,0,0,0.8)] relative overflow-hidden">
          
          {/* Soccer Goal posts framework */}
          <div className="relative w-full max-w-[540px] h-[220px] border-t-8 border-x-8 border-white bg-black/45 shadow-[0_4px_10px_rgba(0,0,0,0.6)]">
            
            {/* Goalkeeper Silhouette */}
            <motion.div
              animate={getGoalieAnimation()}
              transition={{ type: "spring", stiffness: 120, damping: 14 }}
              className="absolute bottom-0 left-[50%] ml-[-26px] text-5xl leading-none select-none z-10 filter drop-shadow-[0_4px_6px_rgba(0,0,0,0.5)] goalkeeper-transition"
            >
              🧤
            </motion.div>

            {/* Target 3x3 Overlay Grid */}
            <div className="grid grid-rows-3 grid-cols-3 w-full h-full absolute top-0 left-0 z-20">
              {zones.map((zone) => {
                const isActive = gameState.activeZone === zone;
                const outcome = gameState.shotOutcome;
                const isHeatmap = mcResults !== null;

                let zoneClass = "bg-transparent border border-white/5 hover:bg-gold/15 hover:border-gold";
                if (isActive && outcome === "scored") {
                  zoneClass = "bg-success/30 border-2 border-success";
                } else if (isActive && outcome === "saved") {
                  zoneClass = "bg-danger/30 border-2 border-danger";
                }

                // Heatmap values
                const rate = isHeatmap ? mcResults.zone_score_rates[zone] : null;

                return (
                  <button
                    key={zone}
                    onClick={() => handleZoneClick(zone)}
                    disabled={gameState.isLock}
                    className={`relative cursor-crosshair flex items-center justify-center transition-all duration-200 group ${zoneClass}`}
                  >
                    {!isHeatmap ? (
                      <span className="font-heading font-bold text-xs bg-black/60 px-2 py-0.5 rounded text-white opacity-0 group-hover:opacity-100 transition-opacity">
                        {zone}
                      </span>
                    ) : (
                      <div className="absolute inset-0 flex flex-col justify-center items-center bg-gold/5 font-heading font-extrabold text-sm text-gold-hover filter drop-shadow-[0_0_2px_rgba(212,175,55,0.3)]">
                        <span className="text-[10px] text-white/55 font-bold uppercase">{zone}</span>
                        <span>{(rate * 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={resetSession}
            className="flex items-center gap-2 border border-gold/15 hover:bg-gold hover:text-maroon-dark hover:border-gold text-gold font-heading font-bold text-xs py-2.5 px-5 rounded-lg cursor-pointer transition-all duration-300"
          >
            <RotateCcw size={14} />
            Reset Session
          </button>
        </div>
      </div>

      {/* ── Statistics & Monte Carlo Simulator Column ── */}
      <div className="glass-panel rounded-2xl p-6 border border-gold/15 flex flex-col justify-between">
        
        {/* Session statistics ticker */}
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-2 pb-4 border-b border-white/5">
            <Activity size={18} className="text-gold" />
            <h3 className="text-white text-lg font-bold font-heading">
              Session Statistics
            </h3>
          </div>

          <div className="flex gap-4">
            <div className="bg-gray-dark border border-white/5 p-3 rounded-xl flex-grow text-center">
              <span className="block text-[10px] text-gray-light/60 font-semibold mb-1">Kicks</span>
              <span className="font-heading font-extrabold text-lg text-white">{session.attempts}</span>
            </div>
            <div className="bg-gray-dark border border-white/5 p-3 rounded-xl flex-grow text-center">
              <span className="block text-[10px] text-gray-light/60 font-semibold mb-1">Goals</span>
              <span className="font-heading font-extrabold text-lg text-success">{session.goals}</span>
            </div>
            <div className="bg-gray-dark border border-white/5 p-3 rounded-xl flex-grow text-center">
              <span className="block text-[10px] text-gray-light/60 font-semibold mb-1">Saves/Miss</span>
              <span className="font-heading font-extrabold text-lg text-danger">{session.saves}</span>
            </div>
          </div>

          {/* Logs */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
              Kick History Logs
            </span>
            <div className="bg-black/35 border border-white/5 rounded-xl p-4 h-[120px] overflow-y-auto text-[11px] flex flex-col gap-2">
              <AnimatePresence>
                {session.logs.map((log) => (
                  <motion.p
                    key={log.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="border-b border-white/5 pb-1 flex justify-between"
                  >
                    <span>
                      Shot #{log.id}: Zone <strong>{log.zone}</strong>, Goalie dived <strong>{log.dive}</strong>
                    </span>
                    <strong className={log.success ? "text-success" : "text-danger"}>
                      {log.result}
                    </strong>
                  </motion.p>
                ))}
              </AnimatePresence>
              {session.logs.length === 0 && (
                <div className="text-center text-gray-light/60 italic mt-8">
                  No kicks taken yet in this session.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Monte Carlo Simulator */}
        <div className="border-t border-white/5 pt-5 mt-4 flex flex-col gap-4">
          <div>
            <h4 className="text-white text-sm font-extrabold font-heading tracking-wide uppercase">
              Monte Carlo Analytics
            </h4>
            <p className="text-gray-light/80 text-[11px] mt-1 leading-relaxed">
              Execute a batch simulation of 10,000 matches to analyze overall win rates and generate target zone score heatmaps.
            </p>
          </div>

          <button
            onClick={runMonteCarlo}
            disabled={mcLoading}
            className="w-full bg-gradient-to-r from-gold to-[#b28d1d] hover:from-gold-hover hover:to-gold text-maroon-dark font-heading font-extrabold text-xs py-3 rounded-lg cursor-pointer transition-all duration-300 shadow-[0_4px_15px_rgba(212,175,55,0.15)] hover:shadow-[0_8px_25px_rgba(212,175,55,0.25)] hover:-translate-y-0.5 disabled:opacity-50"
          >
            {mcLoading ? "Running Simulations..." : "Generate 10K Simulation Heatmap"}
          </button>

          <AnimatePresence>
            {mcResults && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="bg-black/25 rounded-xl p-4 border border-white/5 flex flex-col gap-2 text-xs"
              >
                <div className="flex justify-between">
                  <span>Team A Expected Win Rate</span>
                  <strong className="text-gold font-bold">{(mcResults.team_a_win_rate * 100).toFixed(1)}%</strong>
                </div>
                <div className="flex justify-between">
                  <span>Team B Expected Win Rate</span>
                  <strong className="text-gold font-bold">{(mcResults.team_b_win_rate * 100).toFixed(1)}%</strong>
                </div>
                <div className="flex justify-between">
                  <span>Average Penalty Rounds</span>
                  <strong className="text-gold font-bold">{mcResults.avg_rounds.toFixed(2)}</strong>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

      </div>
    </div>
  );
}
