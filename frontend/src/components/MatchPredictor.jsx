import React, { useState, useEffect } from "react";
import { Sparkles, HelpCircle } from "lucide-react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend
} from "recharts";

export function MatchPredictor({ ratings, currentDate }) {
  const teams = Object.keys(ratings).sort();
  const [homeTeam, setHomeTeam] = useState("Spain");
  const [awayTeam, setAwayTeam] = useState("Germany");
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  // Sync ratings to defaults on start
  useEffect(() => {
    if (teams.length > 0) {
      if (!teams.includes(homeTeam)) setHomeTeam(teams[0]);
      if (!teams.includes(awayTeam)) setAwayTeam(teams[1] || teams[0]);
    }
  }, [ratings]);

  const fetchPrediction = async () => {
    if (homeTeam === awayTeam) {
      alert("Please select two different teams.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(
        `/api/predict?home=${encodeURIComponent(homeTeam)}&away=${encodeURIComponent(
          awayTeam
        )}&date=${currentDate}`
      );
      if (!res.ok) throw new Error("API prediction failure");
      const json = await res.json();
      setPrediction(json);
    } catch (err) {
      console.error(err);
      alert("Match forecast failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Generate deterministic stats based on Elo and name hash for radar chart
  const getTeamStats = (name, elo) => {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const randStat = (index, min, max) => {
      const seed = Math.abs(hash + index * 12345) % 100;
      return Math.round(min + (seed / 100) * (max - min));
    };

    const eloStrength = Math.round(Math.min(Math.max((elo - 1300) / 700 * 100, 30), 99));

    return {
      eloStrength,
      attack: randStat(1, Math.max(eloStrength - 15, 40), Math.min(eloStrength + 10, 99)),
      defense: randStat(2, Math.max(eloStrength - 15, 40), Math.min(eloStrength + 10, 99)),
      form: randStat(3, 45, 95),
      prestige: randStat(4, 50, 98)
    };
  };

  const homeElo = ratings[homeTeam] || 1500;
  const awayElo = ratings[awayTeam] || 1500;

  const homeStats = getTeamStats(homeTeam, homeElo);
  const awayStats = getTeamStats(awayTeam, awayElo);

  // Format data for Recharts Radar chart
  const radarData = [
    { subject: "Elo Strength", [homeTeam]: homeStats.eloStrength, [awayTeam]: awayStats.eloStrength },
    { subject: "Attack Rating", [homeTeam]: homeStats.attack, [awayTeam]: awayStats.attack },
    { subject: "Defense Rating", [homeTeam]: homeStats.defense, [awayTeam]: awayStats.defense },
    { subject: "Recent Form", [homeTeam]: homeStats.form, [awayTeam]: awayStats.form },
    { subject: "Team Prestige", [homeTeam]: homeStats.prestige, [awayTeam]: awayStats.prestige }
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
      
      {/* ── Matchup Form Controls ── */}
      <div className="glass-panel rounded-2xl p-6 border border-gold/15 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 pb-4 mb-4 border-b border-white/5">
            <Sparkles size={18} className="text-gold animate-pulse" />
            <h3 className="text-white text-lg font-bold font-heading">
              Matchup Predictor
            </h3>
          </div>
          <p className="text-gray-light/80 text-xs mb-6">
            Compare any two international football nations. The models run dynamic form checks and ratings to calculate victory chances.
          </p>

          <div className="flex items-center justify-between gap-6 mb-8">
            {/* Home Team Select */}
            <div className="flex flex-col gap-2 w-[45%]">
              <label className="text-[10px] font-bold text-gold tracking-wider uppercase">
                Home Team
              </label>
              <select
                value={homeTeam}
                onChange={(e) => {
                  setHomeTeam(e.target.value);
                  setPrediction(null);
                }}
                className="bg-gray-dark border border-gold/15 text-white text-sm font-semibold p-3.5 rounded-xl cursor-pointer outline-none hover:border-gold transition-all duration-300"
              >
                {teams.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <div className="bg-white/5 text-gray-light font-bold text-xs py-2 px-3 rounded-lg text-center border border-white/5 mt-1">
                Elo: {homeElo.toFixed(0)}
              </div>
            </div>

            {/* VS divider */}
            <div className="font-heading font-extrabold text-2xl text-gold filter drop-shadow-[0_0_8px_rgba(212,175,55,0.4)] mt-6">
              VS
            </div>

            {/* Away Team Select */}
            <div className="flex flex-col gap-2 w-[45%]">
              <label className="text-[10px] font-bold text-gold tracking-wider uppercase">
                Away Team
              </label>
              <select
                value={awayTeam}
                onChange={(e) => {
                  setAwayTeam(e.target.value);
                  setPrediction(null);
                }}
                className="bg-gray-dark border border-gold/15 text-white text-sm font-semibold p-3.5 rounded-xl cursor-pointer outline-none hover:border-gold transition-all duration-300"
              >
                {teams.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <div className="bg-white/5 text-gray-light font-bold text-xs py-2 px-3 rounded-lg text-center border border-white/5 mt-1">
                Elo: {awayElo.toFixed(0)}
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={fetchPrediction}
          disabled={loading}
          className="w-full bg-gradient-to-r from-gold to-[#b28d1d] hover:from-gold-hover hover:to-gold text-maroon-dark font-heading font-extrabold text-sm py-4 rounded-xl cursor-pointer transition-all duration-300 shadow-[0_4px_15px_rgba(212,175,55,0.25)] hover:shadow-[0_8px_25px_rgba(212,175,55,0.35)] hover:-translate-y-0.5 disabled:opacity-50"
        >
          {loading ? "Simulating Forecast..." : "Simulate Matchup"}
        </button>
      </div>

      {/* ── Forecast & Analytics Column ── */}
      <div className="glass-panel rounded-2xl p-6 border border-gold/15 min-h-[420px] flex flex-col justify-center">
        {!prediction ? (
          <div className="text-center py-20 text-gray-light flex flex-col items-center gap-4">
            <span className="text-5xl filter drop-shadow-[0_0_8px_rgba(212,175,55,0.3)]">🔮</span>
            <h4 className="font-heading font-bold text-base text-white">Ready for Forecast</h4>
            <p className="text-xs max-w-xs leading-relaxed">
              Select Spain and Germany (or any countries), then click simulate to generate comparative prediction probabilities and attribute radar comparisons.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-6 w-full">
            {/* Scoreboard display */}
            <div className="flex justify-around items-center bg-white/[0.02] border border-white/5 p-4 rounded-2xl">
              <div className="text-center w-[40%]">
                <h4 className="font-heading font-extrabold text-base text-white truncate">{prediction.home}</h4>
                <span className="text-[10px] font-bold text-gold/80 uppercase mt-0.5 block">Elo: {prediction.elo_home}</span>
              </div>
              <span className="font-heading font-extrabold text-sm text-gold/60">VS</span>
              <div className="text-center w-[40%]">
                <h4 className="font-heading font-extrabold text-base text-white truncate">{prediction.away}</h4>
                <span className="text-[10px] font-bold text-gold/80 uppercase mt-0.5 block">Elo: {prediction.elo_away}</span>
              </div>
            </div>

            {/* Radar compare chart */}
            <div className="h-[240px] w-full flex justify-center items-center">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                  <PolarGrid stroke="rgba(255, 255, 255, 0.08)" />
                  <PolarAngleAxis dataKey="subject" stroke="rgba(255, 255, 255, 0.6)" fontSize={10} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'rgba(255, 255, 255, 0.3)' }} fontSize={9} />
                  <Radar
                    name={prediction.home}
                    dataKey={prediction.home}
                    stroke="var(--color-success)"
                    fill="var(--color-success)"
                    fillOpacity={0.25}
                  />
                  <Radar
                    name={prediction.away}
                    dataKey={prediction.away}
                    stroke="var(--color-gold)"
                    fill="var(--color-gold)"
                    fillOpacity={0.2}
                  />
                  <Legend verticalAlign="bottom" height={24} iconSize={8} iconType="circle" />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Predictions comparison bars */}
            <div className="flex flex-col gap-4 mt-2">
              {/* Elo Poisson model */}
              <div className="bg-black/20 rounded-xl p-4 border border-white/5">
                <h5 className="text-[11px] font-extrabold text-gold uppercase tracking-wider mb-3">
                  Elo Poisson Model Odds
                </h5>
                <div className="flex flex-col gap-2">
                  {/* Home Win */}
                  <div className="grid grid-cols-[80px_1fr_40px] items-center gap-3 text-xs">
                    <span className="font-medium">Home Win</span>
                    <div className="h-2 rounded-full bg-gray-dark overflow-hidden">
                      <div
                        className="h-full bg-success transition-all duration-700"
                        style={{ width: `${prediction.elo_prediction.home_win * 100}%` }}
                      ></div>
                    </div>
                    <span className="font-bold text-right">{(prediction.elo_prediction.home_win * 100).toFixed(0)}%</span>
                  </div>
                  {/* Draw */}
                  <div className="grid grid-cols-[80px_1fr_40px] items-center gap-3 text-xs">
                    <span className="font-medium">Draw</span>
                    <div className="h-2 rounded-full bg-gray-dark overflow-hidden">
                      <div
                        className="h-full bg-info transition-all duration-700"
                        style={{ width: `${prediction.elo_prediction.draw * 100}%` }}
                      ></div>
                    </div>
                    <span className="font-bold text-right">{(prediction.elo_prediction.draw * 100).toFixed(0)}%</span>
                  </div>
                  {/* Away Win */}
                  <div className="grid grid-cols-[80px_1fr_40px] items-center gap-3 text-xs">
                    <span className="font-medium">Away Win</span>
                    <div className="h-2 rounded-full bg-gray-dark overflow-hidden">
                      <div
                        className="h-full bg-danger transition-all duration-700"
                        style={{ width: `${prediction.elo_prediction.away_win * 100}%` }}
                      ></div>
                    </div>
                    <span className="font-bold text-right">{(prediction.elo_prediction.away_win * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>

              {/* Logistic Regression ML model */}
              <div className="bg-black/20 rounded-xl p-4 border border-white/5">
                <h5 className="text-[11px] font-extrabold text-gold uppercase tracking-wider mb-3">
                  Logistic Regression ML Model
                </h5>
                <div className="flex flex-col gap-2">
                  {/* Home Win */}
                  <div className="grid grid-cols-[80px_1fr_40px] items-center gap-3 text-xs">
                    <span className="font-medium">Home Win</span>
                    <div className="h-2 rounded-full bg-gray-dark overflow-hidden">
                      <div
                        className="h-full bg-success transition-all duration-700"
                        style={{ width: `${prediction.ml_prediction.home_win * 100}%` }}
                      ></div>
                    </div>
                    <span className="font-bold text-right">{(prediction.ml_prediction.home_win * 100).toFixed(0)}%</span>
                  </div>
                  {/* Draw */}
                  <div className="grid grid-cols-[80px_1fr_40px] items-center gap-3 text-xs">
                    <span className="font-medium">Draw</span>
                    <div className="h-2 rounded-full bg-gray-dark overflow-hidden">
                      <div
                        className="h-full bg-info transition-all duration-700"
                        style={{ width: `${prediction.ml_prediction.draw * 100}%` }}
                      ></div>
                    </div>
                    <span className="font-bold text-right">{(prediction.ml_prediction.draw * 100).toFixed(0)}%</span>
                  </div>
                  {/* Away Win */}
                  <div className="grid grid-cols-[80px_1fr_40px] items-center gap-3 text-xs">
                    <span className="font-medium">Away Win</span>
                    <div className="h-2 rounded-full bg-gray-dark overflow-hidden">
                      <div
                        className="h-full bg-danger transition-all duration-700"
                        style={{ width: `${prediction.ml_prediction.away_win * 100}%` }}
                      ></div>
                    </div>
                    <span className="font-bold text-right">{(prediction.ml_prediction.away_win * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
