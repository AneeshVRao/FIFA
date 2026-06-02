import React, { useState, useEffect } from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip
} from "recharts";
import { Search, MapPin, Calendar, Award, Activity, TrendingUp, Sparkles } from "lucide-react";

const STAT_NAMES = [
  "Goals/90", "Assists/90", "Pass %", "Key Passes", "Prog Carries",
  "Tackles", "Interceptions", "Pressures", "Shots", "xG"
];

// Scales to map the raw stats into a clean 0-100 range for the radar chart balance
const SCALES = [100, 100, 1, 20, 10, 20, 20, 4, 20, 100];

const KEY_TEAMS = [
  "Argentina", "Brazil", "Canada", "England", "France", 
  "Germany", "Mexico", "Portugal", "Spain", "United States"
];

export function PlayerRecruiter() {
  const [selectedTeam, setSelectedTeam] = useState("England");
  const [squad, setSquad] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [similarityData, setSimilarityData] = useState(null);
  const [selectedAnalogue, setSelectedAnalogue] = useState(null);
  const [loadingSquad, setLoadingSquad] = useState(false);
  const [loadingSimilarity, setLoadingSimilarity] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  // Check prefers-reduced-motion
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mediaQuery.matches);
    const listener = (e) => setReducedMotion(e.matches);
    mediaQuery.addEventListener("change", listener);
    return () => mediaQuery.removeEventListener("change", listener);
  }, []);

  // Fetch squad list when team changes
  useEffect(() => {
    fetchSquad(selectedTeam);
  }, [selectedTeam]);

  // Fetch similarity data when selected player changes
  useEffect(() => {
    if (selectedPlayer) {
      fetchSimilarity(selectedPlayer);
    }
  }, [selectedPlayer]);

  const fetchSquad = async (team) => {
    setLoadingSquad(true);
    try {
      const res = await fetch(`/api/squad?team=${team}`);
      if (!res.ok) throw new Error("Squad fetch error");
      const json = await res.json();
      setSquad(json.squad || []);
      if (json.squad && json.squad.length > 0) {
        setSelectedPlayer(json.squad[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingSquad(false);
    }
  };

  const fetchSimilarity = async (player) => {
    setLoadingSimilarity(true);
    try {
      const res = await fetch(
        `/api/players/similar?player=${encodeURIComponent(player.name)}&position=${player.position}`
      );
      if (!res.ok) throw new Error("Similarity fetch error");
      const json = await res.json();
      setSimilarityData(json);
      if (json.similar && json.similar.length > 0) {
        setSelectedAnalogue(json.similar[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingSimilarity(false);
    }
  };

  // Prepares normalized chart data
  const getRadarData = () => {
    if (!similarityData || !selectedAnalogue) return [];
    
    const activeVec = similarityData.vector;
    const analogueVec = selectedAnalogue.vector;
    
    return STAT_NAMES.map((name, i) => {
      const scale = SCALES[i];
      return {
        subject: name,
        [similarityData.player]: parseFloat((activeVec[i] * scale).toFixed(1)),
        [selectedAnalogue.name]: parseFloat((analogueVec[i] * scale).toFixed(1)),
        rawPlayer: activeVec[i],
        rawAnalogue: analogueVec[i]
      };
    });
  };

  const radarData = getRadarData();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[0.8fr_1.2fr] gap-6 mt-6">
      
      {/* ── Left Column: Roster & Roster selection ── */}
      <div 
        className="glass-panel rounded-3xl p-6 border border-gold/15 flex flex-col gap-6 shadow-[0_20px_40px_rgba(0,0,0,0.25)] transition-all duration-300 backdrop-blur-2xl bg-white/5"
        style={{ willChange: "transform" }}
      >
        <div>
          <h3 className="text-white text-lg font-bold font-heading flex items-center gap-2">
            <Search className="w-5 h-5 text-gold" />
            Squad Recruiter Search
          </h3>
          <p className="text-gray-light/80 text-xs mt-1">
            Select a tournament squad to scout active roster players and recruit historical equivalents.
          </p>
        </div>

        {/* Team Selector Dropdown */}
        <div className="flex flex-col gap-2">
          <label className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
            National Team
          </label>
          <select
            value={selectedTeam}
            onChange={(e) => setSelectedTeam(e.target.value)}
            className="w-full bg-gray-dark border border-white/10 rounded-xl px-4 py-3 text-sm text-white font-bold focus:outline-none focus:border-gold transition-all cursor-pointer"
          >
            {KEY_TEAMS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        {/* Player Roster List */}
        <div className="flex flex-col gap-2 flex-grow">
          <label className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
            Active Roster Players
          </label>
          <div className="bg-black/25 rounded-xl border border-white/5 overflow-y-auto max-h-[300px] flex flex-col divide-y divide-white/5 custom-scrollbar">
            {loadingSquad ? (
              <div className="text-center py-6 text-gray-light text-xs font-bold">
                Loading squad...
              </div>
            ) : squad.length === 0 ? (
              <div className="text-center py-6 text-gray-light text-xs">
                No players found.
              </div>
            ) : (
              squad.map((p) => {
                const isSelected = selectedPlayer?.name === p.name;
                return (
                  <button
                    key={p.name}
                    onClick={() => setSelectedPlayer(p)}
                    className={`w-full text-left px-4 py-3 text-xs flex items-center justify-between cursor-pointer transition-all duration-300 ${
                      isSelected
                        ? "bg-gold/10 text-gold font-bold border-l-2 border-gold"
                        : "text-gray-light hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <div>
                      <span className="block font-medium">{p.name}</span>
                      <span className="text-[10px] text-gray-light/60">{p.club}</span>
                    </div>
                    <span className="bg-white/5 border border-white/10 px-2 py-0.5 rounded text-[9px] font-mono font-bold text-white/80">
                      {p.position}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Active Player Metadata Card */}
        {selectedPlayer && (
          <div className="bg-white/5 border border-white/5 rounded-2xl p-4 flex flex-col gap-2">
            <h4 className="text-white text-xs font-extrabold uppercase font-heading tracking-wider flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-gold" />
              Scouting Profile
            </h4>
            <div className="grid grid-cols-2 gap-3 text-xs mt-1">
              <div>
                <span className="block text-[9px] text-white/40 uppercase">Position</span>
                <span className="font-bold text-white">{selectedPlayer.position}</span>
              </div>
              <div>
                <span className="block text-[9px] text-white/40 uppercase">Club Team</span>
                <span className="font-bold text-white truncate block">{selectedPlayer.club}</span>
              </div>
              <div>
                <span className="block text-[9px] text-white/40 uppercase">Age</span>
                <span className="font-bold text-white">{selectedPlayer.age} yrs</span>
              </div>
              <div>
                <span className="block text-[9px] text-white/40 uppercase">Squad Number</span>
                <span className="font-bold text-white">#{selectedPlayer.number}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Right Column: Similarity radar chart & Legends ── */}
      <div className="flex flex-col gap-6">
        {loadingSimilarity || !similarityData ? (
          <div className="glass-panel rounded-3xl p-12 border border-gold/15 flex-grow flex justify-center items-center text-white/80 font-bold font-heading">
            Scouting talent metrics...
          </div>
        ) : (
          <>
            {/* Top Section: Comparison Card & Radar Graph */}
            <div 
              className="glass-panel rounded-3xl p-6 border border-gold/15 grid grid-cols-1 md:grid-cols-[1.1fr_0.9fr] gap-6 shadow-[0_20px_40px_rgba(0,0,0,0.25)] transition-all duration-300 backdrop-blur-2xl bg-white/5"
              style={{ willChange: "transform" }}
            >
              <div className="flex flex-col justify-between">
                <div>
                  <span className="bg-gold/10 border border-gold/30 text-gold text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider inline-flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Talent Analogue Comparison
                  </span>
                  <h3 className="text-white text-xl font-extrabold font-heading mt-2">
                    {selectedPlayer?.name}
                  </h3>
                  <p className="text-gray-light/80 text-xs mt-1">
                    Compared to World Cup Legend <strong className="text-gold">{selectedAnalogue?.name}</strong>.
                  </p>
                </div>

                {/* Legend & Summary Info */}
                {selectedAnalogue && (
                  <div className="bg-black/20 border border-white/5 rounded-2xl p-4 flex flex-col gap-3 mt-4">
                    <div className="flex justify-between items-center pb-2 border-b border-white/5">
                      <span className="text-[10px] text-gold/80 font-bold uppercase tracking-wider">Similarity Index</span>
                      <span className="text-lg font-extrabold text-gold">
                        {(selectedAnalogue.similarity * 100).toFixed(2)}%
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-gold/60" />
                        <span className="text-white/80">{selectedAnalogue.country}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-gold/60" />
                        <span className="text-white/80">{selectedAnalogue.era}</span>
                      </div>
                      <div className="flex items-center gap-1.5 col-span-2">
                        <Award className="w-3.5 h-3.5 text-gold/60" />
                        <span className="text-white/80">{selectedAnalogue.club}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Radar Chart Display */}
              <div className="h-[240px] w-full flex justify-center items-center relative">
                {selectedAnalogue && (
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                      <PolarGrid stroke="rgba(255,255,255,0.06)" />
                      <PolarAngleAxis 
                        dataKey="subject" 
                        tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 8, fontWeight: "bold" }} 
                      />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} stroke="none" />
                      <Radar
                        name={selectedPlayer?.name}
                        dataKey={similarityData.player}
                        stroke="var(--color-field-green)"
                        fill="var(--color-field-green)"
                        fillOpacity={0.25}
                        animationDuration={reducedMotion ? 0 : 500}
                      />
                      <Radar
                        name={selectedAnalogue.name}
                        dataKey={selectedAnalogue.name}
                        stroke="var(--color-gold)"
                        fill="var(--color-gold)"
                        fillOpacity={0.25}
                        animationDuration={reducedMotion ? 0 : 500}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "rgba(27,9,16,0.9)",
                          border: "1px solid rgba(212,175,55,0.3)",
                          borderRadius: "12px",
                          fontSize: "11px",
                          color: "white"
                        }}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            {/* Bottom Section: Analogue Ranks List */}
            <div className="flex flex-col gap-3">
              <h4 className="text-white text-xs font-extrabold uppercase font-heading tracking-wider flex items-center gap-1">
                <TrendingUp className="w-4 h-4 text-gold" />
                Top Historical Analogue Matches
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                {similarityData.similar.map((sim, idx) => {
                  const isSelected = selectedAnalogue?.name === sim.name;
                  return (
                    <button
                      key={sim.name}
                      onClick={() => setSelectedAnalogue(sim)}
                      className={`glass-panel p-3 rounded-2xl border text-left cursor-pointer transition-all duration-300 flex flex-col justify-between gap-2 select-none hover:scale-[1.02] ${
                        isSelected
                          ? "bg-gold/10 border-gold shadow-[0_0_12px_rgba(212,175,55,0.15)]"
                          : "bg-white/5 border-white/10 hover:border-gold/30"
                      }`}
                      style={{ transitionDuration: reducedMotion ? "0ms" : "300ms" }}
                    >
                      <div>
                        <div className="flex justify-between items-center text-[9px] font-mono text-gold/80 font-bold mb-1">
                          <span>Rank #{idx + 1}</span>
                          <span>{(sim.similarity * 100).toFixed(1)}%</span>
                        </div>
                        <h5 className="text-white text-xs font-bold truncate">{sim.name}</h5>
                        <p className="text-gray-light/60 text-[9px] truncate mt-0.5">{sim.country}</p>
                      </div>
                      <span className="text-[8px] bg-white/5 border border-white/10 px-1.5 py-0.5 rounded text-white/50 w-fit">
                        {sim.era}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
