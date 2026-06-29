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
