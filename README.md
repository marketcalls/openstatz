# OpenStatz

OpenStatz is a modern rebuild of [QuantStats](https://github.com/ranaroussi/quantstats). It gives
you the same portfolio analytics and the same numbers, plus an optional web tearsheet you can open
in a browser.

![OpenStatz tearsheet](https://raw.githubusercontent.com/marketcalls/openstatz/main/docs/images/snapshot.png)

## What you can do

- Use it in Python as a drop-in for QuantStats.
- Generate the modern web tearsheet as a single offline HTML file. It works on a plain
  `pip install openstatz`, with no server and no Node.js.
- Or run the same dashboard as a live server (`openstatz serve`) to type tickers and upload CSVs.
- Send your backtest returns (a CSV file or a pandas Series) and get a full report.

## Install

```bash
pip install openstatz          # the library
pip install "openstatz[app]"   # also installs the web app and API
```

## Use it in Python

It works like QuantStats. You only change the import.

```python
import openstatz as os

returns = my_backtest.returns                 # a pandas Series of daily returns
benchmark = os.utils.download_returns("SPY")

os.reports.html(returns, benchmark=benchmark, output="tearsheet.html")
os.reports.metrics(returns, mode="full", display=True)

os.extend_pandas()
returns.sharpe()
```

The `qs` alias also works. Note that the `os` alias hides Python's built-in `os` inside files that
use it, so write `import os as _os` if you need both.

## Two ways to make a tearsheet

Both work on a plain `pip install openstatz`, with no `[app]` extra, no server, and no Node.js.

**Modern tearsheet.** The same dashboard as `openstatz serve`, written to a single self-contained
HTML file with the analysis baked in (charts, heatmaps, metrics, light and dark themes, PDF export):

```python
import openstatz as os

os.dashboard(returns, benchmark=benchmark, output="report.html")
```

The file embeds the data and inlines the JS/CSS, so you can email it or commit it and it just opens.

**Classic tearsheet.** The original QuantStats-style report (matplotlib charts in a static HTML
template). Use this when you want the familiar QuantStats look or exact upstream parity:

```python
import openstatz as os

os.reports.html(returns, benchmark=benchmark, output="tearsheet.html")
os.reports.metrics(returns, mode="full", display=True)
```

## Open the web tearsheet (live server)

```bash
pip install "openstatz[app]"
openstatz serve        # opens the API and UI at http://127.0.0.1:8000
```

To run on a different port:

```bash
openstatz serve --port 8200            # http://127.0.0.1:8200

# or without installing the command:
python -m openstatz serve --port 8200
```

In the browser you can:

- Type a ticker and a benchmark, for example RELIANCE.NS and ^NSEI.
- Or upload a CSV of your own returns. Columns: date, return, and an optional benchmark.
  See [docs/example_returns.csv](docs/example_returns.csv) for the format.

The page shows the cumulative return, drawdown, monthly and weekly heatmaps, yearly returns, the
return distribution, and a full table of metrics. It has light and dark themes and a PDF export.

## Send a backtest with the API

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"dates": ["2024-01-02", "..."], "returns": {"Strategy": [0.001, "..."]}}'
```

Endpoints:

- `GET /api/health`
- `POST /api/analyze` for your own returns
- `POST /api/analyze/symbol` for a ticker the server fetches for you

## The same numbers as QuantStats

OpenStatz reuses the QuantStats math without changes, so the results are the same. A test suite
checks this on every change. It runs the real QuantStats and OpenStatz side by side and fails if any
number, table, or chart differs (to within 1e-9). It has been verified to match exactly, even on
live market data.

```bash
python tests/parity/generate_fixtures.py   # build the reference output from QuantStats
pytest tests/parity -q                       # run the check
```

## Data sources

`openstatz.providers` fetches returns for a symbol. yfinance is the default. OpenAlgo is an optional
source for users on that platform.

## Run old QuantStats code unchanged

```python
import openstatz.compat
openstatz.compat.install_quantstats_shim()

import quantstats as qs        # this is now OpenStatz
```

## Project layout

```
openstatz/         the library (drop-in for quantstats)
  app/             optional FastAPI server and JSON serializers
  app/static/      the built web UI, shipped inside the package
app/               web UI source (React, Vite, Tailwind)
tests/parity/      the check against QuantStats
```

## Build the web UI (for contributors)

The shipped app is pre-built, so users need no Node.js. To rebuild it from source:

```bash
cd app && npm ci && npm run build
cp -r dist/* ../openstatz/app/static/
```

## License

Apache 2.0. See [LICENSE.txt](./LICENSE.txt) and [NOTICE](./NOTICE).

OpenStatz is built on QuantStats (Copyright 2019 to 2025, Ran Aroussi, Apache 2.0). The portfolio
math is reused without changes. Thanks to Ran Aroussi and the QuantStats contributors.
