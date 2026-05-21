import { createContext, useCallback, useContext, useMemo, useState } from "react";

/**
 * Shared filter state powering Power-BI-style cross-filtering on the
 * Business Overview dashboard. Each widget reads the filters and re-fetches
 * when they change; clicking a chart segment toggles a filter value.
 *
 * Shape:
 *   {
 *     year: number | null,
 *     familyCodes: string[],
 *     formFactors: string[],
 *     supportActivities: string[],
 *     statuses: string[],
 *     siliconSteppings: string[],
 *   }
 */

const EMPTY_FILTERS = {
  year: null,
  familyCodes: [],
  formFactors: [],
  supportActivities: [],
  statuses: [],
  siliconSteppings: [],
};

const DashboardFiltersContext = createContext(null);

function toggleInArray(arr, value) {
  const idx = arr.indexOf(value);
  if (idx === -1) return [...arr, value];
  const next = arr.slice();
  next.splice(idx, 1);
  return next;
}

export function DashboardFiltersProvider({ children, initial }) {
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS, ...(initial || {}) });

  const setYear = useCallback(
    (year) => setFilters((f) => ({ ...f, year: year ?? null })),
    [],
  );

  const setMulti = useCallback(
    (key, values) => setFilters((f) => ({ ...f, [key]: values || [] })),
    [],
  );

  const toggleMulti = useCallback(
    (key, value) =>
      setFilters((f) => ({ ...f, [key]: toggleInArray(f[key] || [], value) })),
    [],
  );

  const clearAll = useCallback(() => setFilters({ ...EMPTY_FILTERS }), []);

  const removeChip = useCallback((key, value) => {
    setFilters((f) => {
      if (key === "year") return { ...f, year: null };
      const arr = f[key] || [];
      return { ...f, [key]: arr.filter((v) => v !== value) };
    });
  }, []);

  const chips = useMemo(() => {
    const out = [];
    if (filters.year != null) {
      out.push({ key: "year", value: filters.year, label: `Year: ${filters.year}` });
    }
    const groups = [
      ["familyCodes", "Family"],
      ["formFactors", "Form Factor"],
      ["supportActivities", "Activity"],
      ["statuses", "Status"],
      ["siliconSteppings", "Si Stepping"],
    ];
    groups.forEach(([k, label]) => {
      (filters[k] || []).forEach((v) =>
        out.push({ key: k, value: v, label: `${label}: ${v}` }),
      );
    });
    return out;
  }, [filters]);

  const value = useMemo(
    () => ({
      filters,
      setFilters,
      setYear,
      setMulti,
      toggleMulti,
      clearAll,
      removeChip,
      chips,
    }),
    [filters, setYear, setMulti, toggleMulti, clearAll, removeChip, chips],
  );

  return (
    <DashboardFiltersContext.Provider value={value}>
      {children}
    </DashboardFiltersContext.Provider>
  );
}

export function useDashboardFilters() {
  const ctx = useContext(DashboardFiltersContext);
  if (!ctx) {
    throw new Error(
      "useDashboardFilters must be used inside <DashboardFiltersProvider>",
    );
  }
  return ctx;
}
