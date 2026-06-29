# Changelog

All notable changes to OpenStatz are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] — unreleased

The initial OpenStatz rebuild of QuantStats. **Numerically bit-identical** to the
upstream library (enforced by the golden-master parity suite).

### Added
- **Library core** (`openstatz/`): the full QuantStats API ported verbatim — `stats`,
  `utils`, `reports`, `plots`, `_montecarlo`, `extend_pandas()` — with identical numbers.
- **Parity gate** (`tests/parity/`): deterministic corpus × ~70 probes per case, asserting
  openstatz reproduces reference QuantStats to `rtol=1e-9` (metrics, tables, chart series,
  and matching exception classes). Fixtures are committed; CI runs the gate on every commit.
- **Vectorized kernels** (`openstatz/_kernels.py`): pure-NumPy Monte Carlo cumulative + a
  vectorized per-column max-drawdown (~11× faster, bit-identical). *(Numba is intentionally
  deferred — it creates NumPy-compatibility friction.)*
- **`ReturnsContext`** (`openstatz/_context.py`): compute the shared derived series once, with
  a content hash for caching.
- **FastAPI adapter** (`openstatz/app/`, `pip install openstatz[app]`): `serializers` (no math),
  Pydantic v2 `schemas`, a `server` (`/api/health`, `/api/analyze`), and the `openstatz serve`
  CLI. OpenAPI exported for TypeScript generation.
- **Web UI** (`app/`): Vite + React + TS + Tailwind tearsheet — `TimeSeriesChart` adapter over
  `lightweight-charts`, bespoke SVG heatmap/distribution/box plots, a TanStack metrics table,
  one formatting layer, dark "pro quant" tokens, and vector PDF export.
- **Data providers** (`openstatz/providers.py`): pluggable `ReturnsProvider` — `yfinance`
  (default) and an optional `OpenAlgo` provider.
- **quantstats-compat shim** (`openstatz/compat.py`): opt-in `install_quantstats_shim()` so
  `import quantstats as qs` runs on OpenStatz unmodified.

### Notes
- Public API is identical to QuantStats; existing code works by changing only the import
  (`import openstatz as os`, or the `qs` alias).
