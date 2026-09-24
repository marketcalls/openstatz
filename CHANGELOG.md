# Changelog

All notable changes to OpenStatz are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [0.5.0]

This release makes the modern tearsheet (`openstatz.dashboard(...)` and `openstatz serve`) report
the numbers the library computes. Several cards, tables and charts were showing rounded, mislabelled
or stale values. Upgrade if you share these reports; nothing in the classic `reports.html(...)`
output changes except three row labels.

### Breaking
- **Three metric labels are now plain ASCII.** `CAGR﹪` is `CAGR%`, `Sortino/√2` is
  `Sortino/sqrt(2)`, and `Smart Sortino/√2` is `Smart Sortino/sqrt(2)`. Code that looks rows up
  by the old QuantStats spelling (`metrics.loc["CAGR﹪"]`) must use the new one. The old labels
  could not be typed, and `print(metrics)` or `reports.metrics(..., display=True)` raised
  `UnicodeEncodeError` on a Windows console using cp1252. These are the only differences from
  QuantStats output; the parity gate checks every number under them. See `docs/parity.md`.

### Added
- `reports.metrics(..., display=False, raw=True)` returns every metric at full precision. The
  default output still rounds to 2 decimals exactly as QuantStats does, which turns a 13.52% CAGR
  into 0.14 because percentages are fractions there. With `raw=True`, Beta, Alpha, Correlation and
  Treynor Ratio are numbers rather than strings, and `df.attrs["percent_rows"]` and
  `df.attrs["integer_rows"]` say which rows are percentages and counts.
- `OpenAlgoProvider` takes `source="api"` (history from your broker, the default) or `source="db"`
  (history from OpenAlgo's Historify database), on the constructor or per `returns()` call. The
  default path sends nothing new, so older OpenAlgo SDKs keep working.
- The Worst Drawdowns rows in the API carry `ongoing: true` for a drawdown still underwater at
  the last date.

### Fixed
- **Tearsheet values were rounded before display.** CAGR 13.52% showed as 14.00%, max drawdown
  -31.65% as -32.00%, and volatility, time in market, MTD, YTD, 3M, 6M and 1Y the same way, while
  the Return and Risk by Horizon table showed the true value. The full metrics table showed raw
  fractions ("0.14"). Every card and table cell now shows the full-precision value, with
  percentages formatted as percentages.
- **Correlation and Treynor Ratio were shown as percentages** ("0.32%" for a correlation of 0.32).
  They are plain numbers now.
- **Charts could show another series' data.** The prepared-returns cache keyed on values alone,
  so analysing the same returns under a new name (`dashboard(s.rename("B"))` after using
  `s.rename("A")`, or after calling `stats.*` on a DataFrame column) keyed the cumulative and
  rolling charts under the old name: the equity chart showed only the benchmark and the rolling
  Sharpe, volatility and win-rate charts were blank. The key now includes the series name or
  DataFrame columns. It also includes whether excess returns were taken, so with `rf > 0` a
  result no longer depends on which function ran first (`stats.rar(r, rf=0.05)` returned a
  different value after `stats.cagr(r, rf=0.05)`).
- **Worst Drawdowns listed an ongoing drawdown as recovered** on the last date of the data. The
  Recovered column now reads "Not yet".
- **Worst Drawdowns was not sorted by the depth it showed.** It sorted by the full drawdown but
  displayed QuantStats' "99% max drawdown", so rows appeared out of order and the deepest row
  disagreed with the Max Drawdown metric. It now shows the full depth it sorts by.
- **The monthly heatmap filled months with no data as 0.0**, both after the last date and before
  the first. Those cells are blank now, and they no longer skew the monthly box plot.
- **Stray tick labels at the end of chart axes.** A multi-year axis could end in a bare day of the
  month ("9") or month ("Jul"). Axes now label only the tick marks that suit the time span shown.
- **The header and the metrics disagreed on the start date.** With a benchmark, the metrics skip
  the leading zero returns (Start Period 2016-10-04) while the header, charts and tables used the
  first row (2016-09-27, with more observations). Everything now uses the metrics' window.
- `reports.html(...)` and `reports.full(...)` raised `TypeError` for a one-column DataFrame. It
  had only worked when the stale cache entry above happened to hand them a Series.

### Docs
- Examples use `import openstatz as ostz`. The old `import openstatz as os` hid Python's own `os`
  module, so the examples broke in any script that also needed it.

## [0.4.1]

### Fixed
- **PyPI project metadata pointed at the upstream QuantStats repo** (#1). The Homepage /
  Documentation / Repository links and the author/maintainer email all referenced
  `ranaroussi/quantstats` and its maintainer. Project URLs now point to
  [openalgo.in](https://openalgo.in) and `marketcalls/openstatz` (plus Issues and Changelog), and
  the authors/maintainers are OpenAlgo and marketcalls. The QuantStats attribution remains in
  `NOTICE`, `LICENSE.txt`, the README, and the source headers, as Apache-2.0 requires.

## [0.4.0]

### Added
- **Tearsheet analytics**: Rolling Win Rate chart (trailing % of positive periods), a
  **Return & Risk by Horizon** table (CAGR / Max Drawdown / Calmar over trailing 1Y, 3Y, 5Y and
  all-time windows, with N/A for horizons longer than the available history), and a
  **Consecutive Losing Streaks** distribution in the Risk section. New library helpers
  `stats.rolling_win_rate`, `stats.consecutive_loss_lengths`, and `stats.horizon_summary`.

### Fixed
- **Web server security**: the `openstatz serve` SPA route no longer follows URL-encoded `..`
  segments, closing a path-traversal that could read files outside the static root; CORS is now
  restricted to same-machine origins by default (override with `OPENSTATZ_CORS_ORIGINS`).
- **Robustness**: `/api/analyze` and `/api/compare` return a clean 422 (instead of a 500) for empty
  input and unparseable dates.
- `openstatz --version` now prints the version (the flag was never registered).
- `safe_random_seed()` now actually seeds the RNG (it previously discarded the generator).

## [0.3.1]

### Changed
- Compare: the head-to-head table uses "Serenity Index" instead of "Recovery Factor", which is
  blank for multi-strategy input.
- Pin `pandas<3` for now: the vendored QuantStats compute core is not yet pandas-3.0 ready.

### Added
- Tag-triggered PyPI release workflow using Trusted Publishing (no stored token); see RELEASING.md.

## [0.3.0]

### Added
- **Compare view**: a new tab in the web app (and `POST /api/compare/symbols` +
  `POST /api/compare`) to compare several strategies side by side. Shows a leaderboard (who wins
  the most key metrics), an overlaid cumulative chart, and a head-to-head table with the best value
  per metric in green and worst in red. Example: AAPL vs NVDA.
- README examples for US and Indian markets and for a custom backtest strategy; the hero image now
  shows the modern dashboard.

### Fixed
- Blank metric cards / garbled metrics table when a strategy and its benchmark shared a name.
  `download_returns` now names the series after the ticker (not "Close"), plus a name-collision
  guard and a duplicate-column safety net in the serializer.

### Changed
- Removed the "Generated by QuantStats" branding from the classic report and the app; the
  QuantStats credit now lives only in the README (plus the required LICENSE / NOTICE / source
  headers). The tearsheets link to openalgo.in.

## [0.2.0]

### Added
- **Modern tearsheet on the base install** (`openstatz.dashboard(...)`): renders the same React
  dashboard served by `openstatz serve` into a single self-contained offline HTML file, with the
  analysis bundle embedded and the JS/CSS inlined. No server, no `[app]` extra, and no network. It
  works on a plain `pip install openstatz`.
- The web UI now bootstraps from an embedded `window.__OPENSTATZ_DATA__` payload when present,
  falling back to the live `/api` (server) path otherwise.

### Docs
- README documents both tearsheets: the modern `dashboard(...)` file and the classic
  `reports.html(...)` QuantStats-style report.

## [0.1.0]

The initial OpenStatz rebuild of QuantStats. **Numerically bit-identical** to the
upstream library (enforced by the golden-master parity suite).

### Added
- **Library core** (`openstatz/`): the full QuantStats API ported verbatim (`stats`,
  `utils`, `reports`, `plots`, `_montecarlo`, `extend_pandas()`), with identical numbers.
- **Parity gate** (`tests/parity/`): deterministic corpus × ~70 probes per case, asserting
  openstatz reproduces reference QuantStats to `rtol=1e-9` (metrics, tables, chart series,
  and matching exception classes). Fixtures are committed; CI runs the gate on every commit.
- **Vectorized kernels** (`openstatz/_kernels.py`): pure-NumPy Monte Carlo cumulative + a
  vectorized per-column max-drawdown (~11x faster, bit-identical). *(Numba is intentionally
  deferred, it creates NumPy-compatibility friction.)*
- **`ReturnsContext`** (`openstatz/_context.py`): compute the shared derived series once, with
  a content hash for caching.
- **FastAPI adapter** (`openstatz/app/`, `pip install openstatz[app]`): `serializers` (no math),
  Pydantic v2 `schemas`, a `server` (`/api/health`, `/api/analyze`), and the `openstatz serve`
  CLI. OpenAPI exported for TypeScript generation.
- **Web UI** (`app/`): Vite + React + TS + Tailwind tearsheet, with a `TimeSeriesChart` adapter over
  `lightweight-charts`, bespoke SVG heatmap/distribution/box plots, a TanStack metrics table,
  one formatting layer, dark "pro quant" tokens, and vector PDF export.
- **Data providers** (`openstatz/providers.py`): pluggable `ReturnsProvider` with `yfinance`
  (default) and an optional `OpenAlgo` provider.
- **quantstats-compat shim** (`openstatz/compat.py`): opt-in `install_quantstats_shim()` so
  `import quantstats as qs` runs on OpenStatz unmodified.

### Notes
- Public API is identical to QuantStats; existing code works by changing only the import
  (`import openstatz as os`, or the `qs` alias).
