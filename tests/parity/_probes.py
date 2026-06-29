"""Engine-agnostic probe registry — the single source of truth for parity.

The same probes are evaluated against the *reference* quantstats (to generate
golden fixtures) and against *openstatz* (to assert parity). Because parity
means "same engine, same inputs, same args", every probe is called with default
arguments — the corpus, not the args, is what exercises the different code paths.

A probe result is captured as one of:
  - a Python float / int
  - a numpy array (from a pandas Series/DataFrame/Index .values)
  - a ("__error__", "<ExceptionClassName>") sentinel when the call raises

Capturing the exception *class* lets parity assert that openstatz fails exactly
where quantstats fails (identical code => identical edges), instead of silently
skipping hard cases.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Probe specs. Each entry: (func_name, extra_args, extra_kwargs)
# Called as: stats.<func_name>(returns, *extra_args, **extra_kwargs)
# ---------------------------------------------------------------------------

RETURNS_ONLY = [
    ("comp", (), {}),
    ("expected_return", (), {}),
    ("geometric_mean", (), {}),
    ("ghpr", (), {}),
    ("avg_return", (), {}),
    ("avg_win", (), {}),
    ("avg_loss", (), {}),
    ("best", ("day",), {}),
    ("worst", ("day",), {}),
    ("volatility", (), {}),
    ("sharpe", (), {}),
    ("smart_sharpe", (), {}),
    ("sortino", (), {}),
    ("smart_sortino", (), {}),
    ("adjusted_sortino", (), {}),
    ("omega", (), {}),
    ("cagr", (), {}),
    ("rar", (), {}),
    ("skew", (), {}),
    ("kurtosis", (), {}),
    ("calmar", (), {}),
    ("ulcer_index", (), {}),
    ("ulcer_performance_index", (), {}),
    ("upi", (), {}),
    ("serenity_index", (), {}),
    ("risk_of_ruin", (), {}),
    ("ror", (), {}),
    ("value_at_risk", (), {}),
    ("var", (), {}),
    ("conditional_value_at_risk", (), {}),
    ("cvar", (), {}),
    ("expected_shortfall", (), {}),
    ("tail_ratio", (), {}),
    ("payoff_ratio", (), {}),
    ("win_loss_ratio", (), {}),
    ("profit_ratio", (), {}),
    ("profit_factor", (), {}),
    ("cpc_index", (), {}),
    ("common_sense_ratio", (), {}),
    ("outlier_win_ratio", (), {}),
    ("outlier_loss_ratio", (), {}),
    ("recovery_factor", (), {}),
    ("risk_return_ratio", (), {}),
    ("max_drawdown", (), {}),
    ("kelly_criterion", (), {}),
    ("exposure", (), {}),
    ("win_rate", (), {}),
    ("consecutive_wins", (), {}),
    ("consecutive_losses", (), {}),
    ("probabilistic_sharpe_ratio", (), {}),
    ("probabilistic_sortino_ratio", (), {}),
    ("probabilistic_adjusted_sortino_ratio", (), {}),
    ("gain_to_pain_ratio", (), {}),
]

# Series / array valued (returns only). Compared element-wise.
RETURNS_ONLY_SERIES = [
    ("compsum", (), {}),
    ("pct_rank", (), {}),
    ("to_drawdown_series", (), {}),
    ("rolling_sharpe", (), {}),
    ("rolling_sortino", (), {}),
    ("rolling_volatility", (), {}),
    ("outliers", (), {}),
    ("remove_outliers", (), {}),
]

# Require a benchmark: stats.<func>(returns, benchmark, *args, **kwargs)
BENCH = [
    ("treynor_ratio", (), {}),
    ("r_squared", (), {}),
    ("r2", (), {}),
    ("information_ratio", (), {}),
    ("greeks", (), {}),
    ("rolling_greeks", (), {}),
]

# Table-valued probes handled specially (monthly_returns, drawdown_details).


def _to_native(value):
    """Normalize any probe return value to something picklable & comparable."""
    if isinstance(value, (pd.Series, pd.DataFrame)):
        return value
    if isinstance(value, pd.Index):
        return np.asarray(value)
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _safe_call(fn, *args, **kwargs):
    try:
        return _to_native(fn(*args, **kwargs))
    except Exception as exc:  # noqa: BLE001 - we intentionally record the class
        return ("__error__", type(exc).__name__)


def run_probes(stats, reports, case):
    """Evaluate every probe for one corpus case against a given library.

    Parameters
    ----------
    stats : module
        The library's ``stats`` module (openstatz.stats or quantstats.stats).
    reports : module
        The library's ``reports`` module.
    case : dict
        One entry from build_corpus().

    Returns
    -------
    dict[str, Any]  label -> captured value
    """
    returns = case["returns"]
    benchmark = case["benchmark"]
    out = {}

    for name, a, kw in RETURNS_ONLY:
        fn = getattr(stats, name, None)
        if fn is None:
            out[name] = ("__error__", "MissingSymbol")
            continue
        out[name] = _safe_call(fn, _copy(returns), *a, **kw)

    for name, a, kw in RETURNS_ONLY_SERIES:
        fn = getattr(stats, name, None)
        if fn is None:
            out[name] = ("__error__", "MissingSymbol")
            continue
        out[name] = _safe_call(fn, _copy(returns), *a, **kw)

    if benchmark is not None:
        for name, a, kw in BENCH:
            fn = getattr(stats, name, None)
            if fn is None:
                out[name] = ("__error__", "MissingSymbol")
                continue
            out[name] = _safe_call(fn, _copy(returns), _copy(benchmark), *a, **kw)

    # Table probes
    out["monthly_returns"] = _safe_call(
        getattr(stats, "monthly_returns"), _copy(returns)
    )
    dd = _safe_call(getattr(stats, "to_drawdown_series"), _copy(returns))
    if not (isinstance(dd, tuple) and dd and dd[0] == "__error__"):
        out["drawdown_details"] = _safe_call(
            getattr(stats, "drawdown_details"), dd
        )
    else:
        out["drawdown_details"] = ("__error__", "UpstreamDrawdownFailed")

    # Full report metric table (display-formatted; exact structural parity).
    out["reports.metrics.full"] = _safe_call(
        reports.metrics,
        _copy(returns),
        benchmark=_copy(benchmark) if benchmark is not None else None,
        mode="full",
        display=False,
        sep=True,
    )

    return out


def _copy(obj):
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.copy()
    return obj
