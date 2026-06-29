import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  LineSeries,
  AreaSeries,
  BaselineSeries,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";

// ── THE ADAPTER BOUNDARY ──────────────────────────────────────────────────
// This is the ONLY module that imports lightweight-charts. Everything else
// speaks the normalized `{ time, value }` contract below, so swapping in
// openalgo-charts later is a one-file change (architecture sections 3.3 / 8).

export interface NormalizedPoint {
  time: number; // epoch seconds
  value: number | null;
}

export interface ChartSeries {
  name: string;
  data: NormalizedPoint[];
  color?: string;
  type?: "line" | "area" | "baseline";
  lineWidth?: number;
}

// Resolve ANY css color (var(), hsl(), hex, name) to a concrete "rgb(r, g, b)"
// by letting the browser compute it. lightweight-charts draws on a canvas whose
// gradient stops don't accept var()/color-mix(), so we must hand it solid rgb.
function toRgb(color: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  const el = document.createElement("span");
  el.style.color = color;
  el.style.display = "none";
  document.body.appendChild(el);
  const rgb = getComputedStyle(el).color;
  el.remove();
  return rgb && rgb.startsWith("rgb") ? rgb : fallback;
}

function cssVar(name: string, fallback: string): string {
  return toRgb(`var(${name})`, fallback);
}

// "rgb(r, g, b)" -> "rgba(r, g, b, a)" for translucent area fills.
function rgba(rgb: string, a: number): string {
  return rgb.replace(/^rgb\(/, "rgba(").replace(/\)$/, `, ${a})`);
}

export function TimeSeriesChart({
  series,
  height = 260,
  valueFormat = "percent",
  baseline = false,
  theme,
}: {
  series: ChartSeries[];
  height?: number;
  valueFormat?: "percent" | "number";
  baseline?: boolean; // draw a zero reference line
  theme?: string; // changes => rebuild so canvas colors re-read CSS vars
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const ink = cssVar("--text", "#e7eaf0");
    const muted = cssVar("--text-faint", "#5b6275");
    const grid = cssVar("--grid", "rgba(255,255,255,0.05)");

    const chart = createChart(el, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: muted,
        fontFamily:
          'ui-monospace, "JetBrains Mono", "SF Mono", monospace',
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "transparent" },
        horzLines: { color: grid },
      },
      rightPriceScale: { borderColor: "transparent" },
      timeScale: { borderColor: "transparent", fixLeftEdge: true, fixRightEdge: true },
      crosshair: { mode: 0 },
      localization: {
        priceFormatter:
          valueFormat === "percent"
            ? (v: number) => `${(v * 100).toFixed(1)}%`
            : (v: number) => v.toFixed(2),
      },
    });
    chartRef.current = chart;

    series.forEach((s, i) => {
      const fallback = i === 0 ? "rgb(30, 30, 35)" : "rgb(120, 120, 140)";
      const color = toRgb(s.color ?? "var(--text)", fallback);
      const data = s.data
        .filter((p) => p.value !== null && Number.isFinite(p.value))
        .map((p) => ({ time: p.time as UTCTimestamp, value: p.value as number }));
      const lineWidth = (s.lineWidth ?? 2) as 1 | 2 | 3 | 4;

      if (s.type === "baseline") {
        // Shades the region BETWEEN the zero baseline and the line — i.e. the
        // underwater area for a drawdown plot (values are <= 0).
        const bs = chart.addSeries(BaselineSeries, {
          baseValue: { type: "price", price: 0 },
          topLineColor: color,
          topFillColor1: rgba(color, 0),
          topFillColor2: rgba(color, 0),
          bottomLineColor: color,
          bottomFillColor1: rgba(color, 0.06),
          bottomFillColor2: rgba(color, 0.32),
          lineWidth,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        bs.setData(data);
      } else if (s.type === "area") {
        const as = chart.addSeries(AreaSeries, {
          lineColor: color,
          topColor: rgba(color, 0.22),
          bottomColor: rgba(color, 0.02),
          lineWidth,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        as.setData(data);
      } else {
        const ls = chart.addSeries(LineSeries, {
          color,
          lineWidth,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        ls.setData(data);
        if (baseline) {
          ls.createPriceLine({
            price: 0,
            color: muted,
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: false,
            title: "",
          });
        }
      }
    });

    chart.timeScale().fitContent();
    void ink;

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth });
      chart.timeScale().fitContent();
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [series, height, valueFormat, baseline, theme]);

  return <div ref={containerRef} style={{ width: "100%" }} />;
}
