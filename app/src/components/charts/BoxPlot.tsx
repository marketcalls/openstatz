import { quantileSorted, max as d3max, min as d3min } from "d3-array";
import { scaleLinear } from "d3-scale";
import { fmtPct } from "../../lib/format";

// Quantile box/whisker of (typically monthly) returns. Bespoke SVG: low
// cardinality, exact, themeable.

interface Box {
  label: string;
  values: number[];
}

function stats(values: number[]) {
  const v = values.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  return {
    min: d3min(v) ?? 0,
    q1: quantileSorted(v, 0.25) ?? 0,
    med: quantileSorted(v, 0.5) ?? 0,
    q3: quantileSorted(v, 0.75) ?? 0,
    max: d3max(v) ?? 0,
  };
}

export function BoxPlot({ boxes, height = 200 }: { boxes: Box[]; height?: number }) {
  const valid = boxes.filter((b) => b.values.some((v) => Number.isFinite(v)));
  if (valid.length === 0) return <div className="text-muted text-sm">No data</div>;

  const width = 520;
  const m = { top: 12, right: 16, bottom: 26, left: 64 };
  const iw = width - m.left - m.right;
  const ih = height - m.top - m.bottom;

  const computed = valid.map((b) => ({ label: b.label, s: stats(b.values) }));
  const lo = Math.min(...computed.map((c) => c.s.min));
  const hi = Math.max(...computed.map((c) => c.s.max));
  const x = scaleLinear().domain([lo, hi]).range([0, iw]).nice();

  const rowH = ih / computed.length;
  const boxH = Math.min(22, rowH * 0.5);
  const ticks = x.ticks(6);

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Returns box plot">
      <g transform={`translate(${m.left},${m.top})`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={0} y2={ih} stroke="var(--grid)" />
            <text
              x={x(t)}
              y={ih + 16}
              textAnchor="middle"
              style={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--text-faint)" }}
            >
              {(t * 100).toFixed(1)}%
            </text>
          </g>
        ))}
        {/* zero reference */}
        {lo < 0 && hi > 0 && (
          <line x1={x(0)} x2={x(0)} y1={0} y2={ih} stroke="var(--border-strong)" strokeDasharray="2 2" />
        )}
        {computed.map((c, i) => {
          const cy = i * rowH + rowH / 2;
          const accent = c.s.med >= 0 ? "var(--pnl-pos)" : "var(--pnl-neg)";
          return (
            <g key={c.label}>
              <text
                x={-10}
                y={cy + 3}
                textAnchor="end"
                style={{ fontSize: 11, fill: "var(--text-muted)" }}
              >
                {c.label}
              </text>
              {/* whiskers */}
              <line x1={x(c.s.min)} x2={x(c.s.max)} y1={cy} y2={cy} stroke="var(--text-faint)" />
              <line x1={x(c.s.min)} x2={x(c.s.min)} y1={cy - 5} y2={cy + 5} stroke="var(--text-faint)" />
              <line x1={x(c.s.max)} x2={x(c.s.max)} y1={cy - 5} y2={cy + 5} stroke="var(--text-faint)" />
              {/* box */}
              <rect
                x={x(c.s.q1)}
                y={cy - boxH / 2}
                width={Math.max(1, x(c.s.q3) - x(c.s.q1))}
                height={boxH}
                fill={accent}
                opacity={0.22}
                stroke={accent}
              />
              {/* median */}
              <line
                x1={x(c.s.med)}
                x2={x(c.s.med)}
                y1={cy - boxH / 2}
                y2={cy + boxH / 2}
                stroke={accent}
                strokeWidth={2}
              >
                <title>{`median ${fmtPct(c.s.med)}`}</title>
              </line>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
