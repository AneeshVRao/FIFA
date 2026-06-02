import React, { useState, useEffect } from "react";
import { Sparkles, Loader2, Compass, History, Activity } from "lucide-react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend
} from "recharts";

export function TacticsAnalyzer({ ratings }) {
  const teams = Object.keys(ratings || {}).sort();
  const [homeTeam, setHomeTeam] = useState("Spain");
  const [awayTeam, setAwayTeam] = useState("Germany");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Sync default team selections
  useEffect(() => {
    if (teams.length > 0) {
      if (!teams.includes(homeTeam)) setHomeTeam(teams[0]);
      if (!teams.includes(awayTeam)) setAwayTeam(teams[1] || teams[0]);
    }
  }, [ratings]);

  useEffect(() => {
    if (homeTeam && awayTeam && homeTeam !== awayTeam) {
      fetchTacticsMatchup();
    }
  }, [homeTeam, awayTeam]);

  const fetchTacticsMatchup = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `/api/tactics/matchup?home=${encodeURIComponent(homeTeam)}&away=${encodeURIComponent(awayTeam)}`
      );
      if (!res.ok) throw new Error("Tactics API failed");
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getRadarData = () => {
    if (!data) return [];
    
    const labels = [
      "Pressing",
      "Line Height",
      "Possession",
      "Directness",
      "Squad Value",
      "Avg. Age",
      "Attacking",
      "Defensive",
      "Crossing",
      "Counter Speed"
    ];
    
    return labels.map((label, idx) => ({
      attribute: label,
      [homeTeam]: Math.round(data.home_vector[idx] * 100),
      [awayTeam]: Math.round(data.away_vector[idx] * 100)
    }));
  };

  // Compile a dynamic, professional tactical briefing based on vector comparison values
  const generateBriefing = () => {
    if (!data) return "";
    
    const hVec = data.home_vector;
    const aVec = data.away_vector;
    
    let insights = [];
    
    // Possession vs Block
    if (hVec[2] > 0.70 && aVec[1] > 0.65) {
      insights.push(`${homeTeam} is projected to dominate possession (${Math.round(hVec[2]*100)}%), which will collide directly with ${awayTeam}'s deep block defensive posture (${Math.round(aVec[1]*100)}% block depth).`);
    } else if (aVec[2] > 0.70 && hVec[1] > 0.65) {
      insights.push(`${awayTeam} is projected to control the ball (${Math.round(aVec[2]*100)}%), testing ${homeTeam}'s deep defensive block (${Math.round(hVec[1]*100)}% block depth).`);
    }
    
    // Pressing styles
    if (hVec[0] > 0.80 && aVec[0] > 0.80) {
      insights.push("Both teams deploy aggressive high-pressing systems (PPDA percentile >80), signaling an intense mid-pitch battle for turnovers.");
    } else if (hVec[0] > 0.80) {
      insights.push(`${homeTeam} will utilize high pressing (${Math.round(hVec[0]*100)}%) to disrupt ${awayTeam}'s build-up phase.`);
    } else if (aVec[0] > 0.80) {
      insights.push(`${awayTeam} will utilize high pressing (${Math.round(aVec[0]*100)}%) to disrupt ${homeTeam}'s build-up phase.`);
    }

    // Transitions & Counter speed
    if (hVec[9] > 0.75 && hVec[3] > 0.60) {
      insights.push(`${homeTeam}'s directness and counter-attack speed (${Math.round(hVec[9]*100)}%) represents a high transition threat.`);
    }
    if (aVec[9] > 0.75 && aVec[3] > 0.60) {
      insights.push(`${awayTeam}'s directness and counter-attack speed (${Math.round(aVec[9]*100)}%) represents a high transition threat.`);
    }

    // Budget discrepancy
    const valDiff = Math.abs(hVec[4] - aVec[4]);
    if (valDiff > 0.35) {
      const richer = hVec[4] > aVec[4] ? homeTeam : awayTeam;
      const poorer = hVec[4] > aVec[4] ? awayTeam : homeTeam;
      insights.push(`There is a significant squad market value disparity. ${richer}'s elite roster value gives them a depth advantage over ${poorer}.`);
    }

    if (insights.length === 0) {
      insights.push("Both teams present balanced tactical structures. Expect a cagey affair decided by micro-tactical shifts or individual brilliance.");
    }

    return insights.join(" ");
  };

  return (
    <div className="flex flex-col gap-6">
      
      {/* ── Matchup Team Selector ── */}
      <div className="glass-panel rounded-2xl border border-gold/15 p-6 shadow-2xl">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <Compass className="text-gold" size={24} />
            <div>
              <h3 className="text-white text-lg font-bold font-heading">
                Tactical Playstyle Comparison
              </h3>
              <p className="text-[11px] text-gray-light/70 mt-0.5">
                Generate similarity vectors and find historical matchup analogues
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-teal tracking-wider uppercase mb-1 font-heading">Home Team</span>
              <select
                value={homeTeam}
                onChange={(e) => setHomeTeam(e.target.value)}
                className="bg-black/40 border border-white/10 text-white font-heading font-bold text-sm px-4 py-2 rounded-xl focus:border-gold/50 focus:outline-none"
              >
                {teams.map((t) => (
                  <option key={t} value={t} disabled={t === awayTeam}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <span className="text-gray-light/30 font-black text-xs mt-5">VS</span>

            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-danger tracking-wider uppercase mb-1 font-heading">Away Team</span>
              <select
                value={awayTeam}
                onChange={(e) => setAwayTeam(e.target.value)}
                className="bg-black/40 border border-white/10 text-white font-heading font-bold text-sm px-4 py-2 rounded-xl focus:border-gold/50 focus:outline-none"
              >
                {teams.map((t) => (
                  <option key={t} value={t} disabled={t === homeTeam}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tactics Main Layout Grid ── */}
      {homeTeam === awayTeam ? (
        <div className="glass-panel rounded-2xl p-10 text-center border border-white/5">
          <p className="text-gray-light">Please select two different teams for comparison.</p>
        </div>
      ) : loading ? (
        <div className="glass-panel rounded-2xl p-20 text-center border border-white/5 flex flex-col items-center justify-center">
          <Loader2 className="text-gold animate-spin mb-3" size={32} />
          <span className="text-xs text-gray-light font-bold font-heading tracking-widest uppercase">
            Compiling Tactical Embeddings...
          </span>
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-6">
          
          {/* Left Column: Radar Chart Comparison */}
          <div className="glass-panel rounded-2xl border border-gold/15 p-6 flex flex-col gap-6">
            <div className="border-b border-white/5 pb-3 flex items-center gap-2">
              <Activity className="text-gold" size={16} />
              <h4 className="text-white text-sm font-bold font-heading tracking-wide uppercase">
                Tactical Radar Matrix
              </h4>
            </div>

            {/* Recharts Radar Chart */}
            <div className="h-[360px] w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={getRadarData()}>
                  <PolarGrid stroke="rgba(255,255,255,0.08)" />
                  <PolarAngleAxis
                    dataKey="attribute"
                    tick={{ fill: "rgba(255,255,255,0.7)", fontSize: 10, fontFamily: "Outfit, sans-serif" }}
                  />
                  <PolarRadiusAxis
                    angle={30}
                    domain={[0, 100]}
                    tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 8 }}
                  />
                  <Radar
                    name={homeTeam}
                    dataKey={homeTeam}
                    stroke="#0D9488"
                    fill="#0D9488"
                    fillOpacity={0.25}
                  />
                  <Radar
                    name={awayTeam}
                    dataKey={awayTeam}
                    stroke="#F43F5E"
                    fill="#F43F5E"
                    fillOpacity={0.25}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: "11px", fontFamily: "Outfit, sans-serif", paddingTop: "10px" }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Right Column: Briefing and Historical Analogues */}
          <div className="flex flex-col gap-6">
            
            {/* Tactical Intelligence Report Briefing */}
            <div className="glass-panel rounded-2xl border border-gold/15 p-6 flex flex-col gap-4 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-gold/5 rounded-full blur-2xl" />
              
              <div className="border-b border-white/5 pb-2 flex items-center gap-2">
                <Sparkles className="text-gold" size={16} />
                <h4 className="text-white text-xs font-bold font-heading tracking-wide uppercase">
                  Tactical Intelligence Report
                </h4>
              </div>
              <p className="text-white/80 text-xs leading-relaxed font-medium">
                {generateBriefing()}
              </p>
            </div>

            {/* Similar Historical Match Analogues */}
            <div className="glass-panel rounded-2xl border border-gold/15 p-6 flex flex-col gap-4 flex-grow">
              <div className="border-b border-white/5 pb-2 flex items-center gap-2">
                <History className="text-gold" size={16} />
                <h4 className="text-white text-xs font-bold font-heading tracking-wide uppercase">
                  Historical Match analogues (Vector Cosine Distance)
                </h4>
              </div>

              <div className="flex flex-col gap-3">
                {data.analogues.map((match, i) => (
                  <div
                    key={i}
                    className="flex flex-col gap-1.5 p-3.5 rounded-xl border border-white/5 bg-black/25 relative overflow-hidden"
                  >
                    <div className="flex justify-between items-center text-[10px] font-bold text-gray-light/50">
                      <span>{match.tournament}</span>
                      <span className="font-mono text-gold font-extrabold bg-gold/10 px-2 py-0.5 rounded">
                        {(match.similarity * 100).toFixed(1)}% match
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between text-xs mt-1">
                      <span className="text-white font-semibold">
                        {match.home} vs {match.away}
                      </span>
                      <span className="text-white font-heading font-black tracking-wider bg-white/5 border border-white/10 px-2 py-0.5 rounded">
                        {match.score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>
      ) : null}

    </div>
  );
}
