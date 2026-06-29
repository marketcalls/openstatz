import { useState } from "react";
import type { WeeklyHeatmap as Data } from "../../api/types";
import { fmtPct } from "../../lib/format";

// Year-selectable weekly-returns heatmap: pick a year, see all ~52 weeks colored
// by return (diverging green/red via color-mix, per-year scale). The grid fills
// the card width responsively.
export function WeeklyHeatmap({ data }: { data: Data }) {
  const years = data.years;
  const [year, setYear] = useState(years[years.length - 1] ?? "");
  const activeYear = data.by_year[year] ? year : (years[years.length - 1] ?? "");
  const weeks = data.by_year[activeYear] ?? [];

  const bound = Math.max(0.0001, ...weeks.map((w) => Math.abs(w.value ?? 0)));
  const bg = (v: number | null) => {
    if (v === null || Number.isNaN(v)) return "transparent";
    const t = Math.min(Math.abs(v) / bound, 1) * 0.88;
    const target = v >= 0 ? "var(--heat-pos)" : "var(--heat-neg)";
    return `color-mix(in oklab, ${target} ${Math.round(t * 100)}%, var(--heat-mid))`;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3 gap-3">
        <div className="eyebrow">{weeks.length} weeks · week-ending return</div>
        <select
          value={activeYear}
          onChange={(e) => setYear(e.target.value)}
          className="bg-panel border border-hair rounded-md px-2.5 py-1.5 text-xs text-ink nums focus:outline-none focus:border-ink transition-colors"
          aria-label="Select year"
        >
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>
      <div
        className="grid gap-1"
        style={{ gridTemplateColumns: "repeat(auto-fill, minmax(64px, 1fr))" }}
      >
        {weeks.map((w) => (
          <div
            key={w.week}
            title={`Week ${w.week} (${w.label}): ${fmtPct(w.value)}`}
            className="h-14 rounded-[5px] border border-hair flex flex-col items-center justify-center gap-0.5"
            style={{
              background: bg(w.value),
              color: w.value === null ? "var(--text-faint)" : "var(--text)",
            }}
          >
            <span className="text-[0.74rem] nums">
              {w.value === null ? "" : (w.value * 100).toFixed(1)}
            </span>
            <span className="text-[0.56rem] opacity-60 nums">{w.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
