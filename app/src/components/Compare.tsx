import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { compareSymbols } from "../api/client";
import type { SeriesPoint } from "../api/types";
import { useTheme } from "../theme/ThemeProvider";
import { Card } from "./ui/Card";
import { TimeSeriesChart, type ChartSeries } from "./charts/TimeSeriesChart";
import { MetricsTable } from "./table/MetricsTable";
import { COMPARE_METRICS, getMetric, type Fmt } from "../lib/metrics";
import { fmtPct, fmtNumber } from "../lib/format";

const PERIODS = ["1y", "2y", "5y", "10y", "max"];
// Categorical palette (avoids the P&L green/red, works in both themes).
const PALETTE = ["#4c8dff", "#a855f7", "#f59e0b", "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#14b8a6"];

function fmtVal(v: number | null, fmt: Fmt): string {
  if (v === null || Number.isNaN(v)) return "—";
  return fmt === "pct" ? fmtPct(v) : fmtNumber(v);
}

export function Compare() {
  const { theme } = useTheme();
  const [input, setInput] = useState("AAPL, NVDA");
  const [period, setPeriod] = useState("5y");
  const [submitted, setSubmitted] = useState<{ symbols: string[]; period: string }>({
    symbols: ["AAPL", "NVDA"],
    period: "5y",
  });

  const q = useQuery({
    queryKey: ["compare", submitted],
    queryFn: () => compareSymbols({ symbols: submitted.symbols, period: submitted.period }),
    retry: false,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const syms = input
      .split(/[,\s]+/)
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    if (syms.length >= 2) setSubmitted({ symbols: syms, period });
  };

  const field =
    "bg-panel-2 border border-hair rounded-md px-3 py-2 text-sm text-ink nums focus:outline-none focus:border-ink transition-colors";

  const bar = (
    <form onSubmit={submit} className="no-print flex flex-wrap items-end gap-3 card rounded-lg px-4 py-3.5">
      <label className="flex-1 min-w-[240px]">
        <span className="eyebrow mb-1.5 block">Symbols (2 or more, comma separated)</span>
        <input
          className={`${field} w-full`}
          value={input}
          onChange={(e) => setInput(e.target.value.toUpperCase())}
          placeholder="AAPL, NVDA, MSFT"
        />
      </label>
      <label>
        <span className="eyebrow mb-1.5 block">Period</span>
        <select className={`${field} w-24`} value={period} onChange={(e) => setPeriod(e.target.value)}>
          {PERIODS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </label>
      <button
        type="submit"
        disabled={q.isFetching}
        className="px-5 py-2 rounded-md bg-accent text-accent-ink text-sm font-semibold disabled:opacity-50 hover:brightness-110 transition"
      >
        {q.isFetching ? "Comparing…" : "Compare"}
      </button>
    </form>
  );

  if (q.isLoading) {
    return <div className="space-y-6">{bar}<Centered>Comparing {submitted.symbols.join(", ")} …</Centered></div>;
  }
  if (q.isError) {
    return (
      <div className="space-y-6">
        {bar}
        <Centered>
          <div className="max-w-lg text-center">
            <p className="text-pnl-neg mb-2 serif text-lg">Could not compare.</p>
            <p className="text-muted text-sm">Check the tickers, and make sure at least two have overlapping history.</p>
            <p className="text-faint text-xs mt-3 nums">{String(q.error)}</p>
          </div>
        </Centered>
      </div>
    );
  }

  const data = q.data!;
  const cols = data.meta.columns;
  const colorOf = (c: string) => PALETTE[cols.indexOf(c) % PALETTE.length];

  const toSeries = (bundle: Record<string, SeriesPoint[]> | undefined): ChartSeries[] =>
    (bundle ? cols.filter((c) => bundle[c]) : []).map((c) => ({
      name: c,
      data: bundle![c],
      color: colorOf(c),
      lineWidth: 2,
    }));

  // Best / worst per key metric, and a win tally.
  const wins: Record<string, number> = Object.fromEntries(cols.map((c) => [c, 0]));
  const rows = COMPARE_METRICS.map((spec) => {
    const vals = cols.map((c) => ({ col: c, value: getMetric(data, spec.metric, c, null).value }));
    const present = vals.filter((v) => v.value !== null) as { col: string; value: number }[];
    let best: string | null = null;
    let worst: string | null = null;
    if (present.length > 1) {
      const sorted = [...present].sort((a, b) => a.value - b.value);
      best = spec.better === "up" ? sorted[sorted.length - 1].col : sorted[0].col;
      worst = spec.better === "up" ? sorted[0].col : sorted[sorted.length - 1].col;
      if (best) wins[best] += 1;
    }
    return { spec, vals, best, worst };
  });
  const ranked = [...cols].sort((a, b) => wins[b] - wins[a]);
  const leader = ranked[0];

  const start = new Date(data.meta.start * 1000).toISOString().slice(0, 10);
  const end = new Date(data.meta.end * 1000).toISOString().slice(0, 10);

  return (
    <div className="space-y-6">
      {bar}

      {/* Leaderboard */}
      <div className="card rounded-lg p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-3 mb-4">
          <h2 className="serif text-2xl text-ink">
            {leader} <span className="text-muted text-base font-normal">leads</span>
          </h2>
          <span className="text-xs text-muted nums">
            {start} → {end} · {data.meta.n_periods} obs · wins across {COMPARE_METRICS.length} key metrics
          </span>
        </div>
        <div className="flex flex-wrap gap-3">
          {ranked.map((c, i) => (
            <div key={c} className="flex items-center gap-2 rounded-md border border-hair px-3 py-2">
              <span className="h-3 w-3 rounded-sm" style={{ background: colorOf(c) }} />
              <span className="text-sm text-ink font-medium">{c}</span>
              <span className="text-xs text-muted nums">{wins[c]} wins</span>
              {i === 0 && <span className="text-[0.6rem] uppercase tracking-wider text-pnl-pos font-semibold">best</span>}
            </div>
          ))}
        </div>
      </div>

      <Card title="Cumulative Return" subtitle="Overlaid growth, indexed to start">
        <TimeSeriesChart series={toSeries(data.series.cumulative)} height={340} valueFormat="percent" baseline theme={theme} />
      </Card>

      {/* Head-to-head key metrics */}
      <Card title="Head to Head" subtitle="Best in green, worst in red, per metric">
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-hair">
                <th className="text-left py-2 px-3 font-medium text-muted">Metric</th>
                {cols.map((c) => (
                  <th key={c} className="text-right py-2 px-3 font-medium">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm" style={{ background: colorOf(c) }} />
                      <span className="text-ink">{c}</span>
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(({ spec, vals, best, worst }) => (
                <tr key={spec.name} className="border-b border-hair/60">
                  <td className="py-1.5 px-3 text-ink">{spec.name}</td>
                  {vals.map(({ col, value }) => {
                    const isBest = col === best;
                    const isWorst = col === worst;
                    const cls = isBest
                      ? "text-pnl-pos font-semibold bg-pnl-pos/10"
                      : isWorst
                        ? "text-pnl-neg"
                        : "text-ink";
                    return (
                      <td key={col} className={`py-1.5 px-3 text-right nums ${cls}`}>
                        {fmtVal(value, spec.fmt)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Drawdown" subtitle="Underwater, overlaid">
        <TimeSeriesChart series={toSeries(data.series.drawdown)} height={260} valueFormat="percent" theme={theme} />
      </Card>

      <Card title="All Metrics" subtitle={`${data.metrics.rows.length} metrics · ${cols.join(" · ")}`}>
        <MetricsTable data={data.metrics} />
      </Card>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="min-h-[45vh] flex items-center justify-center text-muted">{children}</div>;
}
