import React, { useState, useMemo, useRef, useEffect } from "react";
import { motion } from "framer-motion";

const ABBREVIATIONS = {
  "Argentina": "ARG", "France": "FRA", "England": "ENG", "Portugal": "POR",
  "Brazil": "BRA", "Spain": "ESP", "Netherlands": "NED", "Germany": "GER",
  "Belgium": "BEL", "Croatia": "CRO", "Uruguay": "URU", "Morocco": "MAR",
  "Switzerland": "SUI", "Japan": "JPN", "Senegal": "SEN", "United States": "USA",
  "Mexico": "MEX", "South Korea": "KOR", "Iran": "IRN", "Austria": "AUT",
  "Australia": "AUS", "Sweden": "SWE", "Ecuador": "ECU", "Czech Republic": "CZE",
  "Turkey": "TUR", "Egypt": "EGY", "Tunisia": "TUN", "Algeria": "ALG",
  "Saudi Arabia": "KSA", "Panama": "PAN", "Norway": "NOR", "Canada": "CAN",
  "Cape Verde": "CPV", "Ghana": "GHA", "Iraq": "IRQ", "DR Congo": "COD",
  "Bosnia and Herzegovina": "BIH", "South Africa": "RSA", "Qatar": "QAT",
  "Scotland": "SCO", "Haiti": "HAI", "Jordan": "JOR", "Paraguay": "PAR",
  "Curacao": "CUW", "Ivory Coast": "CIV", "New Zealand": "NZL",
  "Uzbekistan": "UZB", "Indonesia": "IDN", "Honduras": "HON"
};

// Colors matching our design system variables
const STYLES = {
  gold: "hsl(46, 68%, 53%)",
  burgundy: "hsl(332, 85%, 4%)",
  slate: "hsl(231, 64%, 6%)",
  green: "hsl(145, 63%, 45%)"
};

export default function KnockoutBracket({ fixtures }) {
  const [hoveredTeam, setHoveredTeam] = useState(null);
  const containerRef = useRef(null);
  const [coords, setCoords] = useState({});

  // 1. Filter knockout fixtures
  const koFixtures = useMemo(() => {
    const koGroups = ["Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "3rd Place Match", "Final"];
    return (fixtures || []).filter(f => koGroups.includes(f.group));
  }, [fixtures]);

  // Group fixtures by rounds
  const rounds = useMemo(() => {
    const groups = {
      r32: koFixtures.filter(f => f.group === "Round of 32"),
      r16: koFixtures.filter(f => f.group === "Round of 16"),
      qf: koFixtures.filter(f => f.group === "Quarterfinals"),
      sf: koFixtures.filter(f => f.group === "Semifinals"),
      finals: koFixtures.filter(f => ["Final", "3rd Place Match"].includes(f.group))
    };
    return groups;
  }, [koFixtures]);

  // Handle tracking coordinates of match card slots to draw connecting SVGs
  const updateCoords = () => {
    if (!containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const newCoords = {};

    containerRef.current.querySelectorAll("[data-match-id]").forEach(el => {
      const matchId = el.getAttribute("data-match-id");
      const rect = el.getBoundingClientRect();
      
      // Calculate center right and center left relative to container
      newCoords[matchId] = {
        left: rect.left - containerRect.left,
        right: rect.right - containerRect.left,
        top: rect.top - containerRect.top + rect.height / 2,
        width: rect.width,
        height: rect.height
      };
    });

    setCoords(newCoords);
  };

  useEffect(() => {
    // Initial coordinates calculation
    setTimeout(updateCoords, 500);
    window.addEventListener("resize", updateCoords);
    return () => window.removeEventListener("resize", updateCoords);
  }, [fixtures]);

  // Render SVG connecting lines between parent matches and child matches
  const renderConnections = () => {
    if (Object.keys(coords).length === 0) return null;

    const paths = [];
    const drawLine = (fromId, toId, color = "rgba(255,255,255,0.08)", width = 1.5) => {
      const from = coords[fromId];
      const to = coords[toId];
      if (!from || !to) return null;

      // Draw a neat cubic bezier curve from from.right/left to to.left/right
      const startX = from.right;
      const startY = from.top;
      const endX = to.left;
      const endY = to.top;

      // Control points for curvy lines
      const cp1X = startX + (endX - startX) * 0.5;
      const cp1Y = startY;
      const cp2X = startX + (endX - startX) * 0.5;
      const cp2Y = endY;

      paths.push(
        <path
          key={`path-${fromId}-${toId}`}
          d={`M ${startX} ${startY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${endX} ${endY}`}
          fill="none"
          stroke={color}
          strokeWidth={width}
          className="transition-all duration-300"
        />
      );
    };

    // Connections: R32 -> R16
    // Match 73 & 74 -> 89
    // Match 75 & 76 -> 90
    // Match 77 & 78 -> 91
    // Match 79 & 80 -> 92
    // Match 81 & 82 -> 93
    // Match 83 & 84 -> 94
    // Match 85 & 86 -> 95
    // Match 87 & 88 -> 96
    for (let i = 0; i < 8; i++) {
      const r32_1 = 73 + i * 2;
      const r32_2 = 74 + i * 2;
      const r16 = 89 + i;
      
      const winner1 = koFixtures.find(f => f.match_id === r32_1)?.winner;
      const winner2 = koFixtures.find(f => f.match_id === r32_2)?.winner;
      const active1 = hoveredTeam && winner1 === hoveredTeam;
      const active2 = hoveredTeam && winner2 === hoveredTeam;

      drawLine(r32_1, r16, active1 ? STYLES.gold : undefined, active1 ? 3 : undefined);
      drawLine(r32_2, r16, active2 ? STYLES.gold : undefined, active2 ? 3 : undefined);
    }

    // Connections: R16 -> QF
    // Match 89 & 90 -> 97
    // Match 91 & 92 -> 98
    // Match 93 & 94 -> 99
    // Match 95 & 96 -> 100
    for (let i = 0; i < 4; i++) {
      const r16_1 = 89 + i * 2;
      const r16_2 = 90 + i * 2;
      const qf = 97 + i;

      const winner1 = koFixtures.find(f => f.match_id === r16_1)?.winner;
      const winner2 = koFixtures.find(f => f.match_id === r16_2)?.winner;
      const active1 = hoveredTeam && winner1 === hoveredTeam;
      const active2 = hoveredTeam && winner2 === hoveredTeam;

      drawLine(r16_1, qf, active1 ? STYLES.gold : undefined, active1 ? 3 : undefined);
      drawLine(r16_2, qf, active2 ? STYLES.gold : undefined, active2 ? 3 : undefined);
    }

    // Connections: QF -> SF
    // Match 97 & 98 -> 101
    // Match 99 & 100 -> 102
    for (let i = 0; i < 2; i++) {
      const qf_1 = 97 + i * 2;
      const qf_2 = 98 + i * 2;
      const sf = 101 + i;

      const winner1 = koFixtures.find(f => f.match_id === qf_1)?.winner;
      const winner2 = koFixtures.find(f => f.match_id === qf_2)?.winner;
      const active1 = hoveredTeam && winner1 === hoveredTeam;
      const active2 = hoveredTeam && winner2 === hoveredTeam;

      drawLine(qf_1, sf, active1 ? STYLES.gold : undefined, active1 ? 3 : undefined);
      drawLine(qf_2, sf, active2 ? STYLES.gold : undefined, active2 ? 3 : undefined);
    }

    // Connections: SF -> Final (104)
    // Match 101 & 102 -> 104
    const sf_1 = 101;
    const sf_2 = 102;
    const finalMatch = 104;
    const winner1 = koFixtures.find(f => f.match_id === sf_1)?.winner;
    const winner2 = koFixtures.find(f => f.match_id === sf_2)?.winner;
    const active1 = hoveredTeam && winner1 === hoveredTeam;
    const active2 = hoveredTeam && winner2 === hoveredTeam;

    drawLine(sf_1, finalMatch, active1 ? STYLES.gold : undefined, active1 ? 3 : undefined);
    drawLine(sf_2, finalMatch, active2 ? STYLES.gold : undefined, active2 ? 3 : undefined);

    // Connections: SF -> 3rd Place Playoff (103)
    const thirdPlaceMatch = 103;
    const match_sf1 = koFixtures.find(f => f.match_id === sf_1);
    const match_sf2 = koFixtures.find(f => f.match_id === sf_2);
    const loser1 = match_sf1 ? (match_sf1.winner === match_sf1.home ? match_sf1.away : match_sf1.home) : null;
    const loser2 = match_sf2 ? (match_sf2.winner === match_sf2.home ? match_sf2.away : match_sf2.home) : null;
    const activeLoser1 = hoveredTeam && loser1 === hoveredTeam;
    const activeLoser2 = hoveredTeam && loser2 === hoveredTeam;

    drawLine(sf_1, thirdPlaceMatch, activeLoser1 ? STYLES.gold : "rgba(255,255,255,0.04)", activeLoser1 ? 3 : 0.8);
    drawLine(sf_2, thirdPlaceMatch, activeLoser2 ? STYLES.gold : "rgba(255,255,255,0.04)", activeLoser2 ? 3 : 0.8);

    return (
      <svg className="absolute inset-0 w-full h-full pointer-events-none select-none z-0">
        {paths}
      </svg>
    );
  };

  const getAbbr = (team) => ABBREVIATIONS[team] || (team ? team.substring(0, 3).toUpperCase() : "TBD");

  // Render a single match box
  const MatchCard = ({ match }) => {
    if (!match) return <div className="h-20 bg-white/5 border border-white/10 rounded-lg animate-pulse" />;

    const { match_id, home, away, home_score, away_score, status, extra_time, penalties, penalty_scores, winner } = match;

    const isHomeHovered = hoveredTeam && home === hoveredTeam;
    const isAwayHovered = hoveredTeam && away === hoveredTeam;
    const isWinnerHovered = hoveredTeam && winner === hoveredTeam;

    const homeAbbr = getAbbr(home);
    const awayAbbr = getAbbr(away);

    return (
      <motion.div
        data-match-id={match_id}
        whileHover={{ scale: 1.02 }}
        transition={{ type: "spring", stiffness: 400, damping: 25 }}
        className={`relative z-10 w-56 flex flex-col bg-white/[0.03] border ${
          isWinnerHovered ? "border-[hsl(46,68%,53%)]/60 shadow-[0_0_15px_rgba(217,171,46,0.15)]" : "border-white/10"
        } rounded-xl overflow-hidden shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md p-3 select-none`}
      >
        {/* Match Header Info */}
        <div className="flex justify-between items-center text-[9px] tracking-wider text-white/40 mb-2 font-heading font-semibold">
          <span>MATCH #{match_id}</span>
          <span className="uppercase text-[hsl(46,68%,53%)] font-bold">{match.group}</span>
        </div>

        {/* Teams container */}
        <div className="flex flex-col gap-2">
          {/* Home Team Row */}
          <div
            onMouseEnter={() => home && setHoveredTeam(home)}
            onMouseLeave={() => setHoveredTeam(null)}
            className={`flex justify-between items-center rounded-lg p-1.5 transition-all ${
              isHomeHovered ? "bg-white/10" : ""
            } ${winner === home && status === "completed" ? "font-bold text-white" : "text-white/60"}`}
          >
            <div className="flex items-center gap-2">
              <span className="w-8 h-5 flex items-center justify-center text-[10px] font-bold font-heading rounded border border-white/10 bg-white/5 text-white/80">
                {homeAbbr}
              </span>
              <span className="text-xs truncate max-w-[100px]">{home || "TBD"}</span>
            </div>
            
            <div className="flex items-center gap-1.5 font-numeric text-xs">
              {status === "completed" && (
                <>
                  <span>{home_score}</span>
                  {penalties && penalty_scores && (
                    <span className="text-[9px] text-white/40 font-normal">({penalty_scores[0]})</span>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Away Team Row */}
          <div
            onMouseEnter={() => away && setHoveredTeam(away)}
            onMouseLeave={() => setHoveredTeam(null)}
            className={`flex justify-between items-center rounded-lg p-1.5 transition-all ${
              isAwayHovered ? "bg-white/10" : ""
            } ${winner === away && status === "completed" ? "font-bold text-white" : "text-white/60"}`}
          >
            <div className="flex items-center gap-2">
              <span className="w-8 h-5 flex items-center justify-center text-[10px] font-bold font-heading rounded border border-white/10 bg-white/5 text-white/80">
                {awayAbbr}
              </span>
              <span className="text-xs truncate max-w-[100px]">{away || "TBD"}</span>
            </div>
            
            <div className="flex items-center gap-1.5 font-numeric text-xs">
              {status === "completed" && (
                <>
                  <span>{away_score}</span>
                  {penalties && penalty_scores && (
                    <span className="text-[9px] text-white/40 font-normal">({penalty_scores[1]})</span>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Tiebreaker Badges */}
        {status === "completed" && (extra_time || penalties) && (
          <div className="mt-2 pt-1.5 border-t border-white/5 flex justify-end gap-1.5 text-[8px] font-bold uppercase tracking-wider">
            {extra_time && !penalties && <span className="text-white/40">AET</span>}
            {penalties && <span className="text-[hsl(46,68%,53%)]">PEN</span>}
          </div>
        )}
      </motion.div>
    );
  };

  return (
    <div className="relative flex flex-col w-full h-full bg-white/[0.02] border border-white/5 rounded-2xl p-8 overflow-hidden">
      {/* Glare background */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-white/2 opacity-[0.01] rounded-full blur-[100px]" />
      
      {/* Title Panel */}
      <div className="mb-6 flex justify-between items-center border-b border-white/5 pb-4">
        <div>
          <h2 className="text-xl font-heading font-bold text-white flex items-center gap-3">
            <span className="w-2.5 h-2.5 bg-[hsl(46,68%,53%)] rounded-full animate-pulse" />
            Tournament Bracket
          </h2>
          <p className="text-xs text-white/40 mt-1">Hover over any nation to trace their path through the tournament stages</p>
        </div>
      </div>

      {/* Bracket Tree Container */}
      <div ref={containerRef} className="relative flex justify-between gap-12 min-w-[1100px] py-10 overflow-x-auto overflow-y-hidden z-10">
        
        {/* Draw Line paths behind match cards */}
        {renderConnections()}

        {/* Round of 32 */}
        <div className="flex flex-col justify-around gap-4">
          <div className="text-center text-[10px] tracking-[0.2em] font-heading font-semibold text-white/40 uppercase mb-2">Round of 32</div>
          {rounds.r32.map(f => <MatchCard key={f.match_id} match={f} />)}
        </div>

        {/* Round of 16 */}
        <div className="flex flex-col justify-around gap-6">
          <div className="text-center text-[10px] tracking-[0.2em] font-heading font-semibold text-white/40 uppercase mb-2">Round of 16</div>
          {rounds.r16.map(f => <MatchCard key={f.match_id} match={f} />)}
        </div>

        {/* Quarterfinals */}
        <div className="flex flex-col justify-around gap-8">
          <div className="text-center text-[10px] tracking-[0.2em] font-heading font-semibold text-white/40 uppercase mb-2">Quarterfinals</div>
          {rounds.qf.map(f => <MatchCard key={f.match_id} match={f} />)}
        </div>

        {/* Semifinals */}
        <div className="flex flex-col justify-around gap-12">
          <div className="text-center text-[10px] tracking-[0.2em] font-heading font-semibold text-white/40 uppercase mb-2">Semifinals</div>
          {rounds.sf.map(f => <MatchCard key={f.match_id} match={f} />)}
        </div>

        {/* Final & 3rd Place Match */}
        <div className="flex flex-col justify-center gap-16">
          <div className="flex flex-col gap-4">
            <div className="text-center text-[10px] tracking-[0.2em] font-heading font-semibold text-[hsl(46,68%,53%)] uppercase mb-2">Grand Final</div>
            {rounds.finals.filter(f => f.group === "Final").map(f => <MatchCard key={f.match_id} match={f} />)}
          </div>

          <div className="flex flex-col gap-4 opacity-70">
            <div className="text-center text-[9px] tracking-[0.2em] font-heading font-semibold text-white/30 uppercase mb-2">Third Place Playoff</div>
            {rounds.finals.filter(f => f.group === "3rd Place Match").map(f => <MatchCard key={f.match_id} match={f} />)}
          </div>
        </div>
      </div>
    </div>
  );
}
