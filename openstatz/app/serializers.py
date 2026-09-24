#!/usr/bin/env python
#
# OpenStatz API serializers — turn library output into JSON-friendly dicts.
#
# THERE IS NO MATH HERE. Every number comes from the library core (stats,
# reports, ReturnsContext). This module only reshapes pandas objects into the
# normalized wire contract the web UI consumes:
#
#   - metrics : ordered rows mirroring reports.metrics(mode="full")
#   - series  : list[{time:int(epoch s), value:float}]  (the TimeSeriesChart contract)
#   - tables  : EOY returns, worst drawdowns, monthly heatmap matrix
#
# Pure stdlib + numpy/pandas: importable without the [app] extra, so it is unit
# testable without FastAPI/pydantic.
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

PandasData = pd.Series | pd.DataFrame


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def _epoch_seconds(ts) -> int:
    """Naive/aware Timestamp -> integer POSIX seconds (UTC wall clock)."""
    return int(pd.Timestamp(ts).value // 1_000_000_000)


def _f(x) -> float | None:
    """Coerce to a JSON-safe float (NaN/inf -> None)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def series_to_points(s: pd.Series, *, dropna: bool = True) -> list[dict[str, Any]]:
    """Series with a DatetimeIndex -> [{time, value}] (the chart contract)."""
    out: list[dict[str, Any]] = []
    for ts, val in s.items():
        v = _f(val)
        if v is None and dropna:
            continue
        out.append({"time": _epoch_seconds(ts), "value": v})
    return out


def _columns_of(data: PandasData) -> list[str]:
    if isinstance(data, pd.DataFrame):
        return [str(c) for c in data.columns]
    return [str(data.name) if data.name is not None else "Strategy"]


def _each_column(data: PandasData):
    """Yield (name, Series) for Series or each DataFrame column."""
    if isinstance(data, pd.DataFrame):
        for c in data.columns:
            yield str(c), data[c]
    else:
        yield (str(data.name) if data.name is not None else "Strategy"), data


# ---------------------------------------------------------------------------
# Metrics table (mirrors reports.metrics(mode="full"))
# ---------------------------------------------------------------------------

def serialize_metrics(
    returns: PandasData,
    benchmark: pd.Series | None = None,
    *,
    rf: float = 0.0,
    compounded: bool = True,
    periods_per_year: int = 252,
) -> dict[str, Any]:
    """Return the canonical, ordered metrics table as JSON.

    {
      "columns": ["Benchmark", "Strategy", ...],
      "rows": [ {"label": "Sharpe", "values": {"Strategy": 0.74, ...},
                 "display": {"Strategy": "0.74", ...}}, ... ]
    }

    ``values`` holds each cell at full precision (percentages as fractions,
    0.1352 for 13.52%), or None for a non-numeric cell such as a date.
    ``display`` is the same cell as a person reads it: "13.52%", "0.74",
    "2,135", or the text itself.

    The values come from ``reports.metrics(raw=True)``, never from its default
    output, which rounds every cell to 2 decimals the way QuantStats does. On a
    fraction that turns a 13.52% CAGR into 0.14, so nothing here may read it.
    """
    from openstatz import reports

    df = reports.metrics(
        returns,
        benchmark=benchmark,
        rf=rf,
        compounded=compounded,
        periods_per_year=periods_per_year,
        display=False,
        mode="full",
        sep=False,
        raw=True,
    )
    percent_rows = set(df.attrs.get("percent_rows", ()))
    integer_rows = set(df.attrs.get("integer_rows", ()))

    # reports.metrics labels a single series' column "Strategy" (and the
    # benchmark "Benchmark"). Relabel to the actual series names so the metrics
    # columns line up with meta.columns and the chart-series keys the UI uses.
    rename = {}
    if isinstance(returns, pd.Series) and returns.name is not None and "Strategy" in df.columns:
        rename["Strategy"] = str(returns.name)
    if benchmark is not None and benchmark.name is not None and "Benchmark" in df.columns:
        rename["Benchmark"] = str(benchmark.name)
    if rename:
        df = df.rename(columns=rename)

    # Safety net: never let duplicate column names slip through — indexing a
    # duplicated label returns a Series, which would stringify into the cells.
    if df.columns.duplicated().any():
        seen: dict[str, int] = {}
        new_cols = []
        for c in df.columns:
            c = str(c)
            if c in seen:
                seen[c] += 1
                new_cols.append(f"{c} ({seen[c]})")
            else:
                seen[c] = 0
                new_cols.append(c)
        df = df.copy()
        df.columns = new_cols

    columns = [str(c) for c in df.columns]
    rows = []
    for label, row in df.iterrows():
        kind = "pct" if label in percent_rows else "int" if label in integer_rows else "num"
        values = {str(c): _parse_number(row[c]) for c in df.columns}
        display = {str(c): _display_cell(row[c], values[str(c)], kind) for c in df.columns}
        rows.append({"label": str(label), "values": values, "display": display})
    return {"columns": columns, "rows": rows}


def _display_cell(raw, value: float | None, kind: str) -> str:
    """Human-readable text for one metrics cell."""
    if value is None:
        return _stringify(raw)
    if kind == "pct":
        return f"{value * 100:,.2f}%"
    if kind == "int":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _stringify(v) -> str:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return ""
    return str(v)


def _parse_number(v) -> float | None:
    """Best-effort parse of a (possibly formatted) metric cell to float."""
    if isinstance(v, str):
        # Dates, "-" and other text cells. reports.metrics(raw=True) returns
        # every number as a number, so a string here is never a value.
        return None
    return _f(v)


# ---------------------------------------------------------------------------
# Chart series bundle
# ---------------------------------------------------------------------------

def serialize_series(
    returns: PandasData,
    benchmark: pd.Series | None = None,
    *,
    rf: float = 0.0,
    compounded: bool = True,
    periods_per_year: int = 252,
    rolling_window: int = 126,
) -> dict[str, Any]:
    """Every time-axis chart's underlying series, keyed by chart name.

    Each value is a dict of {column_name: [{time, value}]}. The UI renders the
    identical arrays the matplotlib plots consume (chart parity = same data).
    """
    from openstatz import stats
    from openstatz._context import ReturnsContext

    ctx = ReturnsContext.from_returns(
        returns, rf=rf, periods_per_year=periods_per_year, compounded=compounded
    )

    out: dict[str, Any] = {}

    # Cumulative (equity) + drawdown (underwater), per column.
    out["cumulative"] = _per_col_points(ctx.cumulative)
    out["drawdown"] = _per_col_points(ctx.drawdown)
    out["daily_returns"] = _per_col_points(ctx.returns)
    out["log_returns"] = _per_col_points(_safe(lambda: np.log1p(ctx.cumulative)))

    # Rolling risk series.
    out["rolling_volatility"] = _per_col_points(
        _safe(lambda: stats.rolling_volatility(ctx.returns, rolling_period=rolling_window))
    )
    out["rolling_sharpe"] = _per_col_points(
        _safe(lambda: stats.rolling_sharpe(ctx.returns, rolling_period=rolling_window))
    )
    out["rolling_sortino"] = _per_col_points(
        _safe(lambda: stats.rolling_sortino(ctx.returns, rolling_period=rolling_window))
    )
    # Rolling hit rate (% of positive periods among non-zero periods in the
    # window). Period-based, not trade-level — see stats.rolling_win_rate.
    out["rolling_win_rate"] = _per_col_points(
        _safe(lambda: stats.rolling_win_rate(ctx.returns, rolling_period=rolling_window))
    )

    # Benchmark-relative rolling beta + the benchmark's own equity/drawdown so
    # the UI can overlay it on the cumulative-return chart.
    if benchmark is not None:
        out["rolling_beta"] = _rolling_beta_series(ctx.returns, benchmark, rolling_window)
        bname = str(benchmark.name) if benchmark.name is not None else "Benchmark"
        bctx = ReturnsContext.from_returns(
            benchmark, rf=rf, periods_per_year=periods_per_year, compounded=compounded
        )
        out["cumulative"][bname] = series_to_points(bctx.cumulative)
        out["drawdown"][bname] = series_to_points(bctx.drawdown)

    return out


def _per_col_points(data) -> dict[str, list]:
    if data is None:
        return {}
    res = {}
    for name, s in _each_column(data):
        if isinstance(s, pd.Series):
            res[name] = series_to_points(s)
    return res


def _safe(fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return None


def _rolling_beta_series(returns: PandasData, benchmark: pd.Series, window: int) -> dict[str, list]:
    res = {}
    bench = benchmark.copy()
    for name, s in _each_column(returns):
        joined = pd.concat([s, bench], axis=1).dropna()
        if joined.shape[0] <= window:
            continue
        x = joined.iloc[:, 0]
        y = joined.iloc[:, 1]
        cov = x.rolling(window).cov(y)
        var = y.rolling(window).var()
        beta = (cov / var).dropna()
        res[name] = series_to_points(beta)
    return res


# ---------------------------------------------------------------------------
# Tables: monthly heatmap, EOY returns, worst drawdowns
# ---------------------------------------------------------------------------

def serialize_monthly_heatmap(returns: pd.Series, *, compounded: bool = True) -> dict[str, Any]:
    """Year x Month matrix for the heatmap (uses stats.monthly_returns)."""
    from openstatz import stats

    if isinstance(returns, pd.DataFrame):
        returns = returns[returns.columns[0]]

    mr = stats.monthly_returns(returns, eoy=False, compounded=compounded)
    months = [str(c) for c in mr.columns]
    years = [str(i) for i in mr.index]

    # monthly_returns fills every month of every year, so the months before the
    # first observation and after the last come back as 0.0. They have no data:
    # send null so they render blank instead of as a flat month.
    observed = pd.DatetimeIndex(returns.dropna().index)
    first = (observed.min().year, observed.min().month) if len(observed) else None
    last = (observed.max().year, observed.max().month) if len(observed) else None

    cells = []
    for y in mr.index:
        for i, m in enumerate(mr.columns, start=1):
            value = _f(mr.at[y, m])
            if first is None or not (first <= (int(y), i) <= last):
                value = None
            cells.append({"year": str(y), "month": str(m), "value": value})
    return {"years": years, "months": months, "cells": cells}


def serialize_weekly_heatmap(returns: pd.Series, *, compounded: bool = True) -> dict[str, Any]:
    """Per-ISO-year list of weekly returns for the year-selectable heatmap."""
    if isinstance(returns, pd.DataFrame):
        returns = returns[returns.columns[0]]

    r = returns.dropna()
    if compounded:
        weekly = (1.0 + r).resample("W-SUN").prod() - 1.0
    else:
        weekly = r.resample("W-SUN").sum()

    by_year: dict[str, list] = {}
    for ts, val in weekly.items():
        iso = pd.Timestamp(ts).isocalendar()
        year = str(int(iso[0]))
        week = int(iso[1])
        by_year.setdefault(year, []).append(
            {"week": week, "value": _f(val), "label": pd.Timestamp(ts).strftime("%b %d")}
        )
    years = sorted(by_year.keys())
    return {"years": years, "by_year": by_year}


def serialize_eoy(returns: pd.Series, benchmark: pd.Series | None = None, *, compounded: bool = True) -> dict[str, Any]:
    """End-of-year returns (strategy vs optional benchmark)."""
    from openstatz import stats

    if isinstance(returns, pd.DataFrame):
        returns = returns[returns.columns[0]]

    mr = stats.monthly_returns(returns, eoy=True, compounded=compounded)
    eoy_col = "EOY" if "EOY" in mr.columns else mr.columns[-1]
    rows = [{"year": str(y), "strategy": _f(mr.at[y, eoy_col])} for y in mr.index]

    if benchmark is not None:
        bmr = stats.monthly_returns(benchmark, eoy=True, compounded=compounded)
        beoy = "EOY" if "EOY" in bmr.columns else bmr.columns[-1]
        bmap = {str(y): _f(bmr.at[y, beoy]) for y in bmr.index}
        for row in rows:
            row["benchmark"] = bmap.get(row["year"])
    return {"rows": rows}


def serialize_worst_drawdowns(returns: pd.Series, *, top: int = 10) -> dict[str, Any]:
    """Worst-N drawdown periods (start/valley/end, depth, length), deepest first.

    ``drawdown_pct`` is the episode's full depth (``max drawdown``), the same
    number the rows are sorted by and the Max Drawdown metric reports.
    ``ongoing`` is True for an episode still underwater at the last date: its
    ``end`` is then only the last date of the data, not a recovery.
    """
    from openstatz import stats

    if isinstance(returns, pd.DataFrame):
        returns = returns[returns.columns[0]]

    dd = stats.to_drawdown_series(returns)
    details = stats.drawdown_details(dd)
    if details is None or len(details) == 0:
        return {"rows": []}

    # Only the most recent episode can still be open, and only if the series
    # ends below its high-water mark.
    underwater = len(dd) > 0 and _f(dd.iloc[-1]) is not None and float(dd.iloc[-1]) < 0
    latest_start = str(details["start"].max()) if underwater else None

    details = details.sort_values(by="max drawdown", kind="stable").head(top)
    rows = []
    for _, r in details.iterrows():
        depth = _f(r.get("max drawdown"))
        start = str(r.get("start", ""))
        rows.append(
            {
                "start": start,
                "valley": str(r.get("valley", "")),
                "end": str(r.get("end", "")),
                "days": _f(r.get("days")),
                "max_drawdown": depth,
                "drawdown_pct": depth,
                "ongoing": latest_start is not None and start == latest_start,
            }
        )
    return {"rows": rows}


def serialize_horizon_summary(
    returns: pd.Series,
    *,
    rf: float = 0.0,
    compounded: bool = True,
    periods_per_year: int = 252,
) -> dict[str, Any]:
    """Per-horizon CAGR / Max Drawdown / Calmar (1Y, 3Y, 5Y, all-time).

    One row per horizon; horizons longer than the available history carry
    ``null`` values (the UI renders them as "N/A").
    """
    from openstatz import stats

    if isinstance(returns, pd.DataFrame):
        returns = returns[returns.columns[0]]

    summary = stats.horizon_summary(
        returns, rf=rf, compounded=compounded, periods=periods_per_year
    )
    rows = [
        {
            "horizon": label,
            "cagr": _f(vals.get("cagr")),
            "max_drawdown": _f(vals.get("max_drawdown")),
            "calmar": _f(vals.get("calmar")),
        }
        for label, vals in summary.items()
    ]
    return {"rows": rows}


def serialize_consecutive_losses(returns: pd.Series) -> dict[str, Any]:
    """Distribution of consecutive-losing-period streak lengths.

    Returns a histogram (streak length -> how many times it occurred) plus the
    worst and average streak, so the UI can plot the shape of losing runs
    instead of only the single-number maximum.
    """
    from openstatz import stats

    if isinstance(returns, pd.DataFrame):
        returns = returns[returns.columns[0]]

    lengths = stats.consecutive_loss_lengths(returns)
    if lengths is None or len(lengths) == 0:
        return {"bins": [], "max": 0, "avg": None, "count": 0}

    counts = lengths.value_counts().sort_index()
    bins = [{"length": int(k), "count": int(v)} for k, v in counts.items()]
    return {
        "bins": bins,
        "max": int(lengths.max()),
        "avg": _f(float(lengths.mean())),
        "count": int(len(lengths)),
    }


# ---------------------------------------------------------------------------
# Full bundle
# ---------------------------------------------------------------------------

def _naive_index(data: PandasData) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(data.index)
    return idx.tz_localize(None) if idx.tz is not None else idx


def _from(data: PandasData, start) -> PandasData:
    """Rows of ``data`` on or after ``start`` (compared on naive wall time)."""
    return data[_naive_index(data) >= start]


def _metrics_start(returns: PandasData, benchmark: pd.Series, rf: float):
    """First date of the window reports.metrics analyses when given a benchmark.

    Replays the same steps reports.metrics takes (drop NaN, align the benchmark
    to the strategy's dates, then ``_match_dates``) on the same input, so the
    date is the one its "Start Period" row reports. None if it cannot be found.
    """
    from openstatz import reports, utils

    try:
        r = returns.dropna()
        if len(r) == 0:
            return None
        r = r.copy()
        r.index = _naive_index(r)
        b = utils._prepare_benchmark(benchmark, r.index, rf)
        r, _ = reports._match_dates(r, b)
        return r.index[0] if len(r) else None
    except Exception:  # noqa: BLE001
        return None


def serialize_analysis(
    returns: PandasData,
    benchmark: pd.Series | None = None,
    *,
    rf: float = 0.0,
    compounded: bool = True,
    periods_per_year: int = 252,
    rolling_window: int = 126,
) -> dict[str, Any]:
    """The complete analysis payload: metrics + series + tables + meta."""
    if len(returns) == 0:
        raise ValueError("`returns` is empty — provide at least one observation.")
    primary = returns
    if isinstance(returns, pd.DataFrame) and returns.shape[1] >= 1:
        primary = returns[returns.columns[0]]

    # Guard against a strategy and benchmark that share a name (e.g. both named
    # "Close" from download_returns): that would collide into duplicate columns.
    if benchmark is not None:
        prim_name = str(primary.name) if isinstance(primary, pd.Series) else None
        if str(benchmark.name) == str(prim_name) or benchmark.name is None:
            benchmark = benchmark.rename("Benchmark" if prim_name != "Benchmark" else "Benchmark (bm)")

    # The metrics table is computed over the window reports.metrics settles on:
    # with a benchmark it skips the leading zero returns of both series. Show
    # the header, charts and tables over that same window, or the page carries
    # two start dates and two observation counts. The metrics themselves get
    # the untrimmed input, so they trim exactly once, as they always have.
    metric_returns, metric_benchmark = returns, benchmark
    if benchmark is not None:
        window_start = _metrics_start(returns, benchmark, rf)
        if window_start is not None:
            # window_start is a date of `returns` itself, so nothing empties.
            returns = _from(returns, window_start)
            primary = _from(primary, window_start)
            trimmed = _from(benchmark, window_start)
            benchmark = trimmed if len(trimmed) else benchmark

    start = returns.index[0]
    end = returns.index[-1]

    return {
        "meta": {
            "columns": _columns_of(returns),
            "start": _epoch_seconds(start),
            "end": _epoch_seconds(end),
            "n_periods": int(len(returns)),
            "rf": rf,
            "compounded": compounded,
            "periods_per_year": periods_per_year,
            "has_benchmark": benchmark is not None,
        },
        "metrics": serialize_metrics(
            metric_returns,
            metric_benchmark,
            rf=rf,
            compounded=compounded,
            periods_per_year=periods_per_year,
        ),
        "series": serialize_series(
            returns,
            benchmark,
            rf=rf,
            compounded=compounded,
            periods_per_year=periods_per_year,
            rolling_window=rolling_window,
        ),
        "tables": {
            "monthly_heatmap": serialize_monthly_heatmap(primary, compounded=compounded),
            "weekly_heatmap": serialize_weekly_heatmap(primary, compounded=compounded),
            "eoy": serialize_eoy(primary, benchmark, compounded=compounded),
            "worst_drawdowns": serialize_worst_drawdowns(primary),
            "horizon_summary": serialize_horizon_summary(
                primary, rf=rf, compounded=compounded, periods_per_year=periods_per_year
            ),
            "consecutive_losses": serialize_consecutive_losses(primary),
        },
    }


# ---------------------------------------------------------------------------
# Multi-strategy comparison
# ---------------------------------------------------------------------------

def serialize_comparison(
    returns: pd.DataFrame,
    *,
    rf: float = 0.0,
    compounded: bool = True,
    periods_per_year: int = 252,
    rolling_window: int = 126,
) -> dict[str, Any]:
    """Compare several strategies side by side.

    Returns the full metrics table (one column per strategy) plus overlaid
    cumulative / drawdown / rolling-Sharpe series, so the UI can show which
    strategy is better on each measure. `returns` must be a DataFrame with one
    column per strategy (distinct names).
    """
    from openstatz import stats
    from openstatz._context import ReturnsContext

    if len(returns) == 0:
        raise ValueError("`returns` is empty — provide at least one observation.")
    if isinstance(returns, pd.Series):
        returns = returns.to_frame()
    # Make the column names distinct strings.
    cols = [str(c) for c in returns.columns]
    seen: dict[str, int] = {}
    uniq = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            uniq.append(f"{c} ({seen[c]})")
        else:
            seen[c] = 0
            uniq.append(c)
    returns = returns.copy()
    returns.columns = uniq

    cumulative: dict[str, list] = {}
    drawdown: dict[str, list] = {}
    rolling_sharpe: dict[str, list] = {}
    for col in returns.columns:
        s = returns[col]
        ctx = ReturnsContext.from_returns(
            s, rf=rf, periods_per_year=periods_per_year, compounded=compounded
        )
        cumulative[col] = series_to_points(ctx.cumulative)
        drawdown[col] = series_to_points(ctx.drawdown)
        rs = _safe(lambda c=ctx: stats.rolling_sharpe(c.returns, rolling_period=rolling_window))
        if isinstance(rs, pd.Series):
            rolling_sharpe[col] = series_to_points(rs)

    return {
        "meta": {
            "columns": list(returns.columns),
            "start": _epoch_seconds(returns.index[0]),
            "end": _epoch_seconds(returns.index[-1]),
            "n_periods": int(len(returns)),
            "rf": rf,
            "compounded": compounded,
            "periods_per_year": periods_per_year,
            "has_benchmark": False,
        },
        "metrics": serialize_metrics(
            returns, None, rf=rf, compounded=compounded, periods_per_year=periods_per_year
        ),
        "series": {
            "cumulative": cumulative,
            "drawdown": drawdown,
            "rolling_sharpe": rolling_sharpe,
        },
    }
