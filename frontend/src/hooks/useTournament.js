import { useState, useEffect, useRef } from "react";

export function useTournament() {
  const [currentDate, setCurrentDate] = useState("2026-06-11");
  const [data, setData] = useState({
    fixtures: [],
    standings: {},
    ratings: {}
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // In-memory cache to avoid repeated fetches when sliding back-and-forth
  const cacheRef = useRef({});

  useEffect(() => {
    let active = true;

    async function fetchState() {
      if (cacheRef.current[currentDate]) {
        setData(cacheRef.current[currentDate]);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const res = await fetch(`/api/fixtures?date=${currentDate}`);
        if (!res.ok) {
          throw new Error(`API Error: ${res.statusText}`);
        }
        const json = await res.json();
        
        if (active) {
          cacheRef.current[currentDate] = json;
          setData(json);
          setLoading(false);
        }
      } catch (err) {
        if (active) {
          setError(err.message || "Failed to fetch tournament state");
          setLoading(false);
        }
      }
    }

    fetchState();

    return () => {
      active = false;
    };
  }, [currentDate]);

  return {
    currentDate,
    setCurrentDate,
    fixtures: data.fixtures,
    standings: data.standings,
    ratings: data.ratings,
    loading,
    error
  };
}
