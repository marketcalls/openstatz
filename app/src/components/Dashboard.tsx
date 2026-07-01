import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyze, analyzeSymbol, health } from "../api/client";
import type { SeriesPoint, AnalyzeRequest } from "../api/types";
import type { ReactNode } from "react";
import { parseReturnsCsv } from "../lib/parseCsv";
import { EMBEDDED_DATA, EMBEDDED_HEALTH, IS_STATIC_REPORT } from "../lib/embedded";
import { useTheme } from "../theme/ThemeProvider";
import { Card } from "./ui/Card";
import { SectionHeader } from "./SectionHeader";
import { StatGrid } from "./StatGrid";
import { TimeSeriesChart, type ChartSeries } from "./charts/TimeSeriesChart";
import { MonthlyHeatmap } from "./charts/MonthlyHeatmap";
import { WeeklyHeatmap } from "./charts/WeeklyHeatmap";
import { Distribution } from "./charts/Distribution";
import { BoxPlot } from "./charts/BoxPlot";
import { EoyBars } from "./charts/EoyBars";
import { MetricsTable } from "./table/MetricsTable";
import { EoyTable, WorstDrawdownsTable } from "./table/DataTables";
import { GROUPS } from "../lib/metrics";

const PERIODS = ["1y", "2y", "5y", "10y", "max"];

type AnalyzeReq =
  | { kind: "symbol"; symbol: string; benchmark: string; period: string }
  | { kind: "csv"; label: string; payload: AnalyzeRequest };

function reqKey(r: AnalyzeReq): string {
  return r.kind === "symbol"
    ? `s:${r.symbol}|${r.benchmark}|${r.period}`
    : `c:${r.label}:${r.payload.dates.length}`;
}
function reqLabel(r: AnalyzeReq): string {
  return r.kind === "symbol" ? r.symbol : r.label;
}

function seriesFor(
  bundle: Record<string, SeriesPoint[]> | undefined,
  cols: string[],
  colors: string[],
): ChartSeries[] {
  if (!bundle) return [];
  return cols
    .filter((c) => bundle[c])
    .map((c, i) => ({ name: c, data: bundle[c], color: colors[i % colors.length] }));
}

function GridLabel({ children }: { children: ReactNode }) {
  return <div className="eyebrow mb-2.5 mt-1">{children}</div>;
}

const FIELD =
  "bg-panel-2 border border-hair rounded-md px-3 py-2 text-sm text-ink nums focus:outline-none focus:border-ink transition-colors";
const LBL = "eyebrow mb-1.5 block";

function Tab({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-xs font-semibold uppercase tracking-[0.1em] px-3 py-1.5 rounded-md transition-colors ${
        active ? "bg-accent text-accent-ink" : "text-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function InputBar({
  current,
  onSubmit,
  busy,
}: {
  current: AnalyzeReq;
  onSubmit: (r: AnalyzeReq) => void;
  busy: boolean;
}) {
  const [mode, setMode] = useState<"symbol" | "csv">(current.kind);
  const [sym, setSym] = useState(
    current.kind === "symbol"
      ? { symbol: current.symbol, benchmark: current.benchmark, period: current.period }
      : { symbol: "RELIANCE.NS", benchmark: "^NSEI", period: "5y" },
  );
  const [csvError, setCsvError] = useState<string | null>(null);
  const [csvInfo, setCsvInfo] = useState<string | null>(null);

  const submitSymbol = (e: FormEvent) => {
    e.preventDefault();
    onSubmit({ kind: "symbol", ...sym });
  };

  const onFile = (file: File) => {
    setCsvError(null);
    setCsvInfo(null);
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const res = parseReturnsCsv(String(reader.result), file.name);
        setCsvInfo(
          `${res.strategyName}${res.benchmarkName ? " vs " + res.benchmarkName : ""} · ${res.rows} rows`,
        );
        onSubmit({ kind: "csv", label: file.name, payload: res.request });
      } catch (err) {
        setCsvError(String((err as Error).message));
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="no-print card rounded-lg px-4 py-3.5">
      <div className="flex gap-1 mb-3">
        <Tab active={mode === "symbol"} onClick={() => setMode("symbol")}>Symbol</Tab>
        <Tab active={mode === "csv"} onClick={() => setMode("csv")}>Upload CSV</Tab>
      </div>

      {mode === "symbol" ? (
        <form onSubmit={submitSymbol} className="flex flex-wrap items-end gap-3">
          <label>
            <span className={LBL}>Symbol</span>
            <input className={`${FIELD} w-44`} value={sym.symbol} placeholder="RELIANCE.NS"
              onChange={(e) => setSym({ ...sym, symbol: e.target.value.toUpperCase() })} />
          </label>
          <label>
            <span className={LBL}>Benchmark</span>
            <input className={`${FIELD} w-36`} value={sym.benchmark} placeholder="^NSEI"
              onChange={(e) => setSym({ ...sym, benchmark: e.target.value.toUpperCase() })} />
          </label>
          <label>
            <span className={LBL}>Period</span>
            <select className={`${FIELD} w-24`} value={sym.period}
              onChange={(e) => setSym({ ...sym, period: e.target.value })}>
              {PERIODS.map((p) => (<option key={p} value={p}>{p}</option>))}
            </select>
          </label>
          <button type="submit" disabled={busy}
            className="px-5 py-2 rounded-md bg-accent text-accent-ink text-sm font-semibold disabled:opacity-50 hover:brightness-110 transition">
            {busy ? "Loading…" : "Analyze"}
          </button>
        </form>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <label className="px-4 py-2 rounded-md border border-hair-strong text-sm text-ink cursor-pointer hover:border-ink transition-colors">
            Choose CSV…
            <input type="file" accept=".csv,text/csv,text/plain" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
          </label>
          <span className="text-xs text-muted">
            Columns: <span className="nums text-ink">date, return[, benchmark]</span> (decimals, %,
            or prices). Header optional.
          </span>
          {csvInfo && <span className="text-xs text-pnl-pos nums">Loaded {csvInfo}</span>}
          {csvError && <span className="text-xs text-pnl-neg">{csvError}</span>}
        </div>
      )}
    </div>
  );
}

export function Dashboard() {
  const { theme } = useTheme();
  const [request, setRequest] = useState<AnalyzeReq>({
    kind: "symbol",
    symbol: "RELIANCE.NS",
    benchmark: "^NSEI",
    period: "5y",
  });
  // Static-report mode: data is baked into the file, so never hit the network —
  // seed the query with the embedded bundle and disable fetching.
  const q = useQuery({
    queryKey: ["analyze", reqKey(request)],
    queryFn: () =>
      request.kind === "symbol"
        ? analyzeSymbol({
            symbol: request.symbol,
            benchmark_symbol: request.benchmark || null,
            period: request.period,
          })
        : analyze(request.payload),
    retry: false,
    enabled: !IS_STATIC_REPORT,
    initialData: EMBEDDED_DATA,
  });
  const h = useQuery({
    queryKey: ["health"],
    queryFn: health,
    retry: false,
    enabled: !IS_STATIC_REPORT,
    initialData: EMBEDDED_HEALTH,
  });

  // No input bar in a static report — there's no backend to re-query.
  const bar = IS_STATIC_REPORT ? null : (
    <InputBar current={request} onSubmit={setRequest} busy={q.isFetching} />
  );

  if (q.isLoading) {
    return (
      <div className="space-y-6">
        {bar}
        <Centered>Analyzing {reqLabel(request)} …</Centered>
      </div>
    );
  }
  if (q.isError) {
    return (
      <div className="space-y-6">
        {bar}
        <Centered>
          <div className="max-w-lg text-center">
            <p className="text-pnl-neg mb-2 serif text-lg">Could not analyze {reqLabel(request)}.</p>
            <p className="text-muted text-sm">
              For a symbol, check the ticker. For a CSV, expect columns{" "}
              <code className="text-ink nums">date, return[, benchmark]</code>. The backend must be
              running (<code className="text-ink nums">openstatz serve</code>).
            </p>
            <p className="text-faint text-xs mt-3 nums">{String(q.error)}</p>
          </div>
        </Centered>
      </div>
    );
  }

  const data = q.data!;
  const primary = data.meta.columns[0];
  const benchCol = data.meta.has_benchmark
    ? (data.metrics.columns.find((c) => c !== primary) ?? null)
    : null;

  const inkLine = "var(--text)";
  const accentLine = "var(--text)";
  const neg = "var(--pnl-neg)";
  const benchmarkBlue = "var(--benchmark)";
  const equityColors = [inkLine, benchmarkBlue];

  const startDate = new Date(data.meta.start * 1000).toISOString().slice(0, 10);
  const endDate = new Date(data.meta.end * 1000).toISOString().slice(0, 10);

  const daily = (data.series.daily_returns?.[primary] ?? [])
    .map((p) => p.value)
    .filter((v): v is number => v !== null);
  const monthlyVals = data.tables.monthly_heatmap.cells
    .map((c) => c.value)
    .filter((v): v is number => v !== null);

  const equityCols = [primary, ...(benchCol ? [benchCol] : [])];

  return (
    <div className="space-y-12">
      {bar}

      {/* Instrument header */}
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-hair pb-4">
        <h1 className="serif text-4xl text-ink leading-none">{primary}</h1>
        <span className="text-xs text-muted nums">
          {startDate} → {endDate} · {data.meta.n_periods} obs
          {benchCol ? ` · vs ${benchCol}` : ""}
        </span>
      </div>

      {/* 01 Overview */}
      <section id="overview">
        <SectionHeader n="01" title="Overview" subtitle="Headline risk & return" />
        <StatGrid data={data} specs={GROUPS.overview} primary={primary} benchCol={benchCol} />
      </section>

      {/* 02 Performance */}
      <section id="performance">
        <SectionHeader n="02" title="Performance" subtitle="Equity curve & rolling stats" />
        <Card title="Cumulative Return" subtitle="Compounded growth, indexed to start">
          <TimeSeriesChart
            series={seriesFor(data.series.cumulative, equityCols, equityColors).map((s, i) =>
              i === 0
                ? { ...s, type: "area" as const }
                : { ...s, type: "line" as const, lineWidth: 1.5 },
            )}
            height={320}
            valueFormat="percent"
            baseline
            theme={theme}
          />
        </Card>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <Card title="Rolling Sharpe" subtitle="126-period window">
            <TimeSeriesChart
              series={seriesFor(data.series.rolling_sharpe, [primary], [accentLine])}
              height={220}
              valueFormat="number"
              baseline
              theme={theme}
            />
          </Card>
          <Card title="Rolling Volatility" subtitle="Annualized, 126-period">
            <TimeSeriesChart
              series={seriesFor(data.series.rolling_volatility, [primary], [accentLine])}
              height={220}
              valueFormat="percent"
              theme={theme}
            />
          </Card>
        </div>
        <div className="mt-6">
          <GridLabel>Period Returns</GridLabel>
          <StatGrid data={data} specs={GROUPS.periods} primary={primary} benchCol={benchCol} />
        </div>
      </section>

      {/* 03 Risk */}
      <section id="risk">
        <SectionHeader n="03" title="Risk" subtitle="Drawdown, tails & exposure" />
        <Card title="Drawdown" subtitle="Underwater — peak-to-trough decline">
          <TimeSeriesChart
            series={seriesFor(data.series.drawdown, [primary], [neg]).map((s) => ({
              ...s,
              type: "baseline" as const,
            }))}
            height={240}
            valueFormat="percent"
            theme={theme}
          />
        </Card>
        <div className="mt-6">
          <StatGrid data={data} specs={GROUPS.risk} primary={primary} benchCol={benchCol} />
        </div>
        {benchCol && (
          <div className="mt-6">
            <GridLabel>vs Benchmark · {benchCol}</GridLabel>
            <StatGrid data={data} specs={GROUPS.benchmark} primary={primary} benchCol={benchCol} />
            {data.series.rolling_beta && (
              <Card title="Rolling Beta" subtitle={`vs ${benchCol}, 126-period`} className="mt-4">
                <TimeSeriesChart
                  series={seriesFor(data.series.rolling_beta, [primary], [accentLine])}
                  height={200}
                  valueFormat="number"
                  baseline
                  theme={theme}
                />
              </Card>
            )}
          </div>
        )}
        <Card title="Worst Drawdowns" subtitle="Deepest peak-to-recovery episodes" className="mt-6">
          <WorstDrawdownsTable rows={data.tables.worst_drawdowns.rows} />
        </Card>
      </section>

      {/* 04 Monthly */}
      <section id="monthly">
        <SectionHeader n="04" title="Monthly" subtitle="Seasonality & annual returns" />
        <Card title="Monthly Returns" subtitle="Calendar heatmap, % per month">
          <MonthlyHeatmap data={data.tables.monthly_heatmap} />
        </Card>
        <Card title="Weekly Returns" subtitle="Select a year to see every week" className="mt-4">
          <WeeklyHeatmap key={primary} data={data.tables.weekly_heatmap} />
        </Card>
        <div className="mt-6">
          <StatGrid data={data} specs={GROUPS.monthly} primary={primary} benchCol={benchCol} />
        </div>
        <Card title="Annual Returns" subtitle="End-of-year, strategy vs benchmark" className="mt-4">
          <EoyBars
            rows={data.tables.eoy.rows}
            benchLabel={benchCol ?? "Benchmark"}
            hasBenchmark={data.meta.has_benchmark}
          />
          <div className="mt-4 border-t border-hair pt-2">
            <EoyTable rows={data.tables.eoy.rows} hasBenchmark={data.meta.has_benchmark} />
          </div>
        </Card>
      </section>

      {/* 05 Distribution */}
      <section id="distribution">
        <SectionHeader n="05" title="Distribution" subtitle="Return shape & tails" />
        <StatGrid data={data} specs={GROUPS.distribution} primary={primary} benchCol={benchCol} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
          <Card title="Daily Returns" subtitle="Histogram with mean marker">
            <Distribution key={theme} values={daily} />
          </Card>
          <Card title="Returns Spread" subtitle="Daily vs monthly quantiles">
            <BoxPlot
              key={theme}
              boxes={[
                { label: "Daily", values: daily },
                { label: "Monthly", values: monthlyVals },
              ]}
            />
          </Card>
        </div>
      </section>

      {/* 06 Metrics */}
      <section id="metrics">
        <SectionHeader
          n="06"
          title="Metrics"
          subtitle={`${data.metrics.rows.length} metrics · ${data.metrics.columns.join(" · ")}`}
        />
        <Card>
          <MetricsTable data={data.metrics} />
        </Card>
      </section>

      <StatusFooter health={h.data} />
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[55vh] flex items-center justify-center text-muted">{children}</div>
  );
}

function StatusFooter({ health }: { health?: { version: string } }) {
  return (
    <div className="no-print text-xs text-faint flex items-center gap-3 pt-4 border-t border-hair">
      <span className="serif text-sm text-muted">OpenStatz</span>
      <span className="nums">{health?.version ?? ""}</span>
      <span>· kernels: numpy</span>
      <a
        href="https://openalgo.in"
        target="_blank"
        rel="noreferrer"
        className="ml-auto hover:text-ink transition-colors"
      >
        openalgo.in
      </a>
    </div>
  );
}
