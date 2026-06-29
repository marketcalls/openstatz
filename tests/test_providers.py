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
