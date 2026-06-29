import { bin as d3bin, max as d3max, mean as d3mean } from "d3-array";
import { scaleLinear } from "d3-scale";
import { fmtPct } from "../../lib/format";

// Daily-returns distribution (histogram), bars colored by P&L sign, with a mean
// marker. Bespoke SVG so it stays crisp in PDF export.

export function Distribution({
  values,
  height = 220,
  bins = 41,
}: {
  values: number[];
  height?: number;
  bins?: number;
}) {
  const data = values.filter((v) => Number.isFinite(v));
  if (data.length === 0) return <div className="text-muted text-sm">No data</div>;

  const width = 520;
  const m = { top: 10, right: 12, bottom: 26, left: 12 };
  const iw = width - m.left - m.right;
  const ih = height - m.top - m.bottom;

  const lo = Math.min(...data);
  const hi = Math.max(...data);
  const x = scaleLinear().domain([lo, hi]).range([0, iw]).nice();

  const binner = d3bin<number, number>().domain(x.domain() as [number, number]).thresholds(bins);
  const buckets = binner(data);
  const yMax = d3max(buckets, (b) => b.length) || 1;
  const y = scaleLinear().domain([0, yMax]).range([ih, 0]);

  const avg = d3mean(data) ?? 0;
  const ticks = x.ticks(6);

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Returns distribution">
      <g transform={`translate(${m.left},${m.top})`}>
        {buckets.map((b, i) => {
          const x0 = x(b.x0 ?? 0);
          const x1 = x(b.x1 ?? 0);
          const w = Math.max(1, x1 - x0 - 1);
          const h = ih - y(b.length);
          const center = ((b.x0 ?? 0) + (b.x1 ?? 0)) / 2;
          const fill = center >= 0 ? "var(--pnl-pos)" : "var(--pnl-neg)";
          return (
            <rect
              key={i}
              x={x0}
              y={y(b.length)}
              width={w}
              height={h}
              fill={fill}
              opacity={0.78}
            >
              <title>{`${fmtPct(center)} · ${b.length}`}</title>
            </rect>
          );
        })}
        {/* mean marker */}
        <line
          x1={x(avg)}
          x2={x(avg)}
          y1={0}
          y2={ih}
          stroke="var(--accent)"
          strokeWidth={1.5}
          strokeDasharray="3 3"
        />
        {/* x axis */}
        <line x1={0} x2={iw} y1={ih} y2={ih} stroke="var(--border)" />
        {ticks.map((t) => (
          <text
            key={t}
            x={x(t)}
            y={ih + 16}
            textAnchor="middle"
            style={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--text-faint)" }}
          >
            {(t * 100).toFixed(1)}%
          </text>
        ))}
      </g>
    </svg>
  );
}
