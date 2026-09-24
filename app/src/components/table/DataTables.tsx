import type { EoyRow, DrawdownRow, HorizonRow } from "../../api/types";
import { fmtPct, fmtNumber, pnlClass } from "../../lib/format";

// Return & Risk by horizon: CAGR / Max Drawdown / Calmar over trailing 1Y, 3Y,
// 5Y and all-time windows. Horizons longer than the available history come back
// as null and render as "N/A" (never a mislabelled short window).
export function HorizonTable({ rows }: { rows: HorizonRow[] }) {
  const LABEL: Record<string, string> = {
    "1Y": "1 Year",
    "3Y": "3 Years",
    "5Y": "5 Years",
    All: "All-time",
  };
  const na = (v: number | null) => v === null || Number.isNaN(v);
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-hair text-muted">
          <th className="text-left py-2 px-3 font-medium">Horizon</th>
          <th className="text-right py-2 px-3 font-medium">CAGR</th>
          <th className="text-right py-2 px-3 font-medium">Max DD</th>
          <th className="text-right py-2 px-3 font-medium">Calmar</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.horizon} className="border-b border-hair/60">
            <td className="py-1.5 px-3 text-ink">{LABEL[r.horizon] ?? r.horizon}</td>
            <td className={`py-1.5 px-3 text-right nums ${na(r.cagr) ? "text-faint" : pnlClass(r.cagr)}`}>
              {na(r.cagr) ? "N/A" : fmtPct(r.cagr)}
            </td>
            <td className={`py-1.5 px-3 text-right nums ${na(r.max_drawdown) ? "text-faint" : "text-pnl-neg"}`}>
              {na(r.max_drawdown) ? "N/A" : fmtPct(r.max_drawdown)}
            </td>
            <td className="py-1.5 px-3 text-right nums text-ink">
              {na(r.calmar) ? "N/A" : fmtNumber(r.calmar, 2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function EoyTable({ rows, hasBenchmark }: { rows: EoyRow[]; hasBenchmark: boolean }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-hair text-muted">
          <th className="text-left py-2 px-3 font-medium">Year</th>
          <th className="text-right py-2 px-3 font-medium">Strategy</th>
          {hasBenchmark && <th className="text-right py-2 px-3 font-medium">Benchmark</th>}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.year} className="border-b border-hair/60">
            <td className="py-1.5 px-3 nums">{r.year}</td>
            <td className={`py-1.5 px-3 text-right nums ${pnlClass(r.strategy)}`}>
              {fmtPct(r.strategy)}
            </td>
            {hasBenchmark && (
              <td className={`py-1.5 px-3 text-right nums ${pnlClass(r.benchmark)}`}>
                {fmtPct(r.benchmark)}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function WorstDrawdownsTable({ rows }: { rows: DrawdownRow[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-hair text-muted">
          <th className="text-left py-2 px-3 font-medium">Started</th>
          <th className="text-left py-2 px-3 font-medium">Recovered</th>
          <th className="text-right py-2 px-3 font-medium">Days</th>
          <th className="text-right py-2 px-3 font-medium">Drawdown</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b border-hair/60">
            <td className="py-1.5 px-3 nums text-muted">{r.start}</td>
            <td
              className={`py-1.5 px-3 nums ${r.ongoing ? "text-pnl-neg" : "text-muted"}`}
              title={r.ongoing ? `Still underwater as of ${r.end}` : undefined}
            >
              {r.ongoing ? "Not yet" : r.end}
            </td>
            <td className="py-1.5 px-3 text-right nums">{fmtNumber(r.days, 0)}</td>
            <td className="py-1.5 px-3 text-right nums text-pnl-neg">
              {/* drawdown_pct is the full depth as a percent magnitude (e.g. -19.3),
                  the same number the rows are sorted by */}
              {r.drawdown_pct === null ? "—" : `${fmtNumber(r.drawdown_pct, 2)}%`}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
