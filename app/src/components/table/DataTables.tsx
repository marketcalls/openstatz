import type { EoyRow, DrawdownRow } from "../../api/types";
import { fmtPct, fmtNumber, pnlClass } from "../../lib/format";

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
            <td className="py-1.5 px-3 nums text-muted">{r.end}</td>
            <td className="py-1.5 px-3 text-right nums">{fmtNumber(r.days, 0)}</td>
            <td className="py-1.5 px-3 text-right nums text-pnl-neg">
              {/* drawdown_pct is already a percent magnitude (e.g. -19.3) */}
              {r.drawdown_pct === null ? "—" : `${fmtNumber(r.drawdown_pct, 2)}%`}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
