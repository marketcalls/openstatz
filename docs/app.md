# Web app & API

The web UI is an **optional layer** on top of the same library core. The core never imports
FastAPI or any UI dependency.

## API (`pip install openstatz[app]`)

```bash
openstatz serve            # -> http://127.0.0.1:8000
```

- `GET  /api/health` → `{ status, version, numba }`
- `POST /api/analyze` → the full analysis bundle: `meta`, `metrics` (ordered, parity-faithful),
  `series` (per-chart `{ time, value }` arrays), and `tables` (monthly heatmap, EOY, worst
  drawdowns).

The adapter performs **no math** — it parses the request to pandas, calls the library, and
serializes. Request/response shapes are Pydantic v2 models (`openstatz/app/schemas.py`); export
the OpenAPI schema with `python scripts/export_openapi.py`.

## UI (`app/`)

Vite + React + TypeScript + Tailwind. `lightweight-charts` lives behind a single
`<TimeSeriesChart>` adapter (the swap boundary for [openalgo-charts] later); the statistical
panels (monthly heatmap, distribution, box plot) are bespoke SVG for vector-crisp PDF export.

```bash
cd app
npm install
npm run dev                # http://localhost:5173 (proxies /api to :8000)
```

[openalgo-charts]: https://github.com/marketcalls
