import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar, Filter, Users } from "lucide-react";

export function TournamentHub({ fixtures, standings, loading }) {
  const [selectedGroup, setSelectedGroup] = useState("A");
  const [filterType, setFilterType] = useState("all");

  const groupTeams = standings[selectedGroup] || [];

  const filteredFixtures = fixtures.filter((fix) => {
    if (filterType === "completed") return fix.status === "completed";
    if (filterType === "upcoming") return fix.status === "upcoming";
    return true;
  });

  const formatDateDisplay = (dateStr) => {
    const date = new Date(dateStr + "T00:00:00");
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric"
    });
  };

  // Animation variants
  const listContainer = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.05 }
    }
  };

  const itemFade = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 100 } }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-6 mt-6">
      
      {/* ── Standings Table Column ── */}
      <div className="glass-panel rounded-2xl p-6 border border-gold/15 flex flex-col h-fit">
        <div className="flex justify-between items-center pb-4 mb-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-gold" />
            <h3 className="text-white text-lg font-bold font-heading">
              Group Standings
            </h3>
          </div>
          
          <select
            value={selectedGroup}
            onChange={(e) => setSelectedGroup(e.target.value)}
            className="bg-gray-dark border border-gold/15 text-white text-xs font-semibold px-4 py-2 rounded-lg cursor-pointer outline-none hover:border-gold transition-all duration-300"
          >
            {["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"].map((g) => (
              <option key={g} value={g}>
                Group {g}
              </option>
            ))}
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-center border-collapse">
            <thead>
              <tr className="text-gold font-heading border-b border-white/10 font-bold">
                <th className="py-3 px-2">Pos</th>
                <th className="py-3 px-2 text-left">Team</th>
                <th className="py-3 px-2">P</th>
                <th className="py-3 px-2">W</th>
                <th className="py-3 px-2">D</th>
                <th className="py-3 px-2">L</th>
                <th className="py-3 px-2">GD</th>
                <th className="py-3 px-2">Pts</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence mode="popLayout">
                {groupTeams.map((team, idx) => (
                  <motion.tr
                    key={team.team}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ type: "spring", stiffness: 200, damping: 20 }}
                    className="hover:bg-white/[0.03] transition-colors duration-200 border-b border-white/5"
                  >
                    <td className="py-4 px-2 font-bold text-gray-light/60">{idx + 1}</td>
                    <td className="py-4 px-2 text-left font-bold text-white">{team.team}</td>
                    <td className="py-4 px-2 font-medium">{team.P}</td>
                    <td className="py-4 px-2 font-medium text-success">{team.W}</td>
                    <td className="py-4 px-2 font-medium text-info">{team.D}</td>
                    <td className="py-4 px-2 font-medium text-danger">{team.L}</td>
                    <td className="py-4 px-2 font-semibold">
                      {team.GD > 0 ? `+${team.GD}` : team.GD}
                    </td>
                    <td className="py-4 px-2 font-extrabold text-gold font-heading text-sm">
                      {team.Pts}
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Fixtures Column ── */}
      <div className="glass-panel rounded-2xl p-6 border border-gold/15 flex flex-col h-[650px]">
        <div className="flex justify-between items-center pb-4 mb-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Calendar size={18} className="text-gold" />
            <h3 className="text-white text-lg font-bold font-heading">
              Fixtures & Predictions
            </h3>
          </div>

          <div className="flex gap-1.5 bg-gray-dark/50 border border-white/5 p-1 rounded-lg">
            {["all", "completed", "upcoming"].map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-3 py-1.5 text-[10px] font-bold tracking-wider rounded-md uppercase transition-all duration-200 cursor-pointer ${
                  filterType === type
                    ? "bg-gold text-maroon-dark shadow-[0_0_8px_rgba(212,175,55,0.25)]"
                    : "text-gray-light hover:text-white"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        {/* Scrollable list */}
        <div className="flex-grow overflow-y-auto pr-1">
          {loading ? (
            <div className="flex justify-center items-center h-48">
              <div className="w-8 h-8 border-2 border-gold border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : (
            <motion.div
              variants={listContainer}
              initial="hidden"
              animate="show"
              className="flex flex-col gap-4"
            >
              <AnimatePresence>
                {filteredFixtures.map((fix) => {
                  const isCompleted = fix.status === "completed";
                  const homeScore = isCompleted ? fix.home_score : "";
                  const awayScore = isCompleted ? fix.away_score : "";

                  return (
                    <motion.div
                      key={fix.match_id}
                      variants={itemFade}
                      layout
                      className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-4 hover:border-gold/25 hover:bg-white/[0.04] transition-all duration-300"
                    >
                      <div className="flex justify-between text-[10px] text-gold font-semibold mb-2">
                        <span>Group {fix.group} • {formatDateDisplay(fix.date)}</span>
                        <span className="opacity-80">{fix.venue}</span>
                      </div>

                      <div className="flex items-center justify-between mb-3">
                        <div className="text-right font-bold text-sm text-white w-[40%] truncate">
                          {fix.home}
                        </div>
                        <div className="w-9 h-9 bg-gray-dark/80 rounded-md font-extrabold text-base flex items-center justify-center border border-white/5">
                          {homeScore}
                        </div>
                        <span className="text-xs font-bold text-gold/60 mx-1">VS</span>
                        <div className="w-9 h-9 bg-gray-dark/80 rounded-md font-extrabold text-base flex items-center justify-center border border-white/5">
                          {awayScore}
                        </div>
                        <div className="text-left font-bold text-sm text-white w-[40%] truncate">
                          {fix.away}
                        </div>
                      </div>

                      {/* Display Predictions inside panel */}
                      <div className="border-t border-white/[0.04] pt-2.5 mt-2 flex justify-between items-center text-[10px] font-semibold">
                        <span className="text-gold/80 tracking-wide uppercase">
                          {isCompleted ? "Completed Result" : "Elo Match Forecast"}
                        </span>
                        
                        {isCompleted ? (
                          <span className="bg-success/20 border border-success/30 px-2 py-0.5 rounded text-success uppercase tracking-wider text-[9px] font-bold">
                            Final
                          </span>
                        ) : (
                          <div className="flex gap-2">
                            <span className="text-success bg-success/5 border border-success/10 px-1.5 py-0.5 rounded">
                              H: {(fix.prediction.home_win * 100).toFixed(0)}%
                            </span>
                            <span className="text-info bg-info/5 border border-info/10 px-1.5 py-0.5 rounded">
                              D: {(fix.prediction.draw * 100).toFixed(0)}%
                            </span>
                            <span className="text-danger bg-danger/5 border border-danger/10 px-1.5 py-0.5 rounded">
                              A: {(fix.prediction.away_win * 100).toFixed(0)}%
                            </span>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              {filteredFixtures.length === 0 && (
                <div className="text-center py-20 text-xs text-gray-light/60 italic">
                  No matches matched the filter criteria.
                </div>
              )}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
