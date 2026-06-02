import React, { useState, useEffect, useRef } from "react";
import { Crosshair, ShieldAlert, CircleDot } from "lucide-react";

export function XgSandbox() {
  const [x, setX] = useState(108.0);
  const [y, setY] = useState(40.0);
  const [isHeader, setIsHeader] = useState(false);
  const [underPressure, setUnderPressure] = useState(false);
  const [xg, setXg] = useState(0.76);
  const [xgBaseline, setXgBaseline] = useState(0.76);
  const [loading, setLoading] = useState(false);

  const svgRef = useRef(null);

  useEffect(() => {
    fetchXG();
  }, [x, y, isHeader, underPressure]);

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

  const handlePitchClick = (event) => {
    const svg = svgRef.current;
    if (!svg) return;

    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;

    // Projected mouse cursor coordinates onto the SVG canvas (works with 3D transforms!)
    const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

    // Attacking half is (60 to 120x, 0 to 80y)
    const newX = Math.min(Math.max(svgP.x, 60.0), 120.0);
    const newY = Math.min(Math.max(svgP.y, 0.0), 80.0);

    setX(parseFloat(newX.toFixed(1)));
    setY(parseFloat(newY.toFixed(1)));
  };

  // Radial Gauge Calculations
  const radius = 55;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - xg * circumference;

  const getInterpretation = (val) => {
    if (val >= 0.70) return "Championship Penalty Grade. Typical penalty kick conversion rate.";
    if (val >= 0.35) return "High-quality opportunity. Clean target access inside the goal box.";
    if (val >= 0.15) return "Moderate chance. Average conversion rate for box scrambles.";
    if (val >= 0.05) return "Low chance. Standard distance header or pressured wide-angle shot.";
    return "Speculative try. Minimal scoring probability from this range.";
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-6 mt-6">
      
      {/* ── Attacking 3D Soccer Pitch Column ── */}
      <div className="glass-panel rounded-2xl p-6 border border-gold/15 flex flex-col gap-4">
        <div className="pb-2">
          <h3 className="text-white text-lg font-bold font-heading">
            Expected Goals (xG) Plotter
          </h3>
          <p className="text-gray-light/80 text-xs mt-1">
            Click on the 3D isometric pitch below to change the ball location and calculate the xG value
          </p>
        </div>

        {/* 3D Perspective Wrapper */}
        <div 
          className="bg-gradient-to-br from-[#0a180e] to-[#112d18] border-2 border-gold/10 rounded-2xl p-6 flex justify-center items-center overflow-hidden shadow-[inset_0_0_24px_rgba(0,0,0,0.8)]"
          style={{ perspective: "1000px" }}
        >
          <svg
            ref={svgRef}
            onClick={handlePitchClick}
            viewBox="60 0 60 80"
            className="w-full max-h-[350px] cursor-crosshair origin-center transform transition-transform duration-500 hover:scale-[1.01]"
            style={{
              transform: "rotateX(22deg)",
              transformStyle: "preserve-3d"
            }}
          >
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

            {/* Ball Marker (displays current click coordinates) */}
            <circle
              cx={x}
              cy={y}
              r="1.6"
              className="fill-gold stroke-white stroke-[0.6px] pulse filter drop-shadow-[0_0_6px_var(--color-gold)]"
            />
          </svg>
        </div>
      </div>

      {/* ── Controls & Circular Gauge Column ── */}
      <div className="glass-panel rounded-2xl p-6 border border-gold/15 flex flex-col justify-between">
        <div className="flex flex-col gap-6">
          <div className="pb-2 border-b border-white/5">
            <h3 className="text-white text-lg font-bold font-heading">
              Shot Parameters
            </h3>
          </div>

          {/* Coordinates Display */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
              Target Coordinates
            </span>
            <div className="flex gap-4">
              <div className="bg-gray-dark border border-white/5 px-4 py-3 rounded-xl flex-grow text-center font-extrabold text-sm text-white">
                X: {x.toFixed(1)}m
              </div>
              <div className="bg-gray-dark border border-white/5 px-4 py-3 rounded-xl flex-grow text-center font-extrabold text-sm text-white">
                Y: {y.toFixed(1)}m
              </div>
            </div>
          </div>

          {/* Body Part Selection */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
              Body Part
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
                Foot
              </button>
              <button
                onClick={() => setIsHeader(true)}
                className={`flex-grow py-3 px-4 rounded-xl text-xs font-bold font-heading cursor-pointer transition-all duration-300 border ${
                  isHeader
                    ? "bg-gold text-maroon-dark border-gold shadow-[0_0_10px_rgba(212,175,55,0.2)]"
                    : "bg-gray-dark border-white/5 text-gray-light hover:text-white"
                }`}
              >
                Header
              </button>
            </div>
          </div>

          {/* Pressure Selection */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-bold text-gold/80 tracking-wider uppercase">
              Pressure Level
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
                {xg.toFixed(2)}
              </span>
              <span className="block text-[8px] text-gray-light/60 font-bold uppercase tracking-wider">
                XGBoost xG
              </span>
            </div>
          </div>

          <div className="flex-grow flex flex-col justify-center gap-2">
            <div>
              <h4 className="text-white text-xs font-extrabold font-heading tracking-wide uppercase">
                Goal Probability Comparison
              </h4>
              <p className="text-gray-light/80 text-[11px] leading-relaxed mt-1">
                {getInterpretation(xg)}
              </p>
            </div>
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
              <div className="w-[1px] bg-white/10" />
              <div className="flex flex-col">
                <span className="text-[9px] text-white/45 font-bold uppercase tracking-wider">Variance</span>
                <span className={`text-xs font-bold font-numeric ${Math.abs(xg - xgBaseline) > 0.05 ? "text-amber-400" : "text-white/60"}`}>
                  {((xg - xgBaseline) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
