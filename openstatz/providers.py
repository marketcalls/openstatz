#!/usr/bin/env python
#
# OpenStatz — data providers.
#
# A tiny pluggable interface for fetching a returns series from a symbol. The
# default provider wraps yfinance (exactly the path quantstats uses, preserving
# behavior). An optional OpenAlgo provider pulls daily history via the OpenAlgo
# SDK for users in that ecosystem.
#
# No provider imports its backend at module load — backends are imported lazily
# inside ``returns()`` so the core library stays importable without yfinance or
# the OpenAlgo SDK present.
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class ReturnsProvider(Protocol):
    """Anything that can turn a symbol into a daily returns Series."""

    name: str

    def returns(self, symbol: str, **kwargs) -> pd.Series:  # pragma: no cover - protocol
        ...


class YFinanceProvider:
    """Default provider — wraps ``utils.download_returns`` (yfinance).

    Kept byte-for-byte equivalent to quantstats' download path.
    """

    name = "yfinance"

    def returns(self, symbol: str, period: str = "max", proxy: str | None = None) -> pd.Series:
        from . import utils

        return utils.download_returns(symbol, period=period, proxy=proxy)


class OpenAlgoProvider:
    """Optional provider — daily returns from the OpenAlgo SDK.

    Requires the ``openalgo`` SDK and a running OpenAlgo server. Construction is
    cheap (no import); the SDK is imported on first ``returns()`` call.

    Parameters
    ----------
    api_key : str
        OpenAlgo API key.
    host : str, default "http://127.0.0.1:5000"
        OpenAlgo server URL.
    exchange : str, default "NSE"
    interval : str, default "D"
    """

    name = "openalgo"

    def __init__(
        self,
        api_key: str,
        host: str = "http://127.0.0.1:5000",
        exchange: str = "NSE",
        interval: str = "D",
    ):
        self.api_key = api_key
        self.host = host
        self.exchange = exchange
        self.interval = interval

    def _client(self):
        try:
            from openalgo import api  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise ImportError(
                "OpenAlgoProvider needs the OpenAlgo SDK. Install it with "
                "`pip install openalgo` and ensure an OpenAlgo server is running."
            ) from exc
        return api(api_key=self.api_key, host=self.host)

    def returns(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        exchange: str | None = None,
        interval: str | None = None,
    ) -> pd.Series:
        client = self._client()
        df = client.history(
            symbol=symbol,
            exchange=exchange or self.exchange,
            interval=interval or self.interval,
            start_date=start_date,
            end_date=end_date,
        )
        if not isinstance(df, pd.DataFrame) or "close" not in {c.lower() for c in df.columns}:
            raise ValueError(f"OpenAlgo returned no usable history for {symbol!r}: {df!r}")
        # Normalize the close column name and compute returns.
        close_col = next(c for c in df.columns if c.lower() == "close")
        close = df[close_col].astype(float)
        out = close.pct_change(fill_method=None).fillna(0)
        out.name = symbol
        try:
            out.index = pd.to_datetime(out.index).tz_localize(None)
        except (TypeError, ValueError):
            out.index = pd.to_datetime(out.index)
        return out


# Registry --------------------------------------------------------------------

_REGISTRY: dict[str, ReturnsProvider] = {}


def register_provider(provider: ReturnsProvider) -> None:
    _REGISTRY[provider.name] = provider


def get_provider(name: str = "yfinance") -> ReturnsProvider:
    if name not in _REGISTRY:
        raise KeyError(f"unknown provider {name!r}; registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def download_returns(symbol: str, provider: str = "yfinance", **kwargs) -> pd.Series:
    """Fetch a daily returns Series for ``symbol`` from the named provider."""
    return get_provider(provider).returns(symbol, **kwargs)


# Default registration (yfinance always available as the default path).
register_provider(YFinanceProvider())
