#!/usr/bin/env python
#
# OpenStatz — ReturnsContext: compute the common derived series ONCE.
#
# Today every metric re-prepares returns and re-derives cumulative / drawdown
# series on each call. For a single scalar that is fine, but the API layer
# computes ~80 metrics + a dozen chart series per request off the *same* input.
# ReturnsContext computes the shared pieces once (cleaned returns, compounded
# cumulative, log returns, drawdown) and exposes a content hash for caching the
# resulting bundle.
#
# This module is purely additive: it changes no metric numbers. It uses the
# library's own functions so any derived series is identical to calling the
# public API directly. Imports are deferred to avoid an import-time cycle with
# stats/utils.
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PandasData = pd.Series | pd.DataFrame


def _content_hash(returns: PandasData, rf: float, periods_per_year: int, compounded: bool) -> str:
    """Stable content hash of the (returns, params) tuple for bundle caching."""
    h = hashlib.blake2b(digest_size=16)
    arr = np.ascontiguousarray(returns.to_numpy(dtype="float64"))
    h.update(arr.tobytes())
    # Index identity matters (dates drive period/rolling logic).
    idx = returns.index
    h.update(np.asarray(idx.view("int64") if hasattr(idx, "view") else idx).tobytes())
    if isinstance(returns, pd.DataFrame):
        h.update(("|".join(map(str, returns.columns))).encode())
    else:
        h.update(str(returns.name).encode())
    h.update(repr((float(rf), int(periods_per_year), bool(compounded))).encode())
    return h.hexdigest()


@dataclass(frozen=True)
class ReturnsContext:
    """Pre-computed, shared view of a returns series for a single analysis.

    Attributes
    ----------
    returns : cleaned/prepared returns (NaN->0, inf scrubbed, prices->pct_change)
    cumulative : compounded ``(1+r).cumprod()-1`` (or cumulative sum if simple)
    log_returns : ``log(1+r)``
    drawdown : drawdown series from the cumulative path
    rf, periods_per_year, compounded : the parameters this context was built with
    key : content hash of (returns, params) for caching downstream bundles
    """

    returns: PandasData
    cumulative: PandasData
    log_returns: PandasData
    drawdown: PandasData
    rf: float = 0.0
    periods_per_year: int = 252
    compounded: bool = True
    key: str = ""
    _meta: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_returns(
        cls,
        returns: PandasData,
        rf: float = 0.0,
        periods_per_year: int = 252,
        compounded: bool = True,
        prepare: bool = True,
    ) -> ReturnsContext:
        from . import stats as _stats  # deferred to avoid import cycle
        from . import utils as _utils

        prepared = _utils._prepare_returns(returns, rf) if prepare else returns.copy()

        if compounded:
            cumulative = _stats.compsum(prepared)
        else:
            cumulative = prepared.cumsum()

        log_returns = _utils.log_returns(prepared)
        drawdown = _stats.to_drawdown_series(prepared)

        return cls(
            returns=prepared,
            cumulative=cumulative,
            log_returns=log_returns,
            drawdown=drawdown,
            rf=rf,
            periods_per_year=periods_per_year,
            compounded=compounded,
            key=_content_hash(prepared, rf, periods_per_year, compounded),
        )

    @property
    def is_multi(self) -> bool:
        return isinstance(self.returns, pd.DataFrame)

    @property
    def n_periods(self) -> int:
        return int(len(self.returns))

    def column(self, name: str | None = None) -> ReturnsContext:
        """Return a single-column ReturnsContext (no recompute of inputs)."""
        if not self.is_multi:
            return self
        col = name if name is not None else self.returns.columns[0]
        sub = self.returns[col]
        return ReturnsContext.from_returns(
            sub,
            rf=self.rf,
            periods_per_year=self.periods_per_year,
            compounded=self.compounded,
            prepare=False,
        )
