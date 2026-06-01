import React, { useState } from "react";
import { useTournament } from "./hooks/useTournament";
import { Sidebar } from "./components/Sidebar";
import { TimeMachine } from "./components/TimeMachine";
import { TournamentHub } from "./components/TournamentHub";
import { MatchPredictor } from "./components/MatchPredictor";
import { XgSandbox } from "./components/XgSandbox";
import { ShootoutArena } from "./components/ShootoutArena";

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
      case "xg-sandbox":
        return <XgSandbox />;
      case "penalty-simulator":
        return <ShootoutArena />;
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

  return (
    <div className="flex min-h-screen bg-transparent">
      {/* Sidebar Navigation */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Pane */}
      <main className="flex-grow flex flex-col gap-6 p-8 max-h-screen overflow-y-auto">
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
  );
}

export default App;
