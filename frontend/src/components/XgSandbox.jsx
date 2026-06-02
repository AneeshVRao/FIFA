import React, { useState, useEffect, useRef } from "react";
import { Sparkles, Target, Compass, Eye, ShieldAlert, Cpu } from "lucide-react";

export function XgSandbox() {
  const [x, setX] = useState(108.0);
  const [y, setY] = useState(40.0);
  const [isHeader, setIsHeader] = useState(false);
  const [underPressure, setUnderPressure] = useState(false);
  const [xg, setXg] = useState(0.76);
  const [xgBaseline, setXgBaseline] = useState(0.76);
  const [loading, setLoading] = useState(false);

  // New Expected Threat (xT) Heatmap State
  const [showXtHeatmap, setShowXtHeatmap] = useState(false);
  const [xtHeatmap, setXtHeatmap] = useState(null);
  const [hoveredCell, setHoveredCell] = useState(null);

  // New Pass Completion Probability (xP) State
  const [activeTab, setActiveTab] = useState("xg"); // "xg" or "xp"
  const [passStart, setPassStart] = useState(null);
  const [passEnd, setPassEnd] = useState(null);
  const [hoverPos, setHoverPos] = useState(null);
  const [xpValue, setXpValue] = useState(null);
  const [xpLoading, setXpLoading] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  const svgRef = useRef(null);

  // Check prefers-reduced-motion
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mediaQuery.matches);
    const listener = (e) => setReducedMotion(e.matches);
    mediaQuery.addEventListener("change", listener);
    return () => mediaQuery.removeEventListener("change", listener);
  }, []);

  // Fetch xG when coordinate parameters change
  useEffect(() => {
    if (activeTab === "xg") {
      fetchXG();
    }
  }, [x, y, isHeader, underPressure, activeTab]);

  // Fetch xT heatmap on mount
  useEffect(() => {
    fetchXtHeatmap();
  }, []);

  const fetchXG = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `/api/xg?x=${x}&y=${y}&is_header=${isHeader}&under_pressure=${underPressure}`
      );
      if (!res.ok) throw new Error("xG API error");
      const json = await res.json();
      setXg(json.xg);
      setXgBaseline(json.xg_baseline || json.xg);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchXtHeatmap = async () => {
    try {
      const res = await fetch("/api/xt/heatmap");
      if (!res.ok) throw new Error("xT Heatmap fetch error");
      const json = await res.json();
      setXtHeatmap(json.heatmap);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchXP = async (start, end) => {
    setXpLoading(true);
    try {
      const res = await fetch(
        `/api/xp?x_start=${start.x}&y_start=${start.y}&x_end=${end.x}&y_end=${end.y}&is_header=${isHeader ? 1 : 0}&under_pressure=${underPressure ? 1 : 0}`
      );
      if (!res.ok) throw new Error("xP API error");
      const json = await res.json();
      setXpValue(json.probability);
    } catch (err) {
      console.error(err);
    } finally {
      setXpLoading(false);
    }
  };

  const getCoordinatesFromEvent = (event) => {
    const svg = svgRef.current;
    if (!svg) return null;

    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;

    const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

    // Attacking half is (60 to 120x, 0 to 80y)
    const newX = Math.min(Math.max(svgP.x, 60.0), 120.0);
    const newY = Math.min(Math.max(svgP.y, 0.0), 80.0);
    return { x: parseFloat(newX.toFixed(1)), y: parseFloat(newY.toFixed(1)) };
  };

  const handlePitchClick = (event) => {
    const coords = getCoordinatesFromEvent(event);
    if (!coords) return;

    if (activeTab === "xg") {
      setX(coords.x);
      setY(coords.y);
    } else {
      if (!passStart || (passStart && passEnd)) {
        setPassStart(coords);
        setPassEnd(null);
        setXpValue(null);
      } else {
        setPassEnd(coords);
        fetchXP(passStart, coords);
      }
    }
  };

  const handlePitchMouseMove = (event) => {
    if (activeTab !== "xp" || !passStart || passEnd) return;
    const coords = getCoordinatesFromEvent(event);
    if (coords) {
      setHoverPos(coords);
    }
  };

  // Radial Gauge Calculations
  const radius = 55;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  
  // Calculate display value
  const displayVal = activeTab === "xg" ? xg : (xpValue !== null ? xpValue : 0.0);
  const strokeDashoffset = circumference - displayVal * circumference;

  const getInterpretation = (val) => {
    if (activeTab === "xg") {
      if (val >= 0.70) return "Championship Penalty Grade. Typical penalty kick conversion rate.";
      if (val >= 0.35) return "High-quality opportunity. Clean target access inside the goal box.";
      if (val >= 0.15) return "Moderate chance. Average conversion rate for box scrambles.";
      if (val >= 0.05) return "Low chance. Standard distance header or pressured wide-angle shot.";
      return "Speculative try. Minimal scoring probability from this range.";
    } else {
      if (val >= 0.85) return "Highly reliable link. Excellent completion chance over safe space.";
      if (val >= 0.70) return "Solid pass. Good link opportunity with moderate distance.";
      if (val >= 0.50) return "Contested attempt. Risky pass option under pressure or length.";
      if (val >= 0.25) return "Low completion odds. Speculative long ball or crowded target area.";
      return "Highly speculative target. High probability of interception or loss of possession.";
    }
  };

  const resetPass = () => {
    setPassStart(null);
    setPassEnd(null);
    setXpValue(null);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-6 mt-6">
      
      {/* ── Attacking 3D Soccer Pitch Column ── */}
      <div 
        className="glass-panel rounded-3xl p-6 border border-gold/15 flex flex-col gap-4 shadow-[0_20px_40px_rgba(0,0,0,0.25)] transition-all duration-300 backdrop-blur-2xl bg-white/5"
        style={{ willChange: "transform" }}
      >
        <div className="flex justify-between items-center pb-2 border-b border-white/5">
          <div>
            <h3 className="text-white text-lg font-bold font-heading">
              {activeTab === "xg" ? "Expected Goals (xG) Plotter" : "Expected Pass (xP) Vector Simulator"}
            </h3>
            <p className="text-gray-light/80 text-xs mt-1">
              {activeTab === "xg" 
                ? "Click on the 3D isometric pitch below to change the shot location." 
                : "Click start coordinate, then click target coordinate to draw a pass vector."}
            </p>
          </div>

          {/* Expected Threat (xT) Toggle Switch */}
          <button
            onClick={() => setShowXtHeatmap(!showXtHeatmap)}
            className={`px-3 py-1.5 rounded-xl border text-[10px] font-bold font-heading cursor-pointer flex items-center gap-1.5 transition-all duration-300 ${
              showXtHeatmap
                ? "bg-rose-500/20 border-rose-500 text-rose-400"
                : "bg-white/5 border-white/10 text-gray-light hover:text-white"
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            xT Heatmap Grid
          </button>
        </div>

        {/* 3D Perspective Wrapper */}
        <div 
          className="bg-gradient-to-br from-[#0a180e] to-[#112d18] border-2 border-gold/10 rounded-2xl p-6 flex justify-center items-center overflow-hidden shadow-[inset_0_0_24px_rgba(0,0,0,0.8)] relative"
          style={{ perspective: "1000px" }}
        >
          <svg
            ref={svgRef}
            onClick={handlePitchClick}
            onMouseMove={handlePitchMouseMove}
            viewBox="60 0 60 80"
            className="w-full max-h-[350px] cursor-crosshair origin-center transform transition-transform duration-500 hover:scale-[1.01]"
            style={{
              transform: "rotateX(22deg)",
              transformStyle: "preserve-3d"
            }}
          >
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="6"
                refY="5"
                markerWidth="3"
                markerHeight="3"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--color-gold)" />
              </marker>
            </defs>

            {/* Field Turf */}
            <rect x="60" y="0" width="60" height="80" fill="transparent" />

            {/* Grid Turf Lanes (aesthetic stripes) */}
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

            {/* Pitch Markings */}
            <line x1="60" y1="0" x2="60" y2="80" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />
            <line x1="60" y1="40" x2="120" y2="40" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />
            
            {/* Penalty Area */}
            <rect x="102" y="18" width="18" height="44" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />
            
            {/* Goal Box */}
            <rect x="114" y="30" width="6" height="20" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />
            
            {/* Penalty Spot (x=108, y=40) */}
            <circle cx="108" cy="40" r="0.6" fill="rgba(255,255,255,0.8)" />
            
            {/* Penalty Arc */}
            <path d="M 102 33 A 10 10 0 0 0 102 47" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.3" />

            {/* Attacking Goal Post frame */}
            <line x1="120" y1="36" x2="120" y2="44" stroke="var(--color-gold)" strokeWidth="1" />

            {/* ── Expected Threat (xT) Heatmap Overlay ── */}
            {showXtHeatmap && xtHeatmap && (
              <g className="transition-opacity duration-300" style={{ pointerEvents: "auto" }}>
                {xtHeatmap.map((row, cx) => {
                  if (cx < 6) return null;
                  return row.map((val, cy) => {
                    const rectX = cx * 10;
                    const rectY = cy * 10;
                    // Scale values representing visual opacity
                    const opacity = Math.min(0.65, (val / 0.4) * 0.5 + 0.1);
                    const isCellHovered = hoveredCell && hoveredCell.cx === cx && hoveredCell.cy === cy;
                    return (
                      <rect
                        key={`${cx}-${cy}`}
                        x={rectX}
                        y={rectY}
                        width="10"
                        height="10"
                        fill="#F43F5E"
                        opacity={opacity}
                        stroke={isCellHovered ? "var(--color-gold)" : "rgba(255,255,255,0.06)"}
                        strokeWidth={isCellHovered ? "0.6" : "0.15"}
                        className="transition-all cursor-help"
                        onMouseEnter={() => setHoveredCell({ cx, cy, val })}
                        onMouseLeave={() => setHoveredCell(null)}
                      />
                    );
                  });
                })}
              </g>
            )}

            {/* ── xG Shot Ball Marker ── */}
            {activeTab === "xg" && (
              <circle
                cx={x}
                cy={y}
                r="1.6"
                className="fill-gold stroke-white stroke-[0.6px] pulse filter drop-shadow-[0_0_6px_var(--color-gold)]"
              />
            )}

            {/* ── xP Pass Vector Graphics ── */}
            {activeTab === "xp" && passStart && (
              <g>
                {/* Pass Start Coordinates */}
                <circle 
                  cx={passStart.x} 
                  cy={passStart.y} 
                  r="1.2" 
                  fill="rgba(13,148,136,0.3)" 
                  stroke="#0D9488" 
                  strokeWidth="0.4" 
                />
                
                {/* Dotted vector or resolved solid vector with arrow */}
                {passEnd ? (
                  <>
                    <line
                      x1={passStart.x}
                      y1={passStart.y}
                      x2={passEnd.x}
                      y2={passEnd.y}
                      stroke="var(--color-gold)"
                      strokeWidth="0.8"
                      markerEnd="url(#arrow)"
                    />
                    <circle 
                      cx={passEnd.x} 
                      cy={passEnd.y} 
                      r="1.2" 
                      fill="rgba(244,63,94,0.3)" 
                      stroke="#F43F5E" 
                      strokeWidth="0.4" 
                    />
                  </>
                ) : hoverPos ? (
                  <line
                    x1={passStart.x}
                    y1={passStart.y}
                    x2={hoverPos.x}
                    y2={hoverPos.y}
                    stroke="var(--color-gold)"
                    strokeWidth="0.6"
                    strokeDasharray="2,2"
                  />
                ) : null}
              </g>
            )}
          </svg>
        </div>

        {/* Heatmap Tooltip Readout */}
        <div className="flex justify-between items-center text-xs px-4 py-2.5 bg-black/30 border border-white/5 rounded-xl min-h-[36px]">
          {hoveredCell ? (
            <span className="text-white font-bold flex items-center gap-1.5 animate-fadeIn">
              <Eye className="w-3.5 h-3.5 text-gold" />
              Grid Zone ({hoveredCell.cx}, {hoveredCell.cy}) | Expected Threat: <strong className="text-gold">{(hoveredCell.val * 100).toFixed(2)}%</strong>
            </span>
          ) : (
            <span className="text-gray-light/60 text-[11px] flex items-center gap-1">
              <Cpu className="w-3.5 h-3.5 text-gold/60" />
              {showXtHeatmap ? "Hover over any grid square to analyze positional possession threat." : "Click switch to overlay Expected Threat (xT) heat grid."}
            </span>
          )}
        </div>
      </div>

      {/* ── Controls & Circular Gauge Column ── */}
      <div 
        className="glass-panel rounded-3xl p-6 border border-gold/15 flex flex-col justify-between shadow-[0_20px_40px_rgba(0,0,0,0.25)] transition-all duration-300 backdrop-blur-2xl bg-white/5"
        style={{ willChange: "transform" }}
      >
        <div className="flex flex-col gap-5">
          {/* Tab Selector */}
          <div className="flex gap-2 p-1 bg-black/35 border border-white/5 rounded-2xl">
            <button
              onClick={() => setActiveTab("xg")}
              className={`flex-grow py-2.5 px-4 rounded-xl text-xs font-extrabold font-heading cursor-pointer transition-all duration-300 ${
                activeTab === "xg"
                  ? "bg-gold text-maroon-dark font-black"
                  : "text-gray-light hover:text-white"
              }`}
            >
              Shot Plotter (xG)
            </button>
            <button
              onClick={() => setActiveTab("xp")}
              className={`flex-grow py-2.5 px-4 rounded-xl text-xs font-extrabold font-heading cursor-pointer transition-all duration-300 ${
                activeTab === "xp"
                  ? "bg-gold text-maroon-dark font-black"
                  : "text-gray-light hover:text-white"
              }`}
            >
              Pass Simulator (xP)
            </button>
          </div>

          {/* Tab 1: Shot Plotter Coordinates */}
          {activeTab === "xg" && (
            <div className="flex flex-col gap-2">
              <span className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
                Shot Coordinates
              </span>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-dark border border-white/5 px-4 py-3 rounded-xl text-center font-extrabold text-sm text-white">
                  X: {x.toFixed(1)}m
                </div>
                <div className="bg-gray-dark border border-white/5 px-4 py-3 rounded-xl text-center font-extrabold text-sm text-white">
                  Y: {y.toFixed(1)}m
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Pass Simulator Coordinates */}
          {activeTab === "xp" && (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">Pass Coordinates</span>
                  {passStart && (
                    <button onClick={resetPass} className="text-[10px] font-extrabold text-red-400 hover:text-red-300 cursor-pointer">
                      Reset Vector
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-dark border border-white/5 px-3 py-2 rounded-xl text-center text-xs text-white">
                    <span className="block text-[8px] text-white/40 uppercase">Start</span>
                    {passStart ? `X: ${passStart.x}, Y: ${passStart.y}` : "Click Pitch"}
                  </div>
                  <div className="bg-gray-dark border border-white/5 px-3 py-2 rounded-xl text-center text-xs text-white">
                    <span className="block text-[8px] text-white/40 uppercase">Target</span>
                    {passEnd ? `X: ${passEnd.x}, Y: ${passEnd.y}` : "Click Target"}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Body Part Selection */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
              Action Execution Style
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setIsHeader(false)}
                className={`flex-grow py-3 px-4 rounded-xl text-xs font-bold font-heading cursor-pointer transition-all duration-300 border ${
                  !isHeader
                    ? "bg-gold text-maroon-dark border-gold shadow-[0_0_10px_rgba(212,175,55,0.2)]"
                    : "bg-gray-dark border-white/5 text-gray-light hover:text-white"
                }`}
              >
                Foot Kick
              </button>
              <button
                onClick={() => setIsHeader(true)}
                className={`flex-grow py-3 px-4 rounded-xl text-xs font-bold font-heading cursor-pointer transition-all duration-300 border ${
                  isHeader
                    ? "bg-gold text-maroon-dark border-gold shadow-[0_0_10px_rgba(212,175,55,0.2)]"
                    : "bg-gray-dark border-white/5 text-gray-light hover:text-white"
                }`}
              >
                Header / Aerial
              </button>
            </div>
          </div>

          {/* Pressure Selection */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
              Defense Pressure Level
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setUnderPressure(false)}
                className={`flex-grow py-3 px-4 rounded-xl text-xs font-bold font-heading cursor-pointer transition-all duration-300 border ${
                  !underPressure
                    ? "bg-gold text-maroon-dark border-gold shadow-[0_0_10px_rgba(212,175,55,0.2)]"
                    : "bg-gray-dark border-white/5 text-gray-light hover:text-white"
                }`}
              >
                No Pressure
              </button>
              <button
                onClick={() => setUnderPressure(true)}
                className={`flex-grow py-3 px-4 rounded-xl text-xs font-bold font-heading cursor-pointer transition-all duration-300 border ${
                  underPressure
                    ? "bg-gold text-maroon-dark border-gold shadow-[0_0_10px_rgba(212,175,55,0.2)]"
                    : "bg-gray-dark border-white/5 text-gray-light hover:text-white"
                }`}
              >
                Under Pressure
              </button>
            </div>
          </div>
        </div>

        {/* ── Circular Progress Gauge ── */}
        <div className="bg-black/25 rounded-2xl p-5 border border-white/5 mt-4 flex items-center gap-6">
          <div className="relative w-28 h-28 flex justify-center items-center">
            {/* SVG Circle Gauge */}
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="56"
                cy="56"
                r={radius}
                className="fill-none stroke-gray-dark stroke-[8px]"
              />
              <circle
                cx="56"
                cy="56"
                r={radius}
                className="fill-none stroke-[8px] transition-all duration-500 ease-out"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                stroke="url(#gaugeGradient)"
                strokeLinecap="round"
              />
              {/* Gradient definition */}
              <defs>
                <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="var(--color-field-green)" />
                  <stop offset="100%" stopColor="var(--color-gold)" />
                </linearGradient>
              </defs>
            </svg>
            {/* Inner Percentage Label */}
            <div className="absolute text-center">
              <span className="font-heading font-extrabold text-2xl text-gold">
                {displayVal.toFixed(2)}
              </span>
              <span className="block text-[8px] text-gray-light/60 font-bold uppercase tracking-wider">
                {activeTab === "xg" ? "XGBoost xG" : "XGBoost xP"}
              </span>
            </div>
          </div>

          <div className="flex-grow flex flex-col justify-center gap-2">
            <div>
              <h4 className="text-white text-xs font-extrabold font-heading tracking-wide uppercase">
                {activeTab === "xg" ? "Goal Probability Summary" : "Pass Success Probability"}
              </h4>
              <p className="text-gray-light/80 text-[11px] leading-relaxed mt-1 min-h-[32px]">
                {loading || xpLoading ? (
                  <span className="text-gold font-medium animate-pulse flex items-center gap-1.5">Scouting metrics...</span>
                ) : (
                  getInterpretation(displayVal)
                )}
              </p>
            </div>
            
            {activeTab === "xg" && (
              <div className="flex gap-4 border-t border-white/5 pt-2 mt-1">
                <div className="flex flex-col">
                  <span className="text-[9px] text-white/45 font-bold uppercase tracking-wider">Advanced (XGBoost)</span>
                  <span className="text-xs text-gold font-bold font-numeric">{(xg * 100).toFixed(1)}%</span>
                </div>
                <div className="w-[1px] bg-white/10" />
                <div className="flex flex-col">
                  <span className="text-[9px] text-white/45 font-bold uppercase tracking-wider">Baseline (LogReg)</span>
                  <span className="text-xs text-white/80 font-bold font-numeric">{(xgBaseline * 100).toFixed(1)}%</span>
                </div>
              </div>
            )}
            
            {activeTab === "xp" && (
              <div className="flex gap-4 border-t border-white/5 pt-2 mt-1">
                <div className="flex flex-col">
                  <span className="text-[9px] text-white/45 font-bold uppercase tracking-wider">Success Odds</span>
                  <span className="text-xs text-gold font-bold font-numeric">
                    {xpValue !== null ? `${(xpValue * 100).toFixed(1)}%` : "0.0%"}
                  </span>
                </div>
                <div className="w-[1px] bg-white/10" />
                <div className="flex flex-col">
                  <span className="text-[9px] text-white/45 font-bold uppercase tracking-wider">Pressure Decay</span>
                  <span className="text-xs text-white/80 font-bold font-numeric">
                    {underPressure ? "-18.0%" : "0.0%"}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
