# Changelog

All notable changes to OpenStatz are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

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
