import type { AnalyzeRequest } from "../api/types";

// A small deterministic LCG so the demo strategy is stable across reloads.
function lcg(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (1664525 * s + 1013904223) >>> 0;
    return s / 0xffffffff;
  };
}

// Box–Muller normal from a uniform generator.
function normal(rand: () => number, mu: number, sigma: number) {
  const u1 = Math.max(rand(), 1e-12);
  const u2 = rand();
  const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  return mu + sigma * z;
}

function businessDays(start: Date, n: number): string[] {
  const out: string[] = [];
  const d = new Date(start);
  while (out.length < n) {
    const dow = d.getUTCDay();
    if (dow !== 0 && dow !== 6) out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

/** A demo request: one strategy with mild momentum vs a benchmark. */
export function sampleRequest(n = 1000): AnalyzeRequest {
  const dates = businessDays(new Date(Date.UTC(2019, 0, 2)), n);
  const r1 = lcg(424242);
  const r2 = lcg(99); // benchmark
  const strat: number[] = [];
  const bench: number[] = [];
  let drift = 0.0006;
  for (let i = 0; i < n; i++) {
    // slowly varying drift gives realistic-looking equity curves
    drift += (normal(r1, 0, 1) * 0.00002);
    strat.push(normal(r1, drift, 0.011));
    bench.push(normal(r2, 0.0004, 0.009));
  }
  return {
    dates,
    returns: { Strategy: strat },
    benchmark: bench,
    benchmark_name: "Benchmark",
    rf: 0,
    compounded: true,
    periods_per_year: 252,
    rolling_window: 126,
  };
}
