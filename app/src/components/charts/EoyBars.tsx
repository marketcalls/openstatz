import { scaleBand, scaleLinear } from "d3-scale";
import { max as d3max, min as d3min, mean as d3mean } from "d3-array";
import type { EoyRow } from "../../api/types";
import { fmtPct } from "../../lib/format";

// End-of-year returns: grouped bars (strategy vs benchmark) per year, with a
// zero line and the strategy's mean as a dashed reference. Bespoke SVG so it
// stays crisp in PDF and re-themes with CSS variables.
export function EoyBars({
  rows,
  benchLabel,
  hasBenchmark,
}: {
  rows: EoyRow[];
  benchLabel: string;
  hasBenchmark: boolean;
}) {
  const data = rows.filter((r) => r.strategy !== null);
  if (data.length === 0) return <div className="text-muted text-sm">No annual data</div>;

  const width = 680;
  const height = 300;
  const m = { top: 26, right: 14, bottom: 34, left: 44 };
  const iw = width - m.left - m.right;
  const ih = height - m.top - m.bottom;

  const years = data.map((d) => d.year);
  const x = scaleBand<string>().domain(years).range([0, iw]).padding(0.3);
  const vals = data.flatMap((d) => [
    d.strategy ?? 0,
    ...(hasBenchmark ? [d.benchmark ?? 0] : []),
  ]);
  const lo = Math.min(0, d3min(vals) ?? 0);
  const hi = Math.max(0, d3max(vals) ?? 0);
  const y = scaleLinear().domain([lo, hi]).range([ih, 0]).nice();
  const sub = scaleBand<string>()
    .domain(hasBenchmark ? ["strategy", "benchmark"] : ["strategy"])
    .range([0, x.bandwidth()])
    .padding(0.12);

  const avg = d3mean(data.map((d) => d.strategy ?? 0)) ?? 0;
  const ticks = y.ticks(6);
  const stratColor = "var(--text)";
  const benchColor = "var(--benchmark)";

  const bar = (gx: number, key: "strategy" | "benchmark", v: number, fill: string, label: string) => (
    <rect
      x={gx + (sub(key) ?? 0)}
      y={Math.min(y(v), y(0))}
      width={sub.bandwidth()}
      height={Math.abs(y(v) - y(0))}
      fill={fill}
      rx={1}
    >
      <title>{label}</title>
    </rect>
  );

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="EOY returns vs benchmark">
      <g transform={`translate(${m.left},${m.top})`}>
        {/* legend */}
        <g transform={`translate(${iw - (hasBenchmark ? 150 : 70)}, -16)`} style={{ fontFamily: "var(--font-sans)" }}>
          <rect width={10} height={10} fill={stratColor} rx={1} />
          <text x={14} y={9} style={{ fontSize: 10, fill: "var(--text-muted)" }}>Strategy</text>
          {hasBenchmark && (
            <>
              <rect x={78} width={10} height={10} fill={benchColor} rx={1} />
              <text x={92} y={9} style={{ fontSize: 10, fill: "var(--text-muted)" }}>{benchLabel}</text>
            </>
          )}
        </g>

        {ticks.map((t) => (
          <g key={t}>
            <line x1={0} x2={iw} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
            <text x={-8} y={y(t) + 3} textAnchor="end" style={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--text-faint)" }}>
              {(t * 100).toFixed(0)}%
            </text>
          </g>
        ))}

        <line x1={0} x2={iw} y1={y(0)} y2={y(0)} stroke="var(--border-strong)" />
        <line x1={0} x2={iw} y1={y(avg)} y2={y(avg)} stroke="var(--pnl-neg)" strokeDasharray="5 4" strokeWidth={1.3}>
          <title>{`Strategy avg: ${fmtPct(avg)}`}</title>
        </line>

        {data.map((d) => {
          const gx = x(d.year) ?? 0;
          return (
            <g key={d.year}>
              {bar(gx, "strategy", d.strategy ?? 0, stratColor, `${d.year} Strategy: ${fmtPct(d.strategy)}`)}
              {hasBenchmark && d.benchmark != null &&
                bar(gx, "benchmark", d.benchmark, benchColor, `${d.year} ${benchLabel}: ${fmtPct(d.benchmark)}`)}
              <text
                x={gx + x.bandwidth() / 2}
                y={ih + 18}
                textAnchor="middle"
                style={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--text-muted)" }}
              >
                {d.year}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
