#!/usr/bin/env python
#
# OpenStatz — loop-shaped compute kernels (pure NumPy).
#
# These kernels replace per-column pandas Python loops with vectorized NumPy and
# are bit-identical to the original code they replace (gated by tests/parity and
# tests/test_kernels). They carry the real speedups (e.g. ~11x on Monte Carlo
# per-column max-drawdown) with zero extra dependencies.
#
# NOTE: Numba is intentionally NOT used for the time being — it currently creates
# compatibility issues (e.g. numba's NumPy shims lag new NumPy releases). The
# pure-NumPy path is the one and only path. ``using_numba()`` exists so callers
# (the API health check, the UI) can report acceleration state; it always
# returns False today. If/when Numba is reintroduced it must stay behind the
# parity gate and never break import when unavailable.
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

import numpy as np

# Numba is deliberately disabled. Kept as a constant so downstream code that
# reports kernel acceleration state has a stable symbol to read.
NUMBA_AVAILABLE = False


def using_numba() -> bool:
    """Whether kernels dispatch to a Numba-accelerated path. Always False today
    (Numba intentionally avoided for compatibility); kernels are pure NumPy."""
    return NUMBA_AVAILABLE


# ---------------------------------------------------------------------------
# Kernels (pure NumPy)
# ---------------------------------------------------------------------------

def mc_cumulative(returns_array: np.ndarray, idx_matrix: np.ndarray) -> np.ndarray:
    """Cumulative returns for each shuffled Monte Carlo path.

    Parameters
    ----------
    returns_array : (n_periods,) float64
    idx_matrix    : (n_periods, sims) int — column j is a permutation of indices

    Returns
    -------
    (n_periods, sims) float64 — ``cumprod(1 + r) - 1`` per column.

    Bit-identical to the original ``np.cumprod(1 + sim_returns, axis=0) - 1``.
    """
    returns_array = np.ascontiguousarray(returns_array, dtype=np.float64)
    sim = returns_array[idx_matrix]
    return np.cumprod(1.0 + sim, axis=0) - 1.0


def max_drawdown_columns(cumulative: np.ndarray) -> np.ndarray:
    """Per-column maximum drawdown from a (n_periods, sims) cumulative array.

    Bit-identical to the original per-column pandas loop:
        growth = col + 1; rmax = growth.cummax(); ((growth-rmax)/rmax).min()
    but vectorized across all columns at once.
    """
    cumulative = np.ascontiguousarray(cumulative, dtype=np.float64)
    growth = cumulative + 1.0
    running_max = np.maximum.accumulate(growth, axis=0)
    drawdown = (growth - running_max) / running_max
    return drawdown.min(axis=0)


def max_consecutive(mask: np.ndarray) -> int:
    """Longest run of True in a 1-D boolean array (matches _count_consecutive().max())."""
    mask = np.asarray(mask, dtype=bool)
    best = 0
    cur = 0
    for v in mask:
        if v:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return int(best)
