# OpenStatz

[![PyPI version](https://img.shields.io/pypi/v/openstatz.svg)](https://pypi.org/project/openstatz/)
[![Python versions](https://img.shields.io/pypi/pyversions/openstatz.svg)](https://pypi.org/project/openstatz/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE.txt)
[![Website](https://img.shields.io/badge/web-openalgo.in-0aa)](https://openalgo.in)

OpenStatz is a modern rebuild of [QuantStats](https://github.com/ranaroussi/quantstats). It gives
you the same portfolio analytics and the same numbers, plus a modern, interactive web tearsheet you
can open in a browser — all in a single offline HTML file, no server required.

Maintained by [OpenAlgo](https://openalgo.in) and marketcalls.

![OpenStatz tearsheet](https://raw.githubusercontent.com/marketcalls/openstatz/main/docs/images/snapshot.png)

## What you can do

- Use it in Python as a drop-in for QuantStats.
- Generate the modern web tearsheet as a single offline HTML file. It works on a plain
  `pip install openstatz`, with no server and no Node.js.
- Or run the same dashboard as a live server (`openstatz serve`) to type tickers and upload CSVs.
- Send your backtest returns (a CSV file or a pandas Series) and get a full report.
- Compare several strategies side by side and see which one is better on each metric.

## Inside the tearsheet

The dashboard is organized into scannable sections — equity and rolling stats, risk, seasonality,
and return distribution — with light and dark themes and one-click PDF export.

**Performance** — equity curve, rolling Sharpe / volatility / win-rate, and a *Return & Risk by
Horizon* table (CAGR, max drawdown and Calmar over trailing 1Y / 3Y / 5Y / all-time windows):

![Performance section](https://raw.githubusercontent.com/marketcalls/openstatz/main/docs/images/performance.png)

**Risk** — underwater drawdown curve, tail and exposure metrics, the worst drawdown episodes, and
the distribution of consecutive losing streaks:

![Risk section](https://raw.githubusercontent.com/marketcalls/openstatz/main/docs/images/risk.png)

**Seasonality** — monthly and weekly return heatmaps and end-of-year returns vs the benchmark:

![Monthly heatmap](https://raw.githubusercontent.com/marketcalls/openstatz/main/docs/images/monthly_heatmap.png)

**Distribution** — return histogram with a mean marker, and a daily-vs-monthly spread box plot:

![Return distribution](https://raw.githubusercontent.com/marketcalls/openstatz/main/docs/images/distribution.png)

## Install

```bash
pip install openstatz          # the library
pip install "openstatz[app]"   # also installs the web app and API
```

## Use it in Python

It works like QuantStats. You only change the import.

```python
import openstatz as ostz

returns = my_backtest.returns                 # a pandas Series of daily returns
benchmark = ostz.utils.download_returns("SPY")

ostz.reports.html(returns, benchmark=benchmark, output="tearsheet.html")
ostz.reports.metrics(returns, mode="full", display=True)

ostz.extend_pandas()
returns.sharpe()
```

The examples import it as `ostz`; the `qs` alias also works. Avoid `import openstatz as os`: it
hides Python's own `os` module, so `os.path` and `os.environ` stop working in that file.

`reports.metrics(..., display=False)` returns the same table QuantStats does, with every number
rounded to 2 decimals. Percentages are fractions there, so a 13.52% CAGR comes back as 0.14. Pass
`raw=True` to get every number at full precision instead:

```python
m = ostz.reports.metrics(returns, benchmark=benchmark, mode="full", display=False, raw=True)
m.loc["CAGR%"]                 # 0.1352, not 0.14
m.attrs["percent_rows"]        # which rows are percentages
```

## Two ways to make a tearsheet

Both work on a plain `pip install openstatz`, with no `[app]` extra, no server, and no Node.js.

**Modern tearsheet.** The same dashboard as `openstatz serve`, written to a single self-contained
HTML file with the analysis baked in (charts, heatmaps, metrics, light and dark themes, PDF export):

```python
import openstatz as ostz

ostz.dashboard(returns, benchmark=benchmark, output="report.html")
```

The file embeds the data and inlines the JS/CSS, so you can email it or commit it and it just opens.

**Classic tearsheet.** The original QuantStats-style report (matplotlib charts in a static HTML
template). Use this when you want the familiar QuantStats look or exact upstream parity:

```python
import openstatz as ostz

ostz.reports.html(returns, benchmark=benchmark, output="tearsheet.html")
ostz.reports.metrics(returns, mode="full", display=True)
```

## Examples for traders

**US market (a stock vs the market).**

```python
import openstatz as ostz

aapl = ostz.utils.download_returns("AAPL")     # or NVDA, MSFT, TSLA, ...
spy  = ostz.utils.download_returns("SPY")

ostz.dashboard(aapl, benchmark=spy, output="aapl.html")      # modern tearsheet
ostz.reports.html(aapl, benchmark=spy, output="aapl_classic.html")   # classic tearsheet
```

**Indian market (a stock vs the Nifty 50).**

```python
import openstatz as ostz

reliance = ostz.utils.download_returns("RELIANCE.NS")   # NSE tickers end in .NS
nifty    = ostz.utils.download_returns("^NSEI")          # Nifty 50 index

ostz.dashboard(reliance, benchmark=nifty, output="reliance.html")
```

**Your own backtest strategy.** Feed a pandas Series of daily returns straight from your backtest.

```python
import openstatz as ostz

returns = my_backtest.returns          # pd.Series of daily returns
bench   = ostz.utils.download_returns("SPY")

ostz.dashboard(returns, benchmark=bench, output="strategy.html")
ostz.reports.metrics(returns, benchmark=bench, mode="full", display=True)
```

CSV works too: a `date, return` file (with an optional third benchmark column). Load it with
pandas and pass the Series, or drop it into the web app (see below).

## Compare strategies

See which of several strategies is better, at a glance. Start the server and open the **Compare**
tab, or call the API. Best value per metric is green, worst is red, and the leader wins the most
key metrics.

![OpenStatz compare view](https://raw.githubusercontent.com/marketcalls/openstatz/main/docs/images/compare.png)

```bash
openstatz serve      # then click "Compare" and enter, e.g., AAPL, NVDA
```

```bash
# Or the API, for tickers or your own strategies:
curl -X POST http://127.0.0.1:8000/api/compare/symbols \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL", "NVDA", "MSFT"], "period": "5y"}'
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
- `POST /api/compare/symbols` and `POST /api/compare` to compare several strategies

## The same numbers as QuantStats

OpenStatz reuses the QuantStats math without changes, so the results are the same. A test suite
checks this on every change. It runs the real QuantStats and OpenStatz side by side and fails if any
number, table, or chart differs (to within 1e-9). It has been verified to match exactly, even on
live market data. The one deliberate difference is three metric labels written in plain ASCII
(`CAGR%`, `Sortino/sqrt(2)`, `Smart Sortino/sqrt(2)`); see [docs/parity.md](docs/parity.md).

```bash
python tests/parity/generate_fixtures.py   # build the reference output from QuantStats
pytest tests/parity -q                       # run the check
```

## Data sources

`openstatz.providers` fetches returns for a symbol. yfinance is the default. OpenAlgo is an optional
source for users on that platform. It reads from your broker by default, or from the Historify
database with `source="db"`. See [docs/providers.md](docs/providers.md).

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
