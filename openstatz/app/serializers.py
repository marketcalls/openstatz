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

    ``display`` preserves the exact reports.metrics formatting; ``values`` is the
    same cell parsed back to a float when possible (None otherwise).
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
    )

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

    columns = [str(c) for c in df.columns]
    rows = []
    for label, row in df.iterrows():
        display = {str(c): _stringify(row[c]) for c in df.columns}
        values = {str(c): _parse_number(row[c]) for c in df.columns}
        rows.append({"label": str(label), "values": values, "display": display})
    return {"columns": columns, "rows": rows}


def _stringify(v) -> str:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return ""
    return str(v)


def _parse_number(v) -> float | None:
    """Best-effort parse of a (possibly formatted) metric cell to float."""
    f = _f(v)
    if f is not None:
        return f
    s = str(v).strip().replace(",", "")
    if s.endswith("%"):
        # reports.metrics emits ﹪-labelled metrics as plain fractions (no '%'),
        # so a trailing '%' here is a cosmetic suffix on an already-scaled number
        # (e.g. correlation "0.68%"). Strip it; do NOT divide by 100.
        s = s[:-1].strip()
    return _f(s)


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
    cells = []
    for y in mr.index:
        for m in mr.columns:
            cells.append({"year": str(y), "month": str(m), "value": _f(mr.at[y, m])})
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
    """Worst-N drawdown periods (start/valley/end, depth, length)."""
    from openstatz import stats

    if isinstance(returns, pd.DataFrame):
        returns = returns[returns.columns[0]]

    dd = stats.to_drawdown_series(returns)
    details = stats.drawdown_details(dd)
    if details is None or len(details) == 0:
        return {"rows": []}

    details = details.sort_values(by="max drawdown").head(top)
    rows = []
    for _, r in details.iterrows():
        rows.append(
            {
                "start": str(r.get("start", "")),
                "valley": str(r.get("valley", "")),
                "end": str(r.get("end", "")),
                "days": _f(r.get("days")),
                "max_drawdown": _f(r.get("max drawdown")),
                "drawdown_pct": _f(r.get("99% max drawdown", r.get("max drawdown"))),
            }
        )
    return {"rows": rows}


# ---------------------------------------------------------------------------
# Full bundle
# ---------------------------------------------------------------------------

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
    primary = returns
    if isinstance(returns, pd.DataFrame) and returns.shape[1] >= 1:
        primary = returns[returns.columns[0]]

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
            returns, benchmark, rf=rf, compounded=compounded, periods_per_year=periods_per_year
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
        },
    }
