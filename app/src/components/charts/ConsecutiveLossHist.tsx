import { scaleBand, scaleLinear } from "d3-scale";
import { max as d3max } from "d3-array";
import type { ConsecutiveLosses } from "../../api/types";

// Distribution of consecutive-losing-period streak lengths: how often a
// 1-period loss, a 2-period loss, ... occurred. Shows the *shape* of losing
// runs (and the worst / average streak) instead of only the single maximum.
// Bespoke SVG so it stays crisp in PDF export and re-themes via CSS variables.
export function ConsecutiveLossHist({ data }: { data: ConsecutiveLosses }) {
  const bins = data.bins ?? [];
  if (bins.length === 0) {
    return <div className="text-muted text-sm">No losing streaks</div>;
  }

  const width = 680;
  const height = 260;
  const m = { top: 20, right: 14, bottom: 34, left: 40 };
  const iw = width - m.left - m.right;
  const ih = height - m.top - m.bottom;

  const labels = bins.map((b) => String(b.length));
  const x = scaleBand<string>().domain(labels).range([0, iw]).padding(0.25);
  const hi = d3max(bins, (b) => b.count) ?? 1;
  const y = scaleLinear().domain([0, hi]).range([ih, 0]).nice();
  const ticks = y.ticks(5);
  const neg = "var(--pnl-neg)";

  return (
    <div>
      <svg
        width="100%"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Consecutive losing-streak length distribution"
      >
        <g transform={`translate(${m.left},${m.top})`}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={0} x2={iw} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
              <text
                x={-8}
                y={y(t) + 3}
                textAnchor="end"
                style={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--text-faint)" }}
              >
                {t}
              </text>
            </g>
          ))}

          {bins.map((b) => {
            const gx = x(String(b.length)) ?? 0;
            return (
              <g key={b.length}>
                <rect
                  x={gx}
                  y={y(b.count)}
                  width={x.bandwidth()}
                  height={ih - y(b.count)}
                  fill={neg}
                  opacity={0.85}
                  rx={1}
                >
                  <title>{`${b.length}-period streak: ${b.count}×`}</title>
                </rect>
                <text
                  x={gx + x.bandwidth() / 2}
                  y={ih + 18}
                  textAnchor="middle"
                  style={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--text-muted)" }}
                >
                  {b.length}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      <div className="mt-2 flex gap-6 text-xs text-muted nums">
        <span>Streaks: <span className="text-ink">{data.count}</span></span>
        <span>Longest: <span className="text-ink">{data.max}</span></span>
        {data.avg !== null && (
          <span>Average: <span className="text-ink">{data.avg.toFixed(2)}</span></span>
        )}
        <span className="text-faint">length = consecutive losing periods</span>
      </div>
    </div>
  );
}
