import { Fragment } from "react";
import type { MonthlyHeatmap as HeatmapData } from "../../api/types";
import { fmtPct } from "../../lib/format";

// Full-width calendar heatmap. A CSS grid (12 equal month columns) fills the
// card width; cell color is a diverging green/red mix centered at zero, built
// with color-mix() so it works with the hsl() theme vars and re-themes live.
export function MonthlyHeatmap({ data }: { data: HeatmapData }) {
  const vals = data.cells.map((c) => Math.abs(c.value ?? 0));
  const bound = Math.max(0.0001, ...vals);

  const cellOf = (year: string, month: string) =>
    data.cells.find((c) => c.year === year && c.month === month);

  const bg = (v: number | null) => {
    if (v === null || Number.isNaN(v)) return "transparent";
    const t = Math.min(Math.abs(v) / bound, 1) * 0.88;
    const target = v >= 0 ? "var(--heat-pos)" : "var(--heat-neg)";
    return `color-mix(in oklab, ${target} ${Math.round(t * 100)}%, var(--heat-mid))`;
  };

  return (
    <div className="w-full overflow-x-auto">
      <div
        className="min-w-[680px] grid gap-1"
        style={{ gridTemplateColumns: "2.75rem repeat(12, minmax(0, 1fr))" }}
      >
        <div />
        {data.months.map((m) => (
          <div
            key={m}
            className="text-center text-[0.64rem] font-semibold uppercase tracking-wider text-faint pb-1"
          >
            {m.slice(0, 1)}
          </div>
        ))}

        {data.years.map((y) => (
          <Fragment key={y}>
            <div className="flex items-center justify-end pr-2 text-xs text-muted nums">{y}</div>
            {data.months.map((m) => {
              const v = cellOf(y, m)?.value ?? null;
              return (
                <div
                  key={m}
                  title={`${m} ${y}: ${fmtPct(v)}`}
                  className="h-9 rounded-[5px] border border-hair grid place-items-center text-[0.72rem] nums"
                  style={{
                    background: bg(v),
                    color: v === null ? "var(--text-faint)" : "var(--text)",
                  }}
                >
                  {v === null ? "" : (v * 100).toFixed(1)}
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
