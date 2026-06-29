import type { AnalysisResponse, MetricRow } from "../api/types";

// reports.metrics uses some non-ASCII labels (e.g. "CAGR﹪" with U+FE6A, "R^2").
// Normalize away percent signs / case / spacing so lookups by a clean name still
// resolve — this is why the old "CAGR" card showed nothing.
const STRIP = /[﹪%]/g;

export function normLabel(s: string): string {
  return s.replace(STRIP, "").replace(/\s+/g, " ").trim().toLowerCase();
}

export function findRow(data: AnalysisResponse, query: string): MetricRow | undefined {
  const n = normLabel(query);
  return data.metrics.rows.find((r) => normLabel(r.label) === n);
}

export interface MetricView {
  found: boolean;
  value: number | null;
  benchValue: number | null;
}

export function getMetric(
  data: AnalysisResponse,
  query: string,
  col: string,
  benchCol: string | null,
): MetricView {
  const row = findRow(data, query);
  if (!row) return { found: false, value: null, benchValue: null };
  return {
    found: true,
    value: row.values[col] ?? null,
    benchValue: benchCol ? (row.values[benchCol] ?? null) : null,
  };
}

export type Fmt = "pct" | "num" | "int";

// A card spec: `name` shows on the tile, `metric` is the lookup query, `fmt`
// formats the numeric value, `desc` is a static subline when there's no
// benchmark, `tone` enables P&L (green/red) coloring.
export interface StatSpec {
  name: string;
  metric: string;
  fmt: Fmt;
  desc?: string;
  tone?: boolean;
}

const P = (name: string, metric: string, opts: Partial<StatSpec> = {}): StatSpec => ({
  name,
  metric,
  fmt: "pct",
  tone: true,
  ...opts,
});
const N = (name: string, metric: string, desc?: string): StatSpec => ({
  name,
  metric,
  fmt: "num",
  desc,
});

export const GROUPS: Record<string, StatSpec[]> = {
  overview: [
    P("Cumulative Return", "Cumulative Return", { desc: "total" }),
    P("CAGR", "CAGR", { desc: "annualized" }),
    N("Sharpe", "Sharpe", "risk-adjusted"),
    N("Sortino", "Sortino", "downside-adjusted"),
    P("Max Drawdown", "Max Drawdown", { desc: "peak-to-trough" }),
    P("Volatility", "Volatility (ann.)", { tone: false, desc: "annualized" }),
    N("Calmar", "Calmar", "CAGR / MaxDD"),
    N("Smart Sharpe", "Smart Sharpe", "autocorr-adjusted"),
    N("Omega", "Omega", "gain / pain"),
    N("Recovery Factor", "Recovery Factor", "total / MaxDD"),
    N("Ulcer Index", "Ulcer Index", "depth × duration"),
    P("Time in Market", "Time in Market", { tone: false, desc: "exposure" }),
  ],
  periods: [
    P("MTD", "MTD"),
    P("YTD", "YTD"),
    P("3 Month", "3M"),
    P("6 Month", "6M"),
    P("1 Year", "1Y"),
    P("3Y (ann.)", "3Y (ann.)"),
    P("5Y (ann.)", "5Y (ann.)"),
    P("All-time", "All-time (ann.)"),
    P("Best Year", "Best Year"),
    P("Worst Year", "Worst Year"),
  ],
  risk: [
    P("Max Drawdown", "Max Drawdown", { desc: "peak-to-trough" }),
    P("Avg Drawdown", "Avg. Drawdown", { desc: "mean depth" }),
    { name: "Longest DD", metric: "Longest DD Days", fmt: "int", desc: "days underwater" },
    P("Daily VaR", "Daily Value-at-Risk", { desc: "95% 1-day" }),
    P("Expected Shortfall", "Expected Shortfall (cVaR)", { desc: "cVaR" }),
    P("Volatility", "Volatility (ann.)", { tone: false, desc: "annualized" }),
    P("Risk of Ruin", "Risk of Ruin", { tone: false, desc: "probability" }),
    N("Skew", "Skew", "asymmetry"),
    N("Kurtosis", "Kurtosis", "tailedness"),
    N("Tail Ratio", "Tail Ratio", "right / left"),
  ],
  benchmark: [
    N("Beta", "Beta", "market sensitivity"),
    N("Alpha", "Alpha", "excess return"),
    N("Correlation", "Correlation", "to benchmark"),
    N("R²", "R^2", "explained variance"),
    N("Information Ratio", "Information Ratio", "active / tracking err"),
    N("Treynor Ratio", "Treynor Ratio", "return / beta"),
  ],
  monthly: [
    P("Best Month", "Best Month"),
    P("Worst Month", "Worst Month"),
    P("Avg Up Month", "Avg. Up Month"),
    P("Avg Down Month", "Avg. Down Month"),
    P("Win Months", "Win Month", { tone: false, desc: "positive" }),
    P("Win Quarters", "Win Quarter", { tone: false, desc: "positive" }),
  ],
  trade: [
    P("Win Days", "Win Days", { tone: false, desc: "positive" }),
    N("Payoff Ratio", "Payoff Ratio", "avg win / avg loss"),
    N("Profit Factor", "Profit Factor", "gross win / loss"),
    N("Gain / Pain", "Gain/Pain Ratio", "sum win / sum loss"),
    P("Kelly Criterion", "Kelly Criterion", { desc: "optimal size" }),
    P("Avg Win", "Avg. Win", { desc: "per day" }),
    P("Avg Loss", "Avg. Loss", { desc: "per day" }),
    N("Common Sense Ratio", "Common Sense Ratio", "tail × profit"),
  ],
  distribution: [
    P("Best Day", "Best Day"),
    P("Worst Day", "Worst Day"),
    N("Skew", "Skew", "asymmetry"),
    N("Kurtosis", "Kurtosis", "tailedness"),
    N("Outlier Win", "Outlier Win Ratio", "99th pctile"),
    N("Outlier Loss", "Outlier Loss Ratio", "1st pctile"),
  ],
};
