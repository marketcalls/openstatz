"""Provider abstraction: registry, yfinance default, OpenAlgo graceful degrade."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openstatz import providers  # noqa: E402


def test_default_provider_is_yfinance():
    p = providers.get_provider()
    assert p.name == "yfinance"
    assert isinstance(p, providers.YFinanceProvider)


def test_unknown_provider_raises():
    with pytest.raises(KeyError):
        providers.get_provider("does-not-exist")


def test_yfinance_provider_wraps_download_returns(monkeypatch):
    # No network: stub utils.download_returns and assert the provider delegates.
    from openstatz import utils

    idx = pd.bdate_range("2020-01-01", periods=5)
    fake = pd.Series([0.0, 0.01, -0.02, 0.03, 0.0], index=idx, name="SPY")
    captured = {}

    def _stub(ticker, period="max", proxy=None):
        captured["ticker"] = ticker
        captured["period"] = period
        return fake

    monkeypatch.setattr(utils, "download_returns", _stub)
    out = providers.download_returns("SPY", provider="yfinance", period="1y")
    pd.testing.assert_series_equal(out, fake)
    assert captured == {"ticker": "SPY", "period": "1y"}


def test_openalgo_provider_construction_is_cheap():
    # Constructing must not import the SDK or hit the network.
    p = providers.OpenAlgoProvider(api_key="x", host="http://localhost:5000")
    assert p.name == "openalgo"
    assert p.exchange == "NSE"


def test_openalgo_provider_errors_clearly_without_sdk():
    p = providers.OpenAlgoProvider(api_key="x")
    try:
        from openalgo import api  # noqa: F401

        has_sdk = True
    except Exception:
        has_sdk = False

    if has_sdk:
        pytest.skip("OpenAlgo SDK present; skipping the missing-SDK assertion")
    with pytest.raises(ImportError, match="OpenAlgo SDK"):
        p.returns("RELIANCE")


class _FakeClient:
    """Stands in for the OpenAlgo SDK client; records the history() call."""

    def __init__(self):
        self.calls = []

    def history(self, **kwargs):
        self.calls.append(kwargs)
        idx = pd.date_range("2024-01-01", periods=4, freq="D")
        return pd.DataFrame({"close": [100.0, 101.0, 99.0, 102.0]}, index=idx)


def _fake_provider(monkeypatch, **kwargs):
    p = providers.OpenAlgoProvider(api_key="x", **kwargs)
    client = _FakeClient()
    monkeypatch.setattr(p, "_client", lambda: client)
    return p, client


def test_openalgo_provider_defaults_to_broker_api(monkeypatch):
    p, client = _fake_provider(monkeypatch)
    out = p.returns("RELIANCE", start_date="2024-01-01", end_date="2024-01-04")
    assert out.name == "RELIANCE"
    # "api" is the server default and is not sent, so older SDKs keep working.
    assert "source" not in client.calls[0]


def test_openalgo_provider_reads_historify(monkeypatch):
    p, client = _fake_provider(monkeypatch, source="db")
    p.returns("RELIANCE", start_date="2024-01-01", end_date="2024-01-04")
    assert client.calls[0]["source"] == "db"


def test_openalgo_provider_source_per_call(monkeypatch):
    p, client = _fake_provider(monkeypatch)
    p.returns("RELIANCE", start_date="2024-01-01", end_date="2024-01-04", source="db")
    p.returns("RELIANCE", start_date="2024-01-01", end_date="2024-01-04")
    assert client.calls[0]["source"] == "db"
    assert "source" not in client.calls[1]


def test_openalgo_provider_rejects_unknown_source():
    with pytest.raises(ValueError, match="Historify"):
        providers.OpenAlgoProvider(api_key="x", source="cache")
