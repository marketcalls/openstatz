"""
Regression tests for the tearsheet accuracy fixes in 0.5.0.

Each test pins one reported defect. They run on the serializer (the data the
dashboard renders) and on reports.metrics, with no browser and no built UI.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from openstatz import reports, stats, utils
from openstatz.app import serializers


@pytest.fixture
def returns():
    """Ten years of daily returns that start with a flat week and end underwater."""
    idx = pd.bdate_range("2016-09-27", "2026-09-24")
    rng = np.random.default_rng(7)
    r = pd.Series(rng.normal(0.0006, 0.012, len(idx)), index=idx, name="Strategy")
    r.iloc[:5] = 0.0  # not yet invested
    r.iloc[-60:] = -0.002  # still in a drawdown at the last date
    return r


@pytest.fixture
def bench(returns):
    rng = np.random.default_rng(11)
    noise = rng.normal(0.0004, 0.01, len(returns))
    return pd.Series(0.3 * returns.to_numpy() + noise, index=returns.index, name="NIFTY")


def _row(metrics_json, label):
    return next(r for r in metrics_json["rows"] if r["label"] == label)


# ---------------------------------------------------------------------------
# 1. Percent metrics were rounded to 2 decimals as fractions (13.52% -> 0.14)
# ---------------------------------------------------------------------------


def test_raw_metrics_are_not_rounded(returns, bench):
    m = reports.metrics(returns, bench, display=False, mode="full", raw=True)
    assert m.at["CAGR%", "Strategy"] == pytest.approx(stats.cagr(returns.loc["2016-10-04":]))
    assert m.at["Max Drawdown", "Strategy"] == pytest.approx(
        stats.max_drawdown(returns.loc["2016-10-04":])
    )
    # Not a 2-decimal fraction any more.
    assert round(m.at["CAGR%", "Strategy"], 2) != m.at["CAGR%", "Strategy"]
    assert "CAGR%" in m.attrs["percent_rows"]
    assert "Sharpe" not in m.attrs["percent_rows"]
    assert "Longest DD Days" in m.attrs["integer_rows"]


def test_default_metrics_output_is_unchanged(returns, bench):
    # Without raw=True the table stays QuantStats-identical: rounded, with
    # the benchmark rows as strings.
    m = reports.metrics(returns, bench, display=False, mode="full")
    assert m.at["CAGR%", "Strategy"] == round(m.at["CAGR%", "Strategy"], 2)
    assert isinstance(m.at["Correlation", "Strategy"], str)
    assert "percent_rows" not in m.attrs


def test_dashboard_metric_values_are_full_precision(returns, bench):
    out = serializers.serialize_analysis(returns, bench)
    cagr = _row(out["metrics"], "CAGR%")
    exact = stats.cagr(returns.loc["2016-10-04":])
    assert cagr["values"]["Strategy"] == pytest.approx(exact)
    assert cagr["display"]["Strategy"] == f"{exact * 100:,.2f}%"
    for label in ("Volatility (ann.)", "Time in Market", "MTD", "YTD", "3M", "6M", "1Y"):
        v = _row(out["metrics"], label)["values"]["Strategy"]
        assert v is not None
        assert _row(out["metrics"], label)["display"]["Strategy"].endswith("%")


def test_dashboard_metric_display_text(returns, bench):
    out = serializers.serialize_analysis(returns, bench)
    assert _row(out["metrics"], "Sharpe")["display"]["Strategy"].count(".") == 1
    assert not _row(out["metrics"], "Sharpe")["display"]["Strategy"].endswith("%")
    days = _row(out["metrics"], "Longest DD Days")
    assert days["display"]["Strategy"] == f"{days['values']['Strategy']:,.0f}"
    start = _row(out["metrics"], "Start Period")
    assert start["values"]["Strategy"] is None
    assert start["display"]["Strategy"] == "2016-10-04"


# ---------------------------------------------------------------------------
# 2. Labels used U+FE6A and U+221A: not typeable, not printable on cp1252
# ---------------------------------------------------------------------------


def test_metric_labels_are_ascii(returns, bench):
    for kwargs in ({"display": False}, {"display": False, "raw": True}):
        m = reports.metrics(returns, bench, mode="full", **kwargs)
        for label in m.index:
            label.encode("cp1252")  # raises UnicodeEncodeError on U+FE6A / U+221A
            assert label.isascii(), label
        assert "CAGR%" in m.index
        assert "Sortino/sqrt(2)" in m.index


def test_metrics_print_on_cp1252_console(returns, bench, capsys):
    reports.metrics(returns, bench, mode="full", display=True)
    capsys.readouterr().out.encode("cp1252")


# ---------------------------------------------------------------------------
# 3. The prepared-returns cache ignored the series name (and more)
# ---------------------------------------------------------------------------


def test_renamed_series_keeps_its_own_chart_keys(returns, bench):
    serializers.serialize_analysis(returns.rename("A"), bench)
    out = serializers.serialize_analysis(returns.rename("B"), bench)
    assert out["meta"]["columns"] == ["B"]
    for chart in ("cumulative", "drawdown", "rolling_sharpe", "rolling_volatility", "rolling_win_rate"):
        assert "B" in out["series"][chart], chart
        assert "A" not in out["series"][chart], chart


def test_cache_key_covers_dataframe_columns(returns):
    df = pd.DataFrame({"X": returns, "Y": returns * 2})
    utils._prepare_returns(df)
    again = utils._prepare_returns(df.rename(columns={"X": "P", "Y": "Q"}))
    assert list(again.columns) == ["P", "Q"]


def test_cache_does_not_mix_excess_and_plain_returns(returns):
    utils._PREPARE_RETURNS_CACHE.clear()
    clean = stats.rar(returns, rf=0.05)
    utils._PREPARE_RETURNS_CACHE.clear()
    stats.cagr(returns, rf=0.05)  # caches plain (non-excess) returns
    assert stats.rar(returns, rf=0.05) == pytest.approx(clean)


# ---------------------------------------------------------------------------
# 4 + 5. Worst Drawdowns: ongoing episode shown as recovered; not sorted by
# the depth it displays
# ---------------------------------------------------------------------------


def test_ongoing_drawdown_is_flagged(returns):
    rows = serializers.serialize_worst_drawdowns(returns)["rows"]
    ongoing = [r for r in rows if r["ongoing"]]
    assert len(ongoing) == 1
    assert ongoing[0]["end"] == "2026-09-24"
    assert all(not r["ongoing"] for r in rows if r is not ongoing[0])


def test_recovered_series_has_no_ongoing_drawdown(returns):
    recovered = returns.copy()
    recovered.iloc[-60:] = 0.0
    recovered.iloc[-1] = 1.0  # a new high on the last day
    rows = serializers.serialize_worst_drawdowns(recovered)["rows"]
    assert not any(r["ongoing"] for r in rows)


def test_worst_drawdowns_sorted_by_displayed_depth(returns):
    rows = serializers.serialize_worst_drawdowns(returns)["rows"]
    shown = [r["drawdown_pct"] for r in rows]
    assert shown == sorted(shown)
    assert all(r["drawdown_pct"] == r["max_drawdown"] for r in rows)
    # The deepest row matches the Max Drawdown metric.
    assert shown[0] / 100 == pytest.approx(stats.max_drawdown(returns))


# ---------------------------------------------------------------------------
# 6. Correlation and Treynor came back as "0.32%" strings
# ---------------------------------------------------------------------------


def test_correlation_and_treynor_are_plain_numbers(returns, bench):
    m = reports.metrics(returns, bench, display=False, mode="full", raw=True)
    trimmed = returns.loc["2016-10-04":]
    corr = m.at["Correlation", "Strategy"]
    assert isinstance(corr, float)
    assert corr == pytest.approx(bench.loc["2016-10-04":].corr(trimmed))

    out = serializers.serialize_analysis(returns, bench)
    for label in ("Correlation", "Treynor Ratio", "Beta", "Alpha"):
        cell = _row(out["metrics"], label)["display"]["Strategy"]
        assert not cell.endswith("%"), (label, cell)
    assert _row(out["metrics"], "Correlation")["values"]["Strategy"] == pytest.approx(corr)


# ---------------------------------------------------------------------------
# 7. Monthly heatmap filled months with no data as 0.0
# ---------------------------------------------------------------------------


def test_heatmap_months_without_data_are_blank(returns):
    cells = serializers.serialize_monthly_heatmap(returns)["cells"]
    by = {(c["year"], c["month"]): c["value"] for c in cells}
    for month in ("OCT", "NOV", "DEC"):
        assert by[("2026", month)] is None
    for month in ("JAN", "FEB", "AUG"):
        assert by[("2016", month)] is None
    assert by[("2016", "SEP")] is not None  # data starts 2016-09-27
    assert by[("2026", "SEP")] is not None
    assert by[("2020", "JUN")] is not None


# ---------------------------------------------------------------------------
# 9. Header start date and observation count disagreed with the metrics
# ---------------------------------------------------------------------------


def test_header_window_matches_metrics_start(returns, bench):
    out = serializers.serialize_analysis(returns, bench)
    start = _row(out["metrics"], "Start Period")["display"]["Strategy"]
    assert pd.Timestamp(out["meta"]["start"], unit="s").strftime("%Y-%m-%d") == start
    assert out["meta"]["n_periods"] == len(returns.loc[start:])
    first_point = out["series"]["cumulative"]["Strategy"][0]["time"]
    assert pd.Timestamp(first_point, unit="s").strftime("%Y-%m-%d") == start


def test_without_benchmark_nothing_is_trimmed(returns):
    out = serializers.serialize_analysis(returns)
    assert out["meta"]["n_periods"] == len(returns)
    assert pd.Timestamp(out["meta"]["start"], unit="s") == returns.index[0]
