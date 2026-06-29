import type { AnalysisResponse } from "../api/types";
import { getMetric, type StatSpec, type Fmt } from "../lib/metrics";
import { fmtPct, fmtNumber, pnlClass } from "../lib/format";

function fmtVal(v: number | null, fmt: Fmt): string {
  if (v === null || Number.isNaN(v)) return "—";
  if (fmt === "pct") return fmtPct(v);
  if (fmt === "int") return fmtNumber(v, 0);
  return fmtNumber(v);
}

// A connected-hairline grid of stat tiles (label / value / subline). When a
// benchmark is present the subline shows its value; otherwise a short
// description. Return-type values are P&L color-coded.
export function StatGrid({
  data,
  specs,
  primary,
  benchCol,
}: {
  data: AnalysisResponse;
  specs: StatSpec[];
  primary: string;
  benchCol: string | null;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-px bg-hair border border-hair rounded-lg overflow-hidden">
      {specs.map((s) => {
        const m = getMetric(data, s.metric, primary, benchCol);
        const tone = s.tone ? m.value : undefined;
        const sub =
          benchCol && m.benchValue !== null
            ? `${benchCol} ${fmtVal(m.benchValue, s.fmt)}`
            : s.desc;
        return (
          <div key={s.name} className="bg-panel px-4 py-3.5 min-w-0">
            <div className="eyebrow truncate" title={s.name}>
              {s.name}
            </div>
            <div className={`mt-2 text-[1.4rem] leading-none nums ${pnlClass(tone)}`}>
              {fmtVal(m.value, s.fmt)}
            </div>
            {sub && (
              <div className="mt-2 text-[0.7rem] text-faint nums truncate" title={sub}>
                {sub}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
