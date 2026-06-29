"""Kernel correctness gates.

The pure-NumPy kernels are the source of truth: they must be bit-identical to the
original pandas implementations they replace (architecture section 6.4). Numba is
intentionally not used (compatibility), so there is a single code path to verify.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openstatz import _kernels  # noqa: E402


def _rng():
    return np.random.default_rng(2026)


def test_mc_cumulative_matches_pandas_cumprod():
    r = _rng().normal(0.0006, 0.012, 300)
    idx = np.empty((300, 50), dtype=np.intp)
    idx[:, 0] = np.arange(300)
    rg = _rng()
    for j in range(1, 50):
        idx[:, j] = rg.permutation(300)

    sim = r[idx]
    expected = np.cumprod(1.0 + sim, axis=0) - 1.0
    got = _kernels.mc_cumulative(r, idx)
    assert np.array_equal(got, expected)


def test_max_drawdown_columns_matches_pandas_loop():
    rng = _rng()
    cumulative = np.cumprod(1.0 + rng.normal(0.0005, 0.01, (250, 40)), axis=0) - 1.0

    # Reference: the original per-column pandas computation.
    expected = []
    df = pd.DataFrame(cumulative)
    for col in df.columns:
        growth = df[col] + 1.0
        rmax = growth.cummax()
        expected.append(((growth - rmax) / rmax).min())
    expected = np.asarray(expected)

    got = _kernels.max_drawdown_columns(cumulative)
    assert np.allclose(got, expected, rtol=0, atol=0)


def test_max_consecutive_matches_count_consecutive():
    from openstatz.utils import _count_consecutive

    rng = _rng()
    for _ in range(20):
        mask = rng.random(200) > 0.5
        s = pd.Series(mask.astype(int))
        ref = int(_count_consecutive(s).max())
        assert _kernels.max_consecutive(mask) == ref


def test_using_numba_is_false():
    # Numba is intentionally avoided for the time being.
    assert _kernels.using_numba() is False
    assert _kernels.NUMBA_AVAILABLE is False
