import React, { useState, useMemo } from "react";
import { useTournament } from "./hooks/useTournament";
import { Sidebar } from "./components/Sidebar";
import { TimeMachine } from "./components/TimeMachine";
import { TournamentHub } from "./components/TournamentHub";
import { MatchPredictor } from "./components/MatchPredictor";
import { XgSandbox } from "./components/XgSandbox";
import { ShootoutArena } from "./components/ShootoutArena";
import { LiveMatchSimulator } from "./components/LiveMatchSimulator";
import { StatsCenter } from "./components/StatsCenter";
import { TacticsAnalyzer } from "./components/TacticsAnalyzer";
import OpenerLoader from "./components/OpenerLoader";
import KnockoutBracket from "./components/KnockoutBracket";

function App() {
  const [activeTab, setActiveTab] = useState("tournament-hub");
  const {
    currentDate,
    setCurrentDate,
    fixtures,
    standings,
    ratings,
    loading,
    error
  } = useTournament();

  const renderActivePanel = () => {
    switch (activeTab) {
      case "tournament-hub":
        return (
          <TournamentHub
            fixtures={fixtures}
            standings={standings}
            loading={loading}
          />
        );
      case "match-predictor":
        return <MatchPredictor ratings={ratings} currentDate={currentDate} />;
      case "live-simulator":
        return <LiveMatchSimulator ratings={ratings} currentDate={currentDate} />;
      case "stats-center":
        return <StatsCenter />;
      case "tactics-analyzer":
        return <TacticsAnalyzer ratings={ratings} />;
      case "xg-sandbox":
        return <XgSandbox />;
      case "penalty-simulator":
        return <ShootoutArena />;
      case "tournament-bracket":
        return <KnockoutBracket fixtures={fixtures} />;
      default:
        return (
          <TournamentHub
            fixtures={fixtures}
            standings={standings}
            loading={loading}
          />
        );
    }
  };

  // Calculate live statistics for the sports ticker
  const stats = useMemo(() => {
    let goals = 0;
    let completed = 0;
    const teamGoals = {};

    (fixtures || []).forEach((f) => {
      if (f.status === "completed") {
        completed++;
        const hs = f.home_score || 0;
        const as = f.away_score || 0;
        goals += hs + as;

        if (f.home) teamGoals[f.home] = (teamGoals[f.home] || 0) + hs;
        if (f.away) teamGoals[f.away] = (teamGoals[f.away] || 0) + as;
      }
    });

    let topTeam = "None";
    let maxGoals = 0;
    Object.entries(teamGoals).forEach(([team, g]) => {
      if (g > maxGoals) {
        maxGoals = g;
        topTeam = `${team} (${g} gls)`;
      }
    });

    return {
      goals,
      completed,
      yellows: Math.round(completed * 3.6),
      reds: Math.round(completed * 0.14),
      topTeam
    };
  }, [fixtures]);

  return (
    <>
      {/* 3D WebGL Gold Opener */}
      <OpenerLoader loading={loading} />

      <div className="flex min-h-screen bg-transparent">
        {/* Sidebar Navigation */}
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Main Content Pane */}
        <main className="flex-grow flex flex-col gap-6 p-8 max-h-screen overflow-y-auto">
          
          {/* Sports Broadcast Ticker Feed */}
          <div className="w-full bg-black/40 border border-white/5 rounded-xl overflow-hidden px-4 py-2.5 flex items-center justify-between text-xs font-semibold backdrop-blur-md shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
              <span className="font-heading uppercase tracking-wider text-white/50 text-[10px]">Live Stats Feed</span>
            </div>
            
            <div className="flex gap-8 items-center text-white/80 font-heading tracking-wide text-[10px]">
              <div>
                GOALS: <span className="text-gold font-bold font-numeric">{stats.goals}</span>
              </div>
              <div className="h-3 w-[1px] bg-white/10" />
              <div>
                MATCHES: <span className="text-gold font-bold font-numeric">{stats.completed}/104</span>
              </div>
              <div className="h-3 w-[1px] bg-white/10" />
              <div className="hidden sm:block">
                YELLOW CARDS: <span className="text-gold font-bold font-numeric">{stats.yellows}</span>
              </div>
              <div className="h-3 w-[1px] bg-white/10 hidden sm:block" />
              <div className="hidden sm:block">
                RED CARDS: <span className="text-gold font-bold font-numeric">{stats.reds}</span>
              </div>
              <div className="h-3 w-[1px] bg-white/10 hidden sm:block" />
              <div className="hidden md:block">
                LEADER: <span className="text-gold font-bold">{stats.topTeam}</span>
              </div>
            </div>
          </div>

          {/* Time Machine Slide Badge */}
          <TimeMachine currentDate={currentDate} setCurrentDate={setCurrentDate} />

          {/* Global Error Banner */}
          {error && (
            <div className="bg-danger/10 border border-danger text-danger text-xs font-bold px-4 py-3 rounded-lg flex items-center justify-between">
              <span>Error: {error}</span>
            </div>
          )}

          {/* Render Selected View */}
          <div className="flex-grow">
            {renderActivePanel()}
          </div>
        </main>
      </div>
    </>
  );
}

export default App;
