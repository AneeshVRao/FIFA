import React, { useState, useEffect } from "react";
import { Search, Loader2, Award, Users, Shield, Calendar, Globe, ListFilter } from "lucide-react";

export function StatsCenter() {
  const [activeTab, setActiveTab] = useState("premier_league");
  const [activeStat, setActiveStat] = useState("premier_league_top_goalscorers");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const categories = {
    premier_league: {
      label: "Premier League",
      icon: Shield,
      stats: {
        premier_league_top_goalscorers: "Top Goalscorers",
        premier_league_most_assists: "Most Assists",
        premier_league_most_goal_contributions: "Most Goal Contributions",
        premier_league_most_clean_sheets: "Most Clean Sheets",
        premier_league_record_goalscorers: "Record Goalscorers",
        premier_league_foreigners: "Foreign Players",
        premier_league_most_penalties_awarded: "Penalties Awarded",
        premier_league_form_table: "League Form Table",
        premier_league_all_league_champions: "League Champions",
        premier_league_attendance_ranking: "Attendance Ranking",
        premier_league_all_premier_league_stats: "All-Time Stats Summary"
      }
    },
    global_players: {
      label: "Global Players",
      icon: Users,
      stats: {
        global_player_top_goalscorers: "Global Top Goalscorers",
        global_player_most_assists: "Global Most Assists",
        global_player_most_goal_contributions: "Global Goal Contributions",
        global_player_most_clean_sheets: "Global Clean Sheets",
        global_player_most_games_played: "Most Games Played",
        global_player_top_scoring_duos: "Top Scoring Duos",
        global_player_top_scoring_trios: "Top Scoring Trios",
        global_player_latest_multiple_goalscorers: "Latest Multi-Goalscorers",
        global_player_youngest_players_used: "Youngest Players Used",
        global_player_longest_serving_players: "Longest Serving Players",
        global_player_goalscorers_of_the_year: "Goalscorers of the Year",
        global_player_global_foreigners_stat: "Global Foreigners Stat",
        global_player_brothers_at_one_club: "Brothers at One Club",
        global_player_player_comparison: "Head-to-Head Player Comparison"
      }
    },
    global_clubs: {
      label: "Global Clubs",
      icon: Award,
      stats: {
        global_club_all_league_cup_winners: "All League & Cup Winners",
        global_club_double_winners: "Double Winners History",
        global_club_treble_winners: "Treble Winners History",
        global_club_most_european_club_competition_titles: "UEFA European Titles",
        global_club_uefa_club_ranking: "UEFA Club Coefficient",
        global_club_uefa_5_year_ranking: "UEFA 5-Year Ranking",
        global_club_afc_4_year_ranking: "AFC 4-Year Coefficient",
        global_club_international_form_table: "International Form Table",
        global_club_international_attendance_ranking: "International Attendance",
        global_club_club_comparison: "Club-to-Club Comparison Index"
      }
    },
    global_coaches: {
      label: "Global Coaches",
      icon: Calendar,
      stats: {
        global_coach_world_best_club_coach: "World's Best Club Coach",
        global_coach_world_best_national_team_coach: "World's Best National Team Coach",
        global_coach_coaches_in_foreign_countries: "Coaches in Foreign Countries",
        global_coach_coaching_fathers: "Coaching Fathers & Player Sons"
      }
    },
    national_teams: {
      label: "National Teams",
      icon: Globe,
      stats: {
        national_team_fifa_world_ranking: "FIFA Men's World Ranking",
        national_team_record_holding_national_team_players: "Record-Holding Players",
        national_team_fathers_sons: "Fathers & Sons Internationals",
        national_team_brothers: "Brothers at International Level"
      }
    }
  };

  useEffect(() => {
    fetchStats();
  }, [activeStat]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/stats/transfermarkt?category=${activeStat}`);
      if (!res.ok) throw new Error("Stats API failed");
      const json = await res.json();
      setData(json.data || []);
    } catch (err) {
      console.error(err);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  // Filter data based on search input
  const filteredData = data.filter((row) => {
    return Object.values(row).some((val) =>
      String(val).toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // Extract columns dynamically from JSON fields
  const columns = data.length > 0 ? Object.keys(data[0]) : [];

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    const defaultStat = Object.keys(categories[tabId].stats)[0];
    setActiveStat(defaultStat);
    setSearchQuery("");
  };

  const getHeaderLabel = (colName) => {
    return colName
      .replace(/_/g, " ")
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[260px_1fr] gap-6 mt-6">
      
      {/* ── Left Navigation: Stats Categories ── */}
      <div className="flex flex-col gap-4">
        <div className="glass-panel rounded-2xl p-4 border border-gold/15 flex flex-col gap-1.5">
          <span className="text-[10px] font-bold text-gold/80 tracking-[2px] uppercase px-3 pb-2 border-b border-white/5 mb-2 font-heading">
            Stats Categories
          </span>
          {Object.entries(categories).map(([tabId, cat]) => {
            const Icon = cat.icon;
            const isActive = activeTab === tabId;
            return (
              <button
                key={tabId}
                onClick={() => handleTabChange(tabId)}
                className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-bold transition-all duration-300 font-heading text-left cursor-pointer border ${
                  isActive
                    ? "bg-gradient-to-r from-gold/15 to-gold/3 border-gold text-gold shadow-[0_0_10px_rgba(212,175,55,0.1)]"
                    : "border-transparent text-gray-light hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon size={14} className={isActive ? "text-gold" : "text-gray-light/65"} />
                {cat.label}
              </button>
            );
          })}
        </div>

        {/* ── Sub-level Stats List ── */}
        <div className="glass-panel rounded-2xl p-4 border border-gold/15 flex flex-col gap-1.5 max-h-[350px] overflow-y-auto">
          <span className="text-[10px] font-bold text-gold/80 tracking-[2px] uppercase px-3 pb-2 border-b border-white/5 mb-2 font-heading">
            Tables List
          </span>
          {Object.entries(categories[activeTab].stats).map(([statId, label]) => {
            const isActive = activeStat === statId;
            return (
              <button
                key={statId}
                onClick={() => setActiveStat(statId)}
                className={`w-full px-3 py-2 rounded-lg text-[11px] font-medium transition-all text-left cursor-pointer border ${
                  isActive
                    ? "bg-white/10 border-white/10 text-white font-bold"
                    : "border-transparent text-gray-light/75 hover:bg-white/5 hover:text-white"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Right Content: Data Grid ── */}
      <div className="glass-panel rounded-2xl border border-gold/15 p-6 flex flex-col gap-4 min-h-[500px]">
        
        {/* Table Title and Search Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
          <div>
            <h3 className="text-white text-lg font-bold font-heading">
              {categories[activeTab].stats[activeStat]}
            </h3>
            <p className="text-[11px] text-gray-light/70 mt-1">
              Parsed details scraped directly from Transfermarkt records database
            </p>
          </div>

          {/* Search Box */}
          <div className="relative w-full md:w-[280px]">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-light/60" size={14} />
            <input
              type="text"
              placeholder="Search table rows..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-xs text-white placeholder-gray-light/50 focus:border-gold/50 focus:outline-none transition-all shadow-[inset_0_2px_8px_rgba(0,0,0,0.5)] font-medium"
            />
          </div>
        </div>

        {/* Data Presentation Table */}
        <div className="flex-grow overflow-x-auto min-h-[300px]">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[350px]">
              <Loader2 className="text-gold animate-spin mb-3" size={32} />
              <span className="text-xs text-gray-light font-bold font-heading tracking-widest uppercase">
                Loading Transfermarkt Data...
              </span>
            </div>
          ) : filteredData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[350px] text-center">
              <ListFilter className="text-gray-light/25 mb-2" size={36} />
              <p className="text-sm font-bold text-gray-light/80">No stats items found matching your filters</p>
              <p className="text-xs text-gray-light/40 mt-1">Try resetting the query or selecting another stats table.</p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-white/10">
                  {columns.map((col) => (
                    <th
                      key={col}
                      className="py-3 px-4 text-gold font-bold tracking-wider uppercase font-heading text-[10px]"
                    >
                      {getHeaderLabel(col)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredData.map((row, idx) => {
                  const isLeader = row.rank === "1" || idx === 0;
                  return (
                    <tr
                      key={idx}
                      className={`transition-all hover:bg-white/5 ${
                        isLeader 
                          ? "bg-gold/5 border-l-2 border-l-gold shadow-[inset_0_0_12px_rgba(212,175,55,0.02)]" 
                          : ""
                      }`}
                    >
                      {columns.map((col) => {
                        const val = row[col];
                        const isRank = col === "rank" || col === "points";
                        const isValue = col.includes("value") || col.includes("val");
                        return (
                          <td
                            key={col}
                            className={`py-3 px-4 font-medium text-white/95 ${
                              isRank ? "font-mono font-bold text-gold" : ""
                            } ${
                              isValue ? "font-mono text-emerald-400 font-bold" : ""
                            }`}
                          >
                            {isLeader && col === "player" ? (
                              <span className="flex items-center gap-1.5">
                                👑 {val}
                              </span>
                            ) : (
                              val
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

      </div>

    </div>
  );
}
