# OpenStatz — 2026 Rebuild Architecture

> A modern rebuild of QuantStats: same trusted analytics, a fast pandas+Numba core,
> and an optional modern web UI — with **100% output parity** to the original library.

> **Implementation note (2026-06-29):** Numba acceleration is **deferred for the time being** —
> it creates compatibility friction with current NumPy. The loop-shaped kernels described below
> (`openstatz/_kernels.py`) are implemented in **pure vectorized NumPy** instead; they are still
> gated by the parity suite and already deliver the key speedups (e.g. ~11x on the Monte Carlo
> per-column max-drawdown). Numba can be reintroduced later behind the same parity gate without
> changing any public API.

---

## 0. TL;DR

- **OpenStatz stays a normal Python library.** `pip install openstatz` → `import openstatz as os`
  behaves exactly like `quantstats` (same functions, same numbers, `extend_pandas()`).
- **The web UI is an optional layer**, not a replacement. `pip install openstatz[app]`
  adds a FastAPI server + a modern React UI that *imports the same library core*.
- **Compute stays on pandas** (not Polars) for guaranteed numerical parity, with **NumPy +
  Numba** accelerating only a handful of loop-shaped kernels — each gated by a parity test.
- **Parity is enforced, not promised**: a golden-master suite snapshots the current
  QuantStats output and CI asserts OpenStatz reproduces every metric (`rtol=1e-9`) and
  every chart's underlying data series.

---

## 1. Can it run as a library? (Yes — both at once)

OpenStatz is **library-first**. The layering guarantees three usage modes from one codebase:

| Mode | Install | Usage |
|---|---|---|
| Library (drop-in) | `pip install openstatz` | `import openstatz as os; os.stats.sharpe(r)` |
| Pandas extension | `pip install openstatz` | `os.extend_pandas(); r.sharpe()` |
| Web app | `pip install openstatz[app]` | `openstatz serve` → browser UI |

> **Alias caveat:** the documented alias is `os` (`import openstatz as os`). This intentionally
> shadows Python's standard-library `os` module within any file that uses it — `os.path`,
> `os.getcwd()`, etc. will not be available there. Code that needs the stdlib alongside OpenStatz
> should `import os as _os` (or import OpenStatz under a different name in that file). The library
> itself never relies on the alias, so this only affects user scripts.

The core never imports FastAPI, matplotlib-for-web, or any UI dependency. I/O and presentation
live in adapters. This is what keeps the library lean and embeddable while the app sits on top.

---

## 2. Design principle: reuse, don't reimplement

100% numerical parity is only *free* when the new core runs the **same engine** on the same
data. Reimplementing ~80 metric functions on a different engine (e.g. Polars) would mean proving
bit-identical results despite differences in NaN handling, `ddof`, rolling-window edges,
percentile interpolation, and float reduction order. Staying on **pandas** removes that risk.

> **Rule: the metric math is reused from the proven QuantStats implementation. OpenStatz adds a
> modern packaging, an API adapter, a web UI, and *gated* Numba acceleration — it does not
> re-derive the numbers.**

---

## 3. Final stack decisions

### 3.1 Compute core (Python)
- **Python** >= 3.10
- **pandas** (primary engine — same as QuantStats, for parity & compatibility)
- **numpy** (vectorized math)
- **numba** (`@njit`) — **only** on loop-shaped hot kernels, behind existing signatures, gated by parity tests
- **scipy** (distribution fits where already used)
- Packaging: **hatchling**, env/deps via **uv**

### 3.2 API / service layer (optional `[app]` extra)
- **FastAPI** (async) — serializes library outputs to JSON; performs no math
- **Pydantic v2** — typed request/response schemas (TS types generated from these)
- **uvicorn** — ASGI server
- **httpx** — async data fetching (yfinance wrapped behind a provider interface)

### 3.3 Web UI (separate `app/` workspace)
- **Vite + React + TypeScript**
- **Tailwind CSS + shadcn/ui** — design system
- **TanStack Query** (data) + **TanStack Table** (sortable metrics grid)
- **lightweight-charts** (Apache-2.0, canvas) — all time-axis panels
  - **Confined behind a `<TimeSeriesChart>` adapter** so it can be swapped for **openalgo-charts** later with a one-file change
- **Bespoke SVG components** on `d3-scale` + `d3-array` — monthly heatmap, distribution, box/quantile/violin (low-cardinality, vector-crisp, PDF-perfect, fully themeable)

### 3.4 Quality tooling
- **ruff** (lint+format), **pyright** (types), **pytest** (+ **pytest-benchmark**, **hypothesis**)
- **GitHub Actions** matrix (3.10–3.13)

---

## 4. Architecture layers

```
+-------------------------------------------------------------+
|  openstatz  (PURE LIBRARY — pip install openstatz)          |
|                                                             |
|   stats.py   utils.py   reports.py   plots.py               |
|   _kernels.py  (Numba; gated, same signatures)              |
|   ReturnsContext  (compute returns/cumulative/dd once)      |
|        |  pandas in -> DataFrame/Series/dict out            |
+--------|----------------------------------------------------+
         |
         |  (optional) imported by:
         v
+-------------------------------------------------------------+
|  openstatz.app  (FastAPI adapter — pip install openstatz[app]) |
|   - calls library, serializes metrics + chart series to JSON  |
|   - Pydantic v2 schemas  ->  generated TypeScript types        |
|   - NO math here                                              |
+--------|----------------------------------------------------+
         |  JSON  { metrics[], series{time,value}[], tables[] }
         v
+-------------------------------------------------------------+
|  app/  (Vite + React + TS + Tailwind + shadcn)              |
|   TanStack Table (metrics)   TanStack Query (fetch)         |
|   <TimeSeriesChart> -> lightweight-charts (-> openalgo-charts)|
|   <BoxPlot> <MonthlyHeatmap> <Distribution> -> bespoke SVG  |
|   PDF export via headless Chromium (vector)                 |
+-------------------------------------------------------------+
```

---

## 5. Repository structure (monorepo)

```
openstatz/
├── pyproject.toml              # library + [app] optional extra
├── 2026-rebuild-architecture.md
├── openstatz/                  # THE LIBRARY (drop-in for quantstats)
│   ├── __init__.py             # exports + extend_pandas()
│   ├── stats.py
│   ├── utils.py
│   ├── reports.py
│   ├── plots.py                # matplotlib (kept for library/HTML parity)
│   ├── _plotting/
│   ├── _kernels.py             # NEW: Numba kernels, gated by parity tests
│   ├── _montecarlo.py
│   ├── _context.py             # NEW: ReturnsContext (compute-once)
│   ├── version.py
│   └── py.typed
│   └── app/                    # OPTIONAL: FastAPI adapter (extra = [app])
│       ├── server.py
│       ├── schemas.py          # Pydantic v2
│       └── serializers.py      # library output -> JSON
├── app/                        # OPTIONAL: web UI (separate workspace)
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── components/charts/  # <TimeSeriesChart>, <BoxPlot>, <MonthlyHeatmap>...
│       ├── components/table/   # metrics grid (TanStack Table)
│       ├── lib/format.ts       # single number-format layer
│       └── theme/tokens.css    # dark quant design tokens
└── tests/
    ├── test_stats.py ...       # ported from quantstats
    └── parity/                 # NEW: golden-master parity suite
        ├── generate_fixtures.py
        ├── fixtures/           # pickled current-quantstats outputs
        └── test_parity.py
```

---

## 6. Parity contract (the enforcement mechanism)

"100% parity" is a checklist with an automated gate. Three dimensions:

### 6.1 Function parity — every public symbol exists
- **`stats.py`** (~80): pct_rank, compsum, comp, expected_return, geometric_mean, ghpr,
  outliers, remove_outliers, best, worst, consecutive_wins/losses, exposure, win_rate,
  avg_return/win/loss, volatility, rolling_volatility, implied_volatility, sharpe,
  smart_sharpe, rolling_sharpe, sortino, smart_sortino, rolling_sortino, adjusted_sortino,
  probabilistic_(sharpe|sortino|adjusted_sortino)_ratio, treynor_ratio, omega,
  gain_to_pain_ratio, cagr, rar, skew, kurtosis, calmar, ulcer_index,
  ulcer_performance_index, upi, serenity_index, risk_of_ruin, ror, value_at_risk, var,
  conditional_value_at_risk, cvar, expected_shortfall, tail_ratio, payoff_ratio,
  win_loss_ratio, profit_ratio, profit_factor, cpc_index, common_sense_ratio,
  outlier_win/loss_ratio, recovery_factor, risk_return_ratio, max_drawdown,
  to_drawdown_series, kelly_criterion, r_squared, r2, information_ratio, greeks,
  rolling_greeks, compare, monthly_returns, drawdown_details, montecarlo,
  montecarlo_sharpe, montecarlo_drawdown, montecarlo_cagr.
- **`utils.py`** (public): to_returns, to_prices, log_returns, to_log_returns,
  exponential_stdev, rebase, aggregate_returns, group_returns, to_excess_returns,
  multi_shift, download_returns, make_index, make_portfolio, mtd/qtd/ytd helpers.
- **`reports.py`**: html, full, basic, metrics, plots.
- **`extend_pandas()`**: the full `_po.*` method map (stats + utils + plotting + metrics).

### 6.2 Report-output parity — every metric row, in order
`reports.metrics(mode="full")` produces this exact ordered set (the canonical output spec):

Start Period · End Period · Risk-Free Rate % · Time in Market % · Cumulative Return % /
Total Return % · CAGR % · Sharpe · Prob. Sharpe Ratio % · Smart Sharpe · Sortino ·
Smart Sortino · Sortino/√2 · Smart Sortino/√2 · Omega · Max Drawdown % · Max DD Date ·
Max DD Period Start/End · Longest DD Days · Volatility (ann.) % · R^2 · Information Ratio ·
Calmar · Skew · Kurtosis · Ulcer Performance Index · Risk-Adjusted Return % ·
Risk-Return Ratio · Avg. Return/Win/Loss % · Win/Loss Ratio · Profit Ratio ·
Expected Daily/Monthly/Yearly % · Kelly Criterion % · Risk of Ruin % · Daily Value-at-Risk % ·
Expected Shortfall (cVaR) % · Max Consecutive Wins/Losses · Gain/Pain Ratio · Gain/Pain (1M) ·
Payoff Ratio · Profit Factor · Common Sense Ratio · CPC Index · Tail Ratio ·
Outlier Win/Loss Ratio · MTD/3M/6M/YTD/1Y % · 3Y/5Y/10Y/All-time (ann.) % ·
Best/Worst Day/Month/Year % · Avg. Drawdown · Avg. Drawdown Days · Recovery Factor ·
Ulcer Index · Serenity Index · Avg. Up/Down Month % · Win Days/Month/Quarter/Year % ·
Beta · Alpha · Correlation · Treynor Ratio.

Plus the **EOY Returns (vs Benchmark)** table and the **Worst-5 / Worst-10 Drawdowns** table.

### 6.3 Plot parity — every chart reproduced
returns · log_returns · vol-matched returns · yearly_returns · histogram · daily_returns ·
rolling_beta · rolling_volatility · rolling_sharpe · rolling_sortino · drawdowns_periods ·
drawdown (underwater) · monthly_heatmap · distribution · snapshot · earnings · montecarlo ·
montecarlo_distribution.

Chart parity = **same underlying data + same transforms** (compounded / log / match_volatility /
rolling windows), NOT pixel-identical to matplotlib (the new charts are the upgrade). The
golden-master snapshots the data array each matplotlib plot consumes; the UI must render from
the identical array.

### 6.4 The gate (golden master)
1. `generate_fixtures.py` runs the **current quantstats** on a corpus:
   - single-strategy Series; multi-strategy DataFrame
   - with benchmark / without benchmark
   - compounded / simple
   - daily / monthly frequency
2. It pickles every metric row, every table, and every chart's source series into `fixtures/`.
3. `test_parity.py` runs **openstatz** on the same corpus and asserts:
   - metric numbers match to `rtol=1e-9, atol=1e-12`
   - tables match structurally (rows, order, labels)
   - chart series match exactly
4. CI runs this on every commit. A Numba kernel that diverges does not merge.

---

## 7. Performance plan

- **`ReturnsContext`**: clean returns, compounded cumulative, log returns, and drawdown series
  computed **once** per request; all metrics read from it (today each metric re-prepares).
- **Numba kernels** (`_kernels.py`, `@njit(cache=True, nogil=True)`), each gated by §6.4:
  - `montecarlo*` — `parallel=True` + `prange`, pre-generated seeded index matrix for
    deterministic, thread-count-independent results (the big win)
  - `drawdown_details`, `consecutive_wins/losses`, `_count_consecutive` — stateful scans
  - custom rolling kernels where pandas `.apply` is the bottleneck
- **Leave pure-NumPy reductions alone** (sharpe, vol, var, ratios) — already BLAS-fast; Numba
  adds only warmup cost.
- `nogil=True` lets FastAPI run kernels in a threadpool without blocking the event loop.
- Content-hash caching of the full metrics bundle keyed on the returns series.

---

## 8. UI / design ("great quant look")

- **Split by cardinality**: canvas (lightweight-charts) for high-cardinality time series;
  bespoke SVG for low-cardinality statistical panels.
- **Chart adapter boundary**: only `<TimeSeriesChart>` imports lightweight-charts. Normalized
  series contract `{ time: number; value: number }` from the API feeds both it and the future
  openalgo-charts engine.
- **Typography**: grotesk UI font (Inter/Geist) + **tabular/monospaced numerals** everywhere
  numbers appear; right-align numeric columns. (The signature of a pro financial UI.)
- **Color**: deep desaturated dark base (not pure black); green/red reserved strictly for P&L
  semantics; one accent; diverging perceptually-uniform scale centered at 0 for the heatmap.
- **Data-ink**: hairline borders, minimal gridlines, no chartjunk; card layout.
- **One formatting layer** (`lib/format.ts`): %, bps, decimals, thousands separators, negative
  styling — used by every cell and axis.
- **PDF export** via headless Chromium (vector SVG stays crisp) — replaces matplotlib raster.

---

## 9. Phased roadmap

### Phase 0 — Foundation & parity harness (highest leverage)
- [ ] Scaffold repo (pyproject with `[app]` extra, uv, ruff, pyright, CI matrix)
- [ ] Port quantstats library code into `openstatz/` (rename, keep behavior identical)
- [ ] Build `tests/parity/` golden-master generator + `test_parity.py`; capture baseline
- [ ] Green parity run proves drop-in equivalence BEFORE any change

### Phase 1 — Performance (behind parity gate)
- [ ] Introduce `ReturnsContext`
- [ ] Add `_kernels.py` Numba kernels (montecarlo first), each must pass §6.4
- [ ] `pytest-benchmark` baseline vs current; record speedups

### Phase 2 — API adapter
- [ ] Pydantic v2 schemas + serializers (metrics, tables, chart series)
- [ ] FastAPI `serve` command; `openstatz serve`
- [ ] Generate TypeScript types from schemas

### Phase 3 — Web UI
- [ ] Vite + React + TS + Tailwind + shadcn skeleton
- [ ] `<TimeSeriesChart>` (lightweight-charts) + EquityPanel/Drawdown/Rolling panels
- [ ] Bespoke SVG: MonthlyHeatmap, Distribution, BoxPlot
- [ ] TanStack metrics table (parity-ordered rows)
- [ ] Design tokens + format layer + PDF export

### Phase 4 — Polish & release
- [ ] Docs (mkdocs-material), examples
- [ ] openalgo-charts swap behind `<TimeSeriesChart>` (when ready)
- [ ] v1.0.0

---

## 10. Compatibility / migration notes

- **Public API identical** to quantstats so existing user code works by changing only the import
  (`import openstatz as os`). Note: quantstats tutorials use the `qs` alias; either alias works,
  but the documented OpenStatz convention is `os` (see the alias caveat in §1). Optionally ship a
  thin `quantstats` shim that re-exports openstatz.
- pandas at the edges keeps `extend_pandas()` and all DataFrame/Series semantics intact.
- HTML `reports.html()` retained (matplotlib path) so the *library* output matches byte-for-byte;
  the interactive UI is an additional surface, not a replacement.

---

## 11. Open decisions

- [x] Package name on PyPI: `openstatz` — **confirmed available**. Documented import alias: `os`.
- [x] `quantstats`-compat shim: shipped as **opt-in** `openstatz.compat.install_quantstats_shim()`
      (does not silently shadow a real quantstats install).
- [x] Monorepo for `app/` (web UI lives in this repo alongside the library).
- [x] Provider abstraction for data: `openstatz.providers` with `yfinance` (default) and an
      optional `OpenAlgo` provider; `ReturnsProvider` protocol for custom backends.
- [x] Numba: **deferred for now** (compatibility friction with current NumPy). Kernels are pure
      vectorized NumPy and still parity-gated; reintroduce later behind the same gate.
