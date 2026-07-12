"""End-to-end tests for the optional FastAPI adapter (openstatz.app).

Skipped automatically when the [app] extra (fastapi) is not installed, so the
core test run never depends on it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from openstatz.app.server import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def _payload(multi=False, benchmark=False):
    idx = pd.bdate_range("2019-01-01", periods=400)
    rng = np.random.default_rng(7)
    dates = [d.strftime("%Y-%m-%d") for d in idx]
    if multi:
        returns = {
            "Alpha": list(rng.normal(0.0006, 0.011, 400)),
            "Beta": list(rng.normal(0.0003, 0.008, 400)),
        }
    else:
        returns = {"Strategy": list(rng.normal(0.0006, 0.011, 400))}
    body = {"dates": dates, "returns": returns}
    if benchmark:
        body["benchmark"] = list(rng.normal(0.0004, 0.009, 400))
    return body


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    assert "version" in j
    assert isinstance(j["numba"], bool)


def test_analyze_single(client):
    r = client.post("/api/analyze", json=_payload())
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["meta"]["n_periods"] == 400
    assert not j["meta"]["has_benchmark"]
    assert len(j["metrics"]["rows"]) > 50
    assert "cumulative" in j["series"]
    assert len(j["series"]["cumulative"]["Strategy"]) == 400
    assert {"years", "months", "cells"} <= j["tables"]["monthly_heatmap"].keys()


def test_analyze_with_benchmark_has_rolling_beta(client):
    r = client.post("/api/analyze", json=_payload(benchmark=True))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["meta"]["has_benchmark"]
    assert "Benchmark" in j["metrics"]["columns"]
    assert "rolling_beta" in j["series"]
    assert j["tables"]["eoy"]["rows"][0].get("benchmark") is not None


def test_analyze_multi(client):
    r = client.post("/api/analyze", json=_payload(multi=True))
    assert r.status_code == 200, r.text
    j = r.json()
    assert set(j["meta"]["columns"]) == {"Alpha", "Beta"}
    assert "Alpha" in j["series"]["cumulative"]
    assert "Beta" in j["series"]["cumulative"]


def test_length_mismatch_is_422(client):
    body = _payload()
    body["returns"]["Strategy"] = body["returns"]["Strategy"][:-5]
    r = client.post("/api/analyze", json=body)
    assert r.status_code == 422


def test_response_matches_serializer_directly():
    # The HTTP path must equal calling the serializer directly (no math in API).
    from openstatz.app import serializers

    body = _payload(benchmark=True)
    idx = pd.to_datetime(pd.Index(body["dates"]))
    returns = pd.Series(body["returns"]["Strategy"], index=idx, name="Strategy")
    bench = pd.Series(body["benchmark"], index=idx, name="Benchmark")
    direct = serializers.serialize_analysis(returns, bench)

    client = TestClient(create_app())
    http = client.post("/api/analyze", json=body).json()
    # Compare a representative scalar metric cell.
    def sharpe(bundle):
        for row in bundle["metrics"]["rows"]:
            if row["label"] == "Sharpe":
                return row["values"]["Strategy"]
        return None

    assert sharpe(direct) == sharpe(http)


def test_analyze_symbol_uses_provider(client, monkeypatch):
    # No network: stub the provider download so the symbol endpoint is testable.
    from openstatz import providers

    idx = pd.bdate_range("2021-01-01", periods=300)
    rng = np.random.default_rng(3)

    def _fake(symbol, provider="yfinance", period="5y"):
        s = pd.Series(rng.normal(0.0006, 0.012, 300), index=idx, name=symbol)
        return s

    monkeypatch.setattr(providers, "download_returns", _fake)

    r = client.post(
        "/api/analyze/symbol",
        json={"symbol": "RELIANCE.NS", "benchmark_symbol": "^NSEI", "period": "2y"},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["meta"]["columns"] == ["RELIANCE.NS"]
    assert j["meta"]["has_benchmark"]
    assert "^NSEI" in j["metrics"]["columns"]
    assert len(j["series"]["cumulative"]["RELIANCE.NS"]) == 300


def test_analyze_symbol_empty_is_404(client, monkeypatch):
    from openstatz import providers

    idx = pd.bdate_range("2021-01-01", periods=10)

    def _empty(symbol, provider="yfinance", period="5y"):
        return pd.Series([0.0] * 10, index=idx, name=symbol)

    monkeypatch.setattr(providers, "download_returns", _empty)
    r = client.post("/api/analyze/symbol", json={"symbol": "BADTICKER"})
    assert r.status_code == 404


def test_compare_symbols(client, monkeypatch):
    from openstatz import providers

    idx = pd.bdate_range("2021-01-01", periods=400)
    rng = np.random.default_rng(5)

    def _fake(symbol, provider="yfinance", period="5y"):
        return pd.Series(rng.normal(0.0006, 0.012, 400), index=idx, name=symbol)

    monkeypatch.setattr(providers, "download_returns", _fake)
    r = client.post("/api/compare/symbols", json={"symbols": ["AAPL", "NVDA", "MSFT"], "period": "5y"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["meta"]["columns"] == ["AAPL", "NVDA", "MSFT"]
    assert set(j["series"]["cumulative"].keys()) == {"AAPL", "NVDA", "MSFT"}
    assert "AAPL" in j["metrics"]["columns"] and "NVDA" in j["metrics"]["columns"]


def test_compare_needs_two_symbols(client):
    r = client.post("/api/compare/symbols", json={"symbols": ["AAPL"]})
    assert r.status_code == 422


def test_compare_custom_strategies(client):
    idx = pd.bdate_range("2021-01-01", periods=300)
    rng = np.random.default_rng(9)
    dates = [d.strftime("%Y-%m-%d") for d in idx]
    body = {
        "dates": dates,
        "strategies": {
            "Alpha": list(rng.normal(0.0007, 0.011, 300)),
            "Beta": list(rng.normal(0.0003, 0.008, 300)),
        },
    }
    r = client.post("/api/compare", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["meta"]["columns"] == ["Alpha", "Beta"]


# --- Robustness / security regression tests -------------------------------

def test_analyze_empty_input_is_422(client):
    """Empty dates/returns must be a clean 422, not a 500 (IndexError)."""
    r = client.post("/api/analyze", json={"dates": [], "returns": {"S": []}})
    assert r.status_code == 422, r.text


def test_compare_invalid_dates_is_422(client):
    """Unparseable dates must be a clean 422, not a 500 (DateParseError)."""
    body = {
        "dates": ["not-a-date", "also-bad"],
        "strategies": {"A": [0.1, 0.2], "B": [0.1, 0.2]},
    }
    r = client.post("/api/compare", json=body)
    assert r.status_code == 422, r.text


def test_spa_path_traversal_is_contained(tmp_path, monkeypatch):
    """The SPA catch-all must never serve files outside the static root, even
    when the request smuggles URL-encoded `..` segments (`%2e%2e`)."""
    import openstatz.app.server as server

    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html>spa</html>")
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET")

    monkeypatch.setattr(server, "_static_dir", lambda: static)
    c = TestClient(server.create_app())

    r = c.get("/%2e%2e/secret.txt")
    assert "TOP-SECRET" not in r.text  # must not leak the sibling file
    # Falls back to the SPA shell so client-side routing still works.
    assert "spa" in r.text


def test_cors_rejects_arbitrary_origin(client):
    """A wildcard CORS policy would let any site read a user's local server;
    an untrusted Origin must not be reflected back."""
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert r.headers.get("access-control-allow-origin") != "http://evil.example"


def test_cors_allows_env_override(monkeypatch):
    """OPENSTATZ_CORS_ORIGINS lets an operator opt a trusted origin back in."""
    monkeypatch.setenv("OPENSTATZ_CORS_ORIGINS", "http://my-ui.example")
    c = TestClient(create_app())
    r = c.get("/api/health", headers={"Origin": "http://my-ui.example"})
    assert r.headers.get("access-control-allow-origin") == "http://my-ui.example"


# --- Tearsheet analytics: rolling win rate, horizon, loss streaks ---------

def test_analyze_includes_tearsheet_analytics(client):
    r = client.post("/api/analyze", json=_payload())
    assert r.status_code == 200, r.text
    j = r.json()
    col = j["meta"]["columns"][0]

    # Rolling win rate is keyed by the strategy column name (so the UI finds it).
    assert "rolling_win_rate" in j["series"]
    assert col in j["series"]["rolling_win_rate"]

    # Horizon table: 1Y/3Y/5Y/All rows, CAGR/MaxDD/Calmar each.
    horizons = {row["horizon"] for row in j["tables"]["horizon_summary"]["rows"]}
    assert {"1Y", "3Y", "5Y", "All"} <= horizons

    # Consecutive-loss distribution: bins + summary stats.
    cl = j["tables"]["consecutive_losses"]
    assert set(cl) >= {"bins", "max", "avg", "count"}
    if cl["bins"]:
        assert all(b["length"] >= 1 and b["count"] >= 1 for b in cl["bins"])
