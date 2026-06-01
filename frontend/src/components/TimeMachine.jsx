import React from "react";

export function TimeMachine({ currentDate, setCurrentDate }) {
  // Translate date to index (0-30)
  const dateToIndex = (dateStr) => {
    const base = new Date(2026, 5, 11); // June 11, 2026
    const target = new Date(dateStr + "T00:00:00");
    const diffTime = Math.abs(target - base);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  // Translate index to date string (YYYY-MM-DD)
  const indexToDate = (index) => {
    const base = new Date(2026, 5, 11);
    base.setDate(base.getDate() + parseInt(index));
    return base.toISOString().split("T")[0];
  };

  const formatDateDisplay = (dateStr) => {
    const date = new Date(dateStr + "T00:00:00");
    return date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric"
    });
  };

  const currentIndex = dateToIndex(currentDate);

  const handleSliderChange = (e) => {
    const nextDate = indexToDate(e.target.value);
    setCurrentDate(nextDate);
  };

  return (
    <header className="glass-panel rounded-2xl p-6 flex flex-col md:flex-row justify-between items-center gap-6 border border-gold/15 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)] hover:border-gold/30 hover:shadow-[0_12px_40px_0_rgba(0,0,0,0.55),0_0_15px_0_rgba(212,175,55,0.15)] transition-all duration-500">
      <div className="text-center md:text-left flex-grow">
        <h2 className="text-white text-xl font-extrabold tracking-wide font-heading">
          Tournament Time Machine
        </h2>
        <p className="text-gray-light/80 text-xs mt-1">
          Slide the timeline to simulate match outcomes chronologically and update standings
        </p>
      </div>

      <div className="w-full md:w-auto flex flex-col sm:flex-row items-center gap-6 flex-grow max-w-[650px]">
        <div className="flex items-center gap-3 w-full flex-grow">
          <span className="text-[10px] font-bold text-gold/80 tracking-wide uppercase whitespace-nowrap">
            June 11
          </span>
          <input
            type="range"
            min="0"
            max="30"
            value={currentIndex}
            onChange={handleSliderChange}
            className="w-full h-1.5 rounded bg-gray-dark outline-none accent-gold cursor-pointer"
            style={{
              WebkitAppearance: "none",
              MozAppearance: "none"
            }}
          />
          <span className="text-[10px] font-bold text-gold/80 tracking-wide uppercase whitespace-nowrap">
            July 11
          </span>
        </div>

        <div className="bg-gold/10 border border-gold rounded-lg px-4 py-2 text-center min-w-[160px] shadow-[0_0_10px_rgba(212,175,55,0.05)]">
          <span className="block text-[9px] font-bold tracking-widest text-gold uppercase leading-tight">
            Simulation Date
          </span>
          <span className="text-sm font-extrabold text-white font-heading mt-0.5 block">
            {formatDateDisplay(currentDate)}
          </span>
        </div>
      </div>
    </header>
  );
}
