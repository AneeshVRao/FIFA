import React, { useState, useEffect, useRef } from "react";
import { Play, Pause, RotateCcw, Goal, Info, Target } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip
} from "recharts";

export function LiveMatchSimulator({ ratings, currentDate }) {
  const teams = Object.keys(ratings || {}).sort();
  
  // Roster selections
  const [homeTeam, setHomeTeam] = useState("Spain");
  const [awayTeam, setAwayTeam] = useState("Germany");

  // Core match stats
  const [time, setTime] = useState(0);
  const [goalsHome, setGoalsHome] = useState(0);
  const [goalsAway, setGoalsAway] = useState(0);
  const [xgHome, setXgHome] = useState(0.0);
  const [xgAway, setXgAway] = useState(0.0);
  const [redCardsHome, setRedCardsHome] = useState(0);
  const [redCardsAway, setRedCardsAway] = useState(0);

  // Simulation timer running state
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef(null);

  // Interactive Pitch coordinates
  const [shotX, setShotX] = useState(108.0);
  const [shotY, setShotY] = useState(40.0);
  const [isHeader, setIsHeader] = useState(false);
  const [underPressure, setUnderPressure] = useState(false);
  const [shotXg, setShotXg] = useState(0.76);
  const [shotTeam, setShotTeam] = useState("home");
  const [isGoal, setIsGoal] = useState(false);
  const [showPitchModal, setShowPitchModal] = useState(false);

  // Incidents feed & Graph history
  const [incidents, setIncidents] = useState([]);
  const [probHistory, setProbHistory] = useState([
    { minute: 0, homeWin: 0.40, draw: 0.30, awayWin: 0.30 }
  ]);

  // Current live win prediction state
  const [livePrediction, setLivePrediction] = useState({
    home_win: 0.40,
    draw: 0.30,
    away_win: 0.30
  });

  const svgRef = useRef(null);

  // Sync default team selections
  useEffect(() => {
    if (teams.length > 0) {
      if (!teams.includes(homeTeam)) setHomeTeam(teams[0]);
      if (!teams.includes(awayTeam)) setAwayTeam(teams[1] || teams[0]);
    }
  }, [ratings]);

  // Recalculate Live probabilities when core stats update
  useEffect(() => {
    fetchLivePrediction();
  }, [time, goalsHome, goalsAway, xgHome, xgAway, redCardsHome, redCardsAway, homeTeam, awayTeam]);

  // Handle live timer ticking
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setTime((prev) => {
          if (prev >= 90) {
            setIsPlaying(false);
            return 90;
          }
          return prev + 1;
        });
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying]);

  // Calculate coordinates xG on change
  useEffect(() => {
    if (showPitchModal) {
      fetchShotXG();
    }
  }, [shotX, shotY, isHeader, underPressure]);

  const fetchLivePrediction = async () => {
    try {
      const res = await fetch(
        `/api/predict/live?home=${encodeURIComponent(homeTeam)}&away=${encodeURIComponent(
          awayTeam
        )}&time=${time}&goals_home=${goalsHome}&goals_away=${goalsAway}&xg_home=${xgHome.toFixed(
          2
        )}&xg_away=${xgAway.toFixed(2)}&red_cards_home=${redCardsHome}&red_cards_away=${redCardsAway}&date=${currentDate}`
      );
      if (!res.ok) throw new Error("Live prediction error");
      const data = await res.json();
      
      const updatedPred = {
        home_win: data.live_prediction.home_win,
        draw: data.live_prediction.draw,
        away_win: data.live_prediction.away_win
      };
      
      setLivePrediction(updatedPred);

      // Keep graph history synchronized
      setProbHistory((prev) => {
        const filtered = prev.filter((p) => p.minute < time);
        return [
          ...filtered,
          {
            minute: time,
            homeWin: updatedPred.home_win,
            draw: updatedPred.draw,
            awayWin: updatedPred.away_win
          }
        ];
      });
    } catch (err) {
      console.error(err);
    }
  };

  const fetchShotXG = async () => {
    try {
      const res = await fetch(
        `/api/xg?x=${shotX}&y=${shotY}&is_header=${isHeader}&under_pressure=${underPressure}`
      );
      if (!res.ok) throw new Error("xG fetch failed");
      const json = await res.json();
      setShotXg(json.xg);
    } catch (err) {
      console.error(err);
    }
  };

  const handlePitchClick = (event) => {
    const svg = svgRef.current;
    if (!svg) return;

    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;

    const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());
    const newX = Math.min(Math.max(svgP.x, 60.0), 120.0);
    const newY = Math.min(Math.max(svgP.y, 0.0), 80.0);

    setShotX(parseFloat(newX.toFixed(1)));
    setShotY(parseFloat(newY.toFixed(1)));
  };

  const recordIncident = () => {
    if (isGoal) {
      if (shotTeam === "home") {
        setGoalsHome((g) => g + 1);
        setXgHome((x) => parseFloat((x + shotXg).toFixed(2)));
      } else {
        setGoalsAway((g) => g + 1);
        setXgAway((x) => parseFloat((x + shotXg).toFixed(2)));
      }
      setIncidents((prev) => [
        {
          minute: time,
          type: "goal",
          team: shotTeam,
          text: `GOAL! ${shotTeam === "home" ? homeTeam : awayTeam} scores! (xG: ${shotXg.toFixed(2)})`,
          xg: shotXg,
          x: shotX,
          y: shotY
        },
        ...prev
      ]);
    } else {
      if (shotTeam === "home") {
        setXgHome((x) => parseFloat((x + shotXg).toFixed(2)));
      } else {
        setXgAway((x) => parseFloat((x + shotXg).toFixed(2)));
      }
      setIncidents((prev) => [
        {
          minute: time,
          type: "shot",
          team: shotTeam,
          text: `Shot taken by ${shotTeam === "home" ? homeTeam : awayTeam} (xG: ${shotXg.toFixed(2)})`,
          xg: shotXg,
          x: shotX,
          y: shotY
        },
        ...prev
      ]);
    }

    setShowPitchModal(false);
    setIsGoal(false);
  };

  const addCard = (team, type) => {
    if (type === "red") {
      if (team === "home") setRedCardsHome((r) => Math.min(r + 1, 5));
      else setRedCardsAway((r) => Math.min(r + 1, 5));
    }
    setIncidents((prev) => [
      {
        minute: time,
        type: type === "red" ? "red_card" : "yellow_card",
        team: team,
        text: `${type === "red" ? "RED" : "YELLOW"} Card issued to ${
          team === "home" ? homeTeam : awayTeam
        }`
      },
      ...prev
    ]);
  };

  const resetSimulator = () => {
    setIsPlaying(false);
    setTime(0);
    setGoalsHome(0);
    setGoalsAway(0);
    setXgHome(0.0);
    setXgAway(0.0);
    setRedCardsHome(0);
    setRedCardsAway(0);
    setIncidents([]);
    setProbHistory([{ minute: 0, homeWin: 0.40, draw: 0.30, awayWin: 0.30 }]);
  };

  return (
    <div className="flex flex-col gap-6">
      
      {/* ── Match Scoreboard Header ── */}
      <div className="glass-panel rounded-2xl border border-gold/15 p-6 shadow-2xl relative overflow-hidden">
        {/* Background glow effects */}
        <div className="absolute top-0 left-1/4 w-40 h-20 bg-teal/10 rounded-full blur-3xl filter" />
        <div className="absolute top-0 right-1/4 w-40 h-20 bg-danger/10 rounded-full blur-3xl filter" />

        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] items-center gap-6 z-10 relative">
          
          {/* Home Team Details */}
          <div className="flex flex-col md:flex-row items-center justify-end gap-4 text-right">
            <div className="flex flex-col">
              <select
                value={homeTeam}
                onChange={(e) => {
                  setHomeTeam(e.target.value);
                  resetSimulator();
                }}
                className="bg-black/40 border border-white/10 text-white font-heading font-extrabold text-xl md:text-2xl px-4 py-2 rounded-xl focus:border-gold/50 focus:outline-none"
              >
                {teams.map((t) => (
                  <option key={t} value={t} disabled={t === awayTeam}>
                    {t}
                  </option>
                ))}
              </select>
              <div className="flex justify-end gap-3 mt-1 text-[10px] font-bold text-gray-light/60 tracking-wider">
                <span>ELO: {ratings[homeTeam]?.toFixed(0)}</span>
                <span>•</span>
                <span>xG: {xgHome.toFixed(2)}</span>
                {redCardsHome > 0 && (
                  <span className="flex items-center gap-1 text-danger font-extrabold">
                    <span className="w-2 h-3 bg-red-600 rounded-[2px]" /> {redCardsHome} RC
                  </span>
                )}
              </div>
            </div>
            <div className="w-14 h-14 rounded-full bg-teal-600/20 border-2 border-teal flex items-center justify-center font-heading text-lg font-black text-teal">
              {homeTeam.substring(0, 3).toUpperCase()}
            </div>
          </div>

          {/* Central Scoreboard Chronometer */}
          <div className="flex flex-col items-center">
            <div className="bg-black/50 border border-white/10 px-8 py-3 rounded-2xl flex items-center justify-center gap-6 shadow-[inset_0_2px_10px_rgba(0,0,0,0.6)]">
              <span className="text-4xl md:text-5xl font-heading font-black text-white font-numeric tracking-tight w-12 text-center">
                {goalsHome}
              </span>
              <span className="text-gray-light/40 text-2xl font-bold font-heading">:</span>
              <span className="text-4xl md:text-5xl font-heading font-black text-white font-numeric tracking-tight w-12 text-center">
                {goalsAway}
              </span>
            </div>
            
            <div className="mt-2.5 flex items-center gap-3">
              <span className="text-gold font-mono font-extrabold text-sm tracking-widest bg-gold/10 px-3 py-1 rounded-full border border-gold/15">
                {time === 90 ? "FT" : `${time.toString().padStart(2, "0")}:00`}
              </span>
              {time < 90 && (
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className={`p-1.5 rounded-full border text-white transition-all cursor-pointer ${
                    isPlaying 
                      ? "bg-amber-600/20 border-amber-500 hover:bg-amber-500/20 active:scale-95" 
                      : "bg-teal-600/20 border-teal hover:bg-teal-500/20 active:scale-95"
                  }`}
                >
                  {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                </button>
              )}
              <button
                onClick={resetSimulator}
                title="Reset Simulation"
                className="p-1.5 bg-white/5 border border-white/10 rounded-full hover:bg-white/10 text-gray-light hover:text-white transition-all cursor-pointer active:scale-95"
              >
                <RotateCcw size={14} />
              </button>
            </div>
          </div>

          {/* Away Team Details */}
          <div className="flex flex-col md:flex-row-reverse items-center justify-end gap-4 text-left">
            <div className="flex flex-col">
              <select
                value={awayTeam}
                onChange={(e) => {
                  setAwayTeam(e.target.value);
                  resetSimulator();
                }}
                className="bg-black/40 border border-white/10 text-white font-heading font-extrabold text-xl md:text-2xl px-4 py-2 rounded-xl focus:border-gold/50 focus:outline-none"
              >
                {teams.map((t) => (
                  <option key={t} value={t} disabled={t === homeTeam}>
                    {t}
                  </option>
                ))}
              </select>
              <div className="flex justify-start gap-3 mt-1 text-[10px] font-bold text-gray-light/60 tracking-wider">
                <span>ELO: {ratings[awayTeam]?.toFixed(0)}</span>
                <span>•</span>
                <span>xG: {xgAway.toFixed(2)}</span>
                {redCardsAway > 0 && (
                  <span className="flex items-center gap-1 text-danger font-extrabold">
                    <span className="w-2 h-3 bg-red-600 rounded-[2px]" /> {redCardsAway} RC
                  </span>
                )}
              </div>
            </div>
            <div className="w-14 h-14 rounded-full bg-danger-600/20 border-2 border-danger flex items-center justify-center font-heading text-lg font-black text-danger">
              {awayTeam.substring(0, 3).toUpperCase()}
            </div>
          </div>

        </div>

        {/* Timeline Progress Slider */}
        <div className="mt-6 flex items-center gap-4">
          <span className="text-[10px] font-bold tracking-wider text-gray-light/50 font-heading">MIN 0</span>
          <input
            type="range"
            min="0"
            max="90"
            value={time}
            onChange={(e) => setTime(parseInt(e.target.value))}
            className="flex-grow accent-gold h-1.5 bg-black/40 border border-white/10 rounded-lg cursor-pointer"
          />
          <span className="text-[10px] font-bold tracking-wider text-gray-light/50 font-heading">MIN 90</span>
        </div>
      </div>

      {/* ── Simulation Live Actions Dashboard ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-6">
        
        {/* Left Column: Win Probability Plots */}
        <div className="flex flex-col gap-6">
          
          {/* Bayesian win probability dial details */}
          <div className="glass-panel rounded-2xl border border-gold/15 p-6 flex flex-col gap-4">
            <div className="border-b border-white/5 pb-3">
              <h4 className="text-white text-sm font-bold font-heading tracking-wide uppercase">
                Dynamic Win Probability Forecast
              </h4>
            </div>
            
            {/* Visual Arc dial */}
            <div className="flex items-center justify-center py-2">
              <div className="w-full max-w-[420px] bg-black/30 border border-white/5 rounded-2xl p-4 flex flex-col items-center shadow-[inset_0_2px_10px_rgba(0,0,0,0.4)]">
                {/* Horizontal probability ribbon slider bar */}
                <div className="w-full h-4 rounded-full flex overflow-hidden border border-white/10">
                  <div
                    style={{ width: `${livePrediction.home_win * 100}%` }}
                    className="bg-teal transition-all duration-500 ease-out"
                  />
                  <div
                    style={{ width: `${livePrediction.draw * 100}%` }}
                    className="bg-slate-500 transition-all duration-500 ease-out"
                  />
                  <div
                    style={{ width: `${livePrediction.away_win * 100}%` }}
                    className="bg-danger transition-all duration-500 ease-out"
                  />
                </div>

                <div className="grid grid-cols-3 w-full mt-4 text-center">
                  <div className="flex flex-col">
                    <span className="text-teal font-heading font-black text-xl md:text-2xl font-numeric">
                      {(livePrediction.home_win * 100).toFixed(1)}%
                    </span>
                    <span className="text-[10px] font-bold text-gray-light/60 uppercase tracking-wider mt-0.5">
                      {homeTeam} Win
                    </span>
                  </div>
                  <div className="flex flex-col border-x border-white/5">
                    <span className="text-slate-400 font-heading font-black text-xl md:text-2xl font-numeric">
                      {(livePrediction.draw * 100).toFixed(1)}%
                    </span>
                    <span className="text-[10px] font-bold text-gray-light/60 uppercase tracking-wider mt-0.5">
                      Draw Odds
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-danger font-heading font-black text-xl md:text-2xl font-numeric">
                      {(livePrediction.away_win * 100).toFixed(1)}%
                    </span>
                    <span className="text-[10px] font-bold text-gray-light/60 uppercase tracking-wider mt-0.5">
                      {awayTeam} Win
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Probability timeline area chart */}
            <div className="h-[220px] w-full mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={probHistory} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <XAxis
                    dataKey="minute"
                    stroke="rgba(255,255,255,0.4)"
                    fontSize={10}
                    fontFamily="Outfit, sans-serif"
                    tickFormatter={(v) => `${v}'`}
                  />
                  <YAxis
                    stroke="rgba(255,255,255,0.4)"
                    fontSize={10}
                    fontFamily="Outfit, sans-serif"
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    domain={[0, 1]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(10, 5, 5, 0.95)",
                      border: "1px solid rgba(212, 175, 55, 0.25)",
                      borderRadius: "12px",
                      fontSize: "11px",
                      fontFamily: "Outfit, sans-serif"
                    }}
                    formatter={(val) => [`${(val * 100).toFixed(1)}%`]}
                    labelFormatter={(label) => `Minute: ${label}'`}
                  />
                  <Area
                    type="monotone"
                    name={`${homeTeam} P(W)`}
                    dataKey="homeWin"
                    stackId="1"
                    stroke="#0D9488"
                    fill="rgba(13, 148, 136, 0.35)"
                  />
                  <Area
                    type="monotone"
                    name="P(Draw)"
                    dataKey="draw"
                    stackId="1"
                    stroke="#64748B"
                    fill="rgba(100, 116, 139, 0.2)"
                  />
                  <Area
                    type="monotone"
                    name={`${awayTeam} P(W)`}
                    dataKey="awayWin"
                    stackId="1"
                    stroke="#F43F5E"
                    fill="rgba(244, 63, 94, 0.35)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          
        </div>

        {/* Right Column: Actions and Event Stream Log */}
        <div className="flex flex-col gap-6">
          
          {/* Simulator quick incident controller actions */}
          <div className="glass-panel rounded-2xl border border-gold/15 p-6 flex flex-col gap-4">
            <div className="border-b border-white/5 pb-3">
              <h4 className="text-white text-sm font-bold font-heading tracking-wide uppercase">
                Simulated Match Incidents
              </h4>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  setShotTeam("home");
                  setIsGoal(false);
                  setShowPitchModal(true);
                }}
                className="py-3 px-4 rounded-xl border border-white/10 bg-white/5 text-xs font-bold text-teal hover:bg-teal-500/10 hover:border-teal/50 transition-all flex items-center justify-center gap-2 cursor-pointer btn-tactile"
              >
                <Target size={14} /> Add {homeTeam} Shot
              </button>
              <button
                onClick={() => {
                  setShotTeam("away");
                  setIsGoal(false);
                  setShowPitchModal(true);
                }}
                className="py-3 px-4 rounded-xl border border-white/10 bg-white/5 text-xs font-bold text-danger hover:bg-danger-500/10 hover:border-danger/50 transition-all flex items-center justify-center gap-2 cursor-pointer btn-tactile"
              >
                <Target size={14} /> Add {awayTeam} Shot
              </button>
              
              <button
                onClick={() => addCard("home", "red")}
                className="py-3 px-4 rounded-xl border border-white/10 bg-white/5 text-xs font-bold text-teal hover:bg-red-500/10 hover:border-red-500/50 transition-all flex items-center justify-center gap-2 cursor-pointer btn-tactile"
              >
                <span className="w-2.5 h-3.5 bg-red-600 rounded-[2px]" /> Red Card {homeTeam}
              </button>
              <button
                onClick={() => addCard("away", "red")}
                className="py-3 px-4 rounded-xl border border-white/10 bg-white/5 text-xs font-bold text-danger hover:bg-red-500/10 hover:border-red-500/50 transition-all flex items-center justify-center gap-2 cursor-pointer btn-tactile"
              >
                <span className="w-2.5 h-3.5 bg-red-600 rounded-[2px]" /> Red Card {awayTeam}
              </button>
            </div>
          </div>

          {/* Incidents timeline logger feed */}
          <div className="glass-panel rounded-2xl border border-gold/15 p-6 flex flex-col gap-4 flex-grow max-h-[300px] overflow-hidden">
            <div className="border-b border-white/5 pb-2">
              <h4 className="text-white text-xs font-bold font-heading tracking-wide uppercase">
                Match Timeline Stream
              </h4>
            </div>

            <div className="flex-grow overflow-y-auto pr-2 flex flex-col gap-3">
              {incidents.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-10">
                  <Info size={24} className="text-gray-light/35 mb-2" />
                  <p className="text-xs text-gray-light/60">No match incidents recorded yet.</p>
                  <p className="text-[10px] text-gray-light/40 mt-0.5">Use actions above to simulate shots or red cards.</p>
                </div>
              ) : (
                incidents.map((inc, i) => (
                  <div
                    key={i}
                    className={`flex items-center gap-3 p-3 rounded-xl border bg-black/25 text-xs ${
                      inc.type === "goal"
                        ? "border-gold/30 shadow-[inset_0_1px_5px_rgba(212,175,55,0.05)]"
                        : "border-white/5"
                    }`}
                  >
                    <span className="font-mono font-extrabold text-gold bg-gold/10 px-2 py-0.5 rounded text-[10px]">
                      {inc.minute}'
                    </span>
                    {inc.type === "goal" && <Goal size={14} className="text-gold" />}
                    {inc.type === "red_card" && (
                      <span className="w-2.5 h-3.5 bg-red-600 rounded-[2px] inline-block" />
                    )}
                    <span className="text-white/90 flex-grow font-medium leading-normal">{inc.text}</span>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </div>

      {/* ── SVG Pitch Shot Plotter Dialog Modal ── */}
      {showPitchModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel border-2 border-gold/25 rounded-2xl w-full max-w-2xl overflow-hidden shadow-[0_10px_50px_rgba(0,0,0,0.8)] animate-scale-in">
            
            <div className="p-5 border-b border-white/5 flex items-center justify-between">
              <h3 className="text-white font-heading font-extrabold text-lg flex items-center gap-2">
                <Target size={18} className="text-gold" /> Shot Plotter Pitch Map
              </h3>
              <button
                onClick={() => setShowPitchModal(false)}
                className="text-gray-light hover:text-white font-bold text-sm cursor-pointer p-1"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-6 flex flex-col gap-6">
              
              {/* Isometric 3D Pitch canvas for coordinate plotting */}
              <div 
                className="bg-gradient-to-br from-[#0a180e] to-[#112d18] border border-white/10 rounded-xl p-4 flex justify-center items-center overflow-hidden"
                style={{ perspective: "1000px" }}
              >
                <svg
                  ref={svgRef}
                  onClick={handlePitchClick}
                  viewBox="60 0 60 80"
                  className="w-full max-h-[300px] cursor-crosshair origin-center transform"
                  style={{
                    transform: "rotateX(20deg)",
                    transformStyle: "preserve-3d"
                  }}
                >
                  <rect x="60" y="0" width="60" height="80" fill="transparent" />
                  
                  {/* Stripes */}
                  {[60, 70, 80, 90, 100, 110].map((lx, idx) => (
                    <rect
                      key={lx}
                      x={lx}
                      y={0}
                      width="10"
                      height="80"
                      fill={idx % 2 === 0 ? "rgba(255, 255, 255, 0.015)" : "transparent"}
                    />
                  ))}

                  {/* Lines */}
                  <line x1="60" y1="0" x2="60" y2="80" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />
                  <line x1="60" y1="40" x2="120" y2="40" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />
                  <rect x="102" y="18" width="18" height="44" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />
                  <rect x="114" y="30" width="6" height="20" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />
                  <circle cx="108" cy="40" r="0.6" fill="rgba(255,255,255,0.8)" />
                  <path d="M 102 33 A 10 10 0 0 0 102 47" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />

                  {/* Goal frame */}
                  <line x1="120" y1="36" x2="120" y2="44" stroke="var(--color-gold)" strokeWidth="1" />

                  {/* Ball Marker */}
                  <circle
                    cx={shotX}
                    cy={shotY}
                    r="1.6"
                    className="fill-gold stroke-white stroke-[0.6px] filter drop-shadow-[0_0_6px_var(--color-gold)]"
                  />
                </svg>
              </div>

              {/* Coordinates readouts and options selectors */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-black/40 border border-white/5 p-3 rounded-xl flex flex-col text-center">
                  <span className="text-[9px] font-bold text-gray-light/60 uppercase tracking-wider">Coordinates</span>
                  <span className="text-white font-extrabold text-sm mt-1">X: {shotX.toFixed(1)}m, Y: {shotY.toFixed(1)}m</span>
                </div>
                
                <div className="bg-black/40 border border-white/5 p-3 rounded-xl flex flex-col text-center">
                  <span className="text-[9px] font-bold text-gray-light/60 uppercase tracking-wider">Expected Goals</span>
                  <span className="text-gold font-extrabold text-sm mt-1">{shotXg.toFixed(3)}</span>
                </div>

                <div className="flex flex-col gap-1 justify-center">
                  <label className="text-[9px] font-bold text-gray-light/60 uppercase tracking-wider">Body Part</label>
                  <div className="flex gap-1">
                    <button
                      onClick={() => setIsHeader(false)}
                      className={`flex-grow py-1.5 px-2 rounded-lg text-[10px] font-bold cursor-pointer transition-all border ${
                        !isHeader ? "bg-gold text-black border-gold" : "bg-black/40 border-white/5 text-gray-light"
                      }`}
                    >
                      Foot
                    </button>
                    <button
                      onClick={() => setIsHeader(true)}
                      className={`flex-grow py-1.5 px-2 rounded-lg text-[10px] font-bold cursor-pointer transition-all border ${
                        isHeader ? "bg-gold text-black border-gold" : "bg-black/40 border-white/5 text-gray-light"
                      }`}
                    >
                      Head
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-1 justify-center">
                  <label className="text-[9px] font-bold text-gray-light/60 uppercase tracking-wider">Pressure</label>
                  <div className="flex gap-1">
                    <button
                      onClick={() => setUnderPressure(false)}
                      className={`flex-grow py-1.5 px-2 rounded-lg text-[10px] font-bold cursor-pointer transition-all border ${
                        !underPressure ? "bg-gold text-black border-gold" : "bg-black/40 border-white/5 text-gray-light"
                      }`}
                    >
                      Off
                    </button>
                    <button
                      onClick={() => setUnderPressure(true)}
                      className={`flex-grow py-1.5 px-2 rounded-lg text-[10px] font-bold cursor-pointer transition-all border ${
                        underPressure ? "bg-gold text-black border-gold" : "bg-black/40 border-white/5 text-gray-light"
                      }`}
                    >
                      On
                    </button>
                  </div>
                </div>
              </div>

              {/* Goal Outcome option and record actions */}
              <div className="border-t border-white/5 pt-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <label className="text-xs font-bold text-gray-light/80 cursor-pointer flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={isGoal}
                      onChange={(e) => setIsGoal(e.target.checked)}
                      className="w-4.5 h-4.5 rounded border-white/10 accent-gold bg-black/40 cursor-pointer"
                    />
                    Mark shot as a scored goal event
                  </label>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => setShowPitchModal(false)}
                    className="py-2.5 px-5 bg-white/5 border border-white/10 rounded-xl text-xs text-white hover:bg-white/10 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={recordIncident}
                    className="py-2.5 px-5 bg-gold text-black font-extrabold rounded-xl text-xs hover:bg-yellow-500 cursor-pointer transition-all active:scale-[0.98] shadow-[0_0_10px_rgba(212,175,55,0.3)]"
                  >
                    Confirm & Record Shot
                  </button>
                </div>
              </div>

            </div>

          </div>
        </div>
      )}

    </div>
  );
}
