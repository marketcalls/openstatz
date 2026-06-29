# OpenStatz Web UI

A modern, dark "pro quant" tearsheet for the OpenStatz API. Vite + React + TypeScript +
Tailwind v4, with TanStack Query/Table, `lightweight-charts` (behind a one-file adapter), and
bespoke SVG statistical panels.

## Architecture boundaries

- **No analytics math.** Every number comes from the OpenStatz Python core over JSON
  (`/api/analyze`). The UI only renders.
- **`<TimeSeriesChart>` is the only module importing `lightweight-charts`.** Everything else
  speaks the normalized `{ time, value }` contract, so swapping in `openalgo-charts` later is a
  single-file change.
- **Split by cardinality:** canvas (`lightweight-charts`) for high-cardinality time series;
  bespoke SVG (`MonthlyHeatmap`, `Distribution`, `BoxPlot`) for low-cardinality statistical
  panels — vector-crisp and PDF-perfect.
- **One formatting layer** (`src/lib/format.ts`) and **one token file**
  (`src/theme/tokens.css`) — green/red reserved strictly for P&L; tabular numerals everywhere.

## Run

```bash
# 1. Start the backend (from the repo root):
pip install -e ".[app]"
openstatz serve                 # -> http://127.0.0.1:8000

# 2. Start the UI (from app/):
npm install
npm run dev                     # -> http://localhost:5173 (proxies /api to :8000)
```

`npm run build` typechecks (`tsc -b`) and produces `dist/`. PDF export uses the browser's
vector print path (the "Export PDF" button → `window.print()`); for automated export, render
`dist/` with headless Chromium.

## Types

`src/api/types.ts` mirrors the Pydantic schemas. To regenerate from the live contract:

```bash
python ../scripts/export_openapi.py     # writes src/api/openapi.json
npm run gen:types                       # openapi-typescript -> src/api/openapi-types.ts
```
