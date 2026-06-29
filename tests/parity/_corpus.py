"""Deterministic corpus for the golden-master parity suite.

Every case is fully seeded so the reference (quantstats) fixtures and the
openstatz re-run see byte-identical inputs. Covers the matrix from the
architecture doc section 6.4:

  - single-strategy Series  /  multi-strategy DataFrame
  - with benchmark          /  without benchmark
  - compounded              /  simple
  - daily                   /  monthly frequency
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# A single global seed makes the whole corpus reproducible.
_SEED = 20260629


def _returns_series(n, mu, sigma, seed, freq, start="2016-01-04"):
    rng = np.random.default_rng(seed)
    if freq == "D":
        idx = pd.bdate_range(start=start, periods=n)
    elif freq == "ME":
        idx = pd.date_range(start=start, periods=n, freq="ME")
    else:  # pragma: no cover - defensive
        raise ValueError(freq)
    vals = rng.normal(mu, sigma, size=n)
    return pd.Series(vals, index=idx, name="Strategy")


def build_corpus():
    """Return a list of parity cases.

    Each case is a dict:
        name              str, unique fixture key
        returns           pd.Series | pd.DataFrame
        benchmark         pd.Series | None
        compounded        bool
        periods_per_year  int
    """
    cases = []

    # --- daily single-strategy, no benchmark, compounded ---
    daily = _returns_series(1200, 0.0006, 0.011, _SEED + 1, "D")
    cases.append(
        dict(
            name="daily_single_nobench_comp",
            returns=daily,
            benchmark=None,
            compounded=True,
            periods_per_year=252,
        )
    )

    # --- daily single-strategy, no benchmark, simple (non-compounded) ---
    cases.append(
        dict(
            name="daily_single_nobench_simple",
            returns=daily.copy(),
            benchmark=None,
            compounded=False,
            periods_per_year=252,
        )
    )

    # --- daily single-strategy WITH benchmark, compounded ---
    bench = _returns_series(1200, 0.0004, 0.009, _SEED + 2, "D")
    bench.name = "Benchmark"
    cases.append(
        dict(
            name="daily_single_bench_comp",
            returns=daily.copy(),
            benchmark=bench,
            compounded=True,
            periods_per_year=252,
        )
    )

    # --- daily MULTI-strategy DataFrame, with benchmark ---
    s1 = _returns_series(1000, 0.0007, 0.012, _SEED + 3, "D")
    s2 = _returns_series(1000, 0.0003, 0.008, _SEED + 4, "D")
    multi = pd.DataFrame({"Alpha": s1.values, "Beta": s2.values}, index=s1.index)
    bench2 = _returns_series(1000, 0.0004, 0.009, _SEED + 5, "D")
    bench2.name = "Benchmark"
    cases.append(
        dict(
            name="daily_multi_bench_comp",
            returns=multi,
            benchmark=bench2,
            compounded=True,
            periods_per_year=252,
        )
    )

    # --- monthly single-strategy, no benchmark ---
    monthly = _returns_series(120, 0.008, 0.04, _SEED + 6, "ME")
    cases.append(
        dict(
            name="monthly_single_nobench_comp",
            returns=monthly,
            benchmark=None,
            compounded=True,
            periods_per_year=12,
        )
    )

    return cases
