"""ReturnsContext computes shared derived series ONCE, identical to public API."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openstatz as ostz  # noqa: E402
from openstatz._context import ReturnsContext  # noqa: E402


def _returns():
    rng = np.random.default_rng(11)
    idx = pd.bdate_range("2019-01-01", periods=500)
    return pd.Series(rng.normal(0.0005, 0.011, 500), index=idx, name="Strategy")


def test_context_series_match_public_api():
    r = _returns()
    ctx = ReturnsContext.from_returns(r, compounded=True)

    prepared = ostz.utils._prepare_returns(r)
    pd.testing.assert_series_equal(ctx.returns, prepared)
    pd.testing.assert_series_equal(ctx.cumulative, ostz.stats.compsum(prepared))
    pd.testing.assert_series_equal(ctx.drawdown, ostz.stats.to_drawdown_series(prepared))
    pd.testing.assert_series_equal(ctx.log_returns, ostz.utils.log_returns(prepared))


def test_context_hash_is_stable_and_param_sensitive():
    r = _returns()
    a = ReturnsContext.from_returns(r, rf=0.0, compounded=True)
    b = ReturnsContext.from_returns(r, rf=0.0, compounded=True)
    c = ReturnsContext.from_returns(r, rf=0.0, compounded=False)
    assert a.key == b.key
    assert a.key != c.key
    assert len(a.key) == 32  # 16-byte blake2b hex


def test_context_multi_column_and_subset():
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2020-01-01", periods=300)
    df = pd.DataFrame(
        {"A": rng.normal(0, 0.01, 300), "B": rng.normal(0, 0.02, 300)}, index=idx
    )
    ctx = ReturnsContext.from_returns(df)
    assert ctx.is_multi
    assert ctx.n_periods == 300
    sub = ctx.column("B")
    assert not sub.is_multi
    pd.testing.assert_series_equal(
        sub.cumulative, ostz.stats.compsum(ostz.utils._prepare_returns(df)["B"])
    )
