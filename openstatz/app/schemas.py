#!/usr/bin/env python
#
# OpenStatz API schemas (Pydantic v2). These typed request/response models are
# the contract the web UI codes against and the source for generated TypeScript
# types (see scripts/export_openapi.py). The server performs no math; it builds
# the response dict via serializers and validates it against AnalysisResponse.
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """One or more return series on a shared date axis, plus optional benchmark.

    A single key in ``returns`` is a single-strategy analysis; multiple keys is a
    multi-strategy comparison.
    """

    dates: list[str] = Field(..., description="Shared date axis (ISO 8601 strings).")
    returns: dict[str, list[float]] = Field(
        ..., description="Strategy name -> per-date returns (decimal, not %)."
    )
    benchmark: list[float] | None = Field(
        None, description="Optional benchmark returns aligned to `dates`."
    )
    benchmark_name: str = Field("Benchmark", description="Label for the benchmark column.")
    rf: float = Field(0.0, description="Risk-free rate (annual, decimal).")
    compounded: bool = Field(True, description="Compound returns (vs simple sum).")
    periods_per_year: int = Field(252, description="Annualization factor.")
    rolling_window: int = Field(126, ge=2, description="Rolling-metric window length.")


class SymbolRequest(BaseModel):
    """Analyze a ticker fetched server-side via a data provider (e.g. yfinance)."""

    symbol: str = Field(..., description="Ticker, e.g. 'RELIANCE.NS', 'SPY'.")
    benchmark_symbol: str | None = Field(
        None, description="Optional benchmark ticker, e.g. '^NSEI'."
    )
    provider: str = Field("yfinance", description="Registered data provider name.")
    period: str = Field("5y", description="History period passed to the provider.")
    rf: float = Field(0.0, description="Risk-free rate (annual, decimal).")
    compounded: bool = Field(True)
    periods_per_year: int = Field(252)
    rolling_window: int = Field(126, ge=2)


class CompareSymbolsRequest(BaseModel):
    """Compare several tickers fetched server-side (e.g. ['AAPL', 'NVDA'])."""

    symbols: list[str] = Field(..., min_length=2, description="Tickers to compare.")
    provider: str = Field("yfinance")
    period: str = Field("5y")
    rf: float = Field(0.0)
    compounded: bool = Field(True)
    periods_per_year: int = Field(252)
    rolling_window: int = Field(126, ge=2)


class CompareRequest(BaseModel):
    """Compare several custom strategies on a shared date axis."""

    dates: list[str] = Field(..., description="Shared date axis (ISO 8601).")
    strategies: dict[str, list[float]] = Field(
        ..., description="Strategy name -> per-date returns (2+ strategies)."
    )
    rf: float = Field(0.0)
    compounded: bool = Field(True)
    periods_per_year: int = Field(252)
    rolling_window: int = Field(126, ge=2)


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class Meta(BaseModel):
    columns: list[str]
    start: int
    end: int
    n_periods: int
    rf: float
    compounded: bool
    periods_per_year: int
    has_benchmark: bool


class MetricRow(BaseModel):
    label: str
    values: dict[str, float | None]
    display: dict[str, str]


class MetricsTable(BaseModel):
    columns: list[str]
    rows: list[MetricRow]


class SeriesPoint(BaseModel):
    time: int
    value: float | None


class HeatmapCell(BaseModel):
    year: str
    month: str
    value: float | None


class MonthlyHeatmap(BaseModel):
    years: list[str]
    months: list[str]
    cells: list[HeatmapCell]


class EoyRow(BaseModel):
    year: str
    strategy: float | None = None
    benchmark: float | None = None


class EoyTable(BaseModel):
    rows: list[EoyRow]


class DrawdownRow(BaseModel):
    start: str
    valley: str
    end: str
    days: float | None = None
    max_drawdown: float | None = None
    drawdown_pct: float | None = None


class DrawdownTable(BaseModel):
    rows: list[DrawdownRow]


class WeeklyCell(BaseModel):
    week: int
    value: float | None
    label: str


class WeeklyHeatmap(BaseModel):
    years: list[str]
    by_year: dict[str, list[WeeklyCell]]


class Tables(BaseModel):
    monthly_heatmap: MonthlyHeatmap
    weekly_heatmap: WeeklyHeatmap
    eoy: EoyTable
    worst_drawdowns: DrawdownTable


class AnalysisResponse(BaseModel):
    meta: Meta
    metrics: MetricsTable
    # chart -> column -> points. Dynamic column keys => Record<string, ...> in TS.
    series: dict[str, dict[str, list[SeriesPoint]]]
    tables: Tables


class ComparisonResponse(BaseModel):
    meta: Meta
    metrics: MetricsTable
    series: dict[str, dict[str, list[SeriesPoint]]]


class HealthResponse(BaseModel):
    status: str
    version: str
    numba: bool
