import React from "react";
import { Trophy, BarChart3, Sparkles, Target, Network, PlayCircle, Database, Compass, Users } from "lucide-react";

export function Sidebar({ activeTab, setActiveTab }) {
  const menuItems = [
    { id: "tournament-hub", label: "Tournament Hub", icon: BarChart3 },
    { id: "tournament-bracket", label: "Tournament Bracket", icon: Network },
    { id: "match-predictor", label: "Match Predictor", icon: Sparkles },
    { id: "live-simulator", label: "Live Simulator", icon: PlayCircle },
    { id: "stats-center", label: "Stats Center", icon: Database },
    { id: "tactics-analyzer", label: "Tactics Analyzer", icon: Compass },
    { id: "player-recruiter", label: "Player Recruiter", icon: Users },
    { id: "xg-sandbox", label: "xG Pitch Sandbox", icon: Target },
    { id: "penalty-simulator", label: "Penalty Shootout", icon: Trophy }
  ];

  return (
    <aside className="w-[280px] bg-maroon-dark/95 border-r border-gold/15 flex flex-col justify-between p-6 h-screen sticky top-0 z-40">
      <div>
        {/* Brand Header */}
        <div className="flex items-center gap-4 mb-10 mt-2">
          <div className="text-4xl filter drop-shadow-[0_0_8px_rgba(212,175,55,0.7)] text-gold animate-pulse">
            🏆
          </div>
          <div>
            <h1 className="text-white text-xl font-extrabold leading-none tracking-wide font-heading">
              WORLD CUP
            </h1>
            <span className="text-gold text-[10px] font-bold tracking-[3px] uppercase">
              2026 Analytics
            </span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex flex-col gap-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-lg text-sm font-semibold transition-all duration-300 font-heading cursor-pointer text-left border btn-tactile ${
                  isActive
                    ? "bg-gradient-to-r from-gold/15 to-gold/3 border-gold text-gold shadow-[0_0_12px_rgba(212,175,55,0.15)]"
                    : "border-transparent text-gray-light hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon size={18} className={isActive ? "text-gold" : "text-gray-light"} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer */}
      <div className="border-t border-white/5 pt-5 text-center text-[10px] text-gray-light/60 tracking-wider font-medium">
        <p>Data cut-off: June 2026</p>
        <p className="mt-1 text-gold/70">FastAPI & ML Engine</p>
      </div>
    </aside>
  );
}
