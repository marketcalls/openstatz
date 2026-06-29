"""Golden-master parity gate: openstatz must reproduce reference quantstats.

For every pickled fixture (produced by ``generate_fixtures.py`` from the
reference quantstats), this re-runs the identical probes against *openstatz* on
the *exact same pickled inputs* and asserts:

  - scalar / array numbers match to rtol=1e-9, atol=1e-12
  - the ``reports.metrics(mode="full")`` table matches structurally (rows,
    order, labels) and cell-for-cell
  - tables (monthly_returns, drawdown_details) match
  - where quantstats raised, openstatz raises the same exception class

Any change (a kernel rewrite, a refactor) that diverges fails this gate.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(HERE))

from _probes import run_probes  # noqa: E402

# Import openstatz from the repo root (parent of tests/).
sys.path.insert(0, str(HERE.parent.parent))
import openstatz  # noqa: E402

RTOL = 1e-9
ATOL = 1e-12

_FIXTURE_FILES = sorted(FIXTURES.glob("*.pkl"))


def _ids(p):
    return p.stem


@pytest.fixture(scope="module")
def _openstatz_modules():
    return openstatz.stats, openstatz.reports


@pytest.mark.parity
@pytest.mark.skipif(not _FIXTURE_FILES, reason="no parity fixtures; run generate_fixtures.py")
@pytest.mark.parametrize("fixture_path", _FIXTURE_FILES, ids=_ids)
def test_parity(fixture_path, _openstatz_modules):
    stats, reports = _openstatz_modules
    with open(fixture_path, "rb") as fh:
        payload = pickle.load(fh)

    case = {
        "name": payload["name"],
        "returns": payload["returns"],
        "benchmark": payload["benchmark"],
        "compounded": payload["compounded"],
        "periods_per_year": payload["periods_per_year"],
    }
    expected = payload["results"]
    actual = run_probes(stats, reports, case)

    mismatches = []
    for label, exp in expected.items():
        if label not in actual:
            mismatches.append(f"{label}: missing in openstatz output")
            continue
        ok, msg = _compare(exp, actual[label])
        if not ok:
            mismatches.append(f"{label}: {msg}")

    assert not mismatches, (
        f"\n[{payload['name']}] {len(mismatches)} parity mismatch(es):\n  "
        + "\n  ".join(mismatches)
    )


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _is_error(v):
    return isinstance(v, tuple) and len(v) == 2 and v[0] == "__error__"


def _compare(exp, act):
    # Error-sentinel parity: same failure class.
    if _is_error(exp) or _is_error(act):
        if _is_error(exp) and _is_error(act) and exp[1] == act[1]:
            return True, ""
        return False, f"error mismatch: reference={exp!r} openstatz={act!r}"

    if isinstance(exp, pd.DataFrame):
        return _compare_frame(exp, act)
    if isinstance(exp, pd.Series):
        return _compare_series(exp, act)
    if isinstance(exp, np.ndarray):
        return _compare_array(exp, act)
    # scalar
    return _compare_scalar(exp, act)


def _compare_scalar(exp, act):
    try:
        a, b = float(exp), float(act)
    except (TypeError, ValueError):
        return (exp == act), f"scalar !=: {exp!r} vs {act!r}"
    if np.isnan(a) and np.isnan(b):
        return True, ""
    if np.isclose(a, b, rtol=RTOL, atol=ATOL, equal_nan=True):
        return True, ""
    return False, f"{exp!r} vs {act!r} (|d|={abs(a - b):.3e})"


def _compare_array(exp, act):
    act = np.asarray(act)
    if exp.shape != act.shape:
        return False, f"shape {exp.shape} vs {act.shape}"
    if exp.dtype.kind in "OUS" or act.dtype.kind in "OUS":
        return (np.array_equal(exp, act)), "object/string array !="
    if np.allclose(exp, act, rtol=RTOL, atol=ATOL, equal_nan=True):
        return True, ""
    d = np.nanmax(np.abs(exp.astype(float) - act.astype(float)))
    return False, f"array max|d|={d:.3e}"


def _compare_series(exp, act):
    if not isinstance(act, pd.Series):
        return False, f"type {type(act).__name__} != Series"
    if not exp.index.equals(act.index):
        return False, "index mismatch"
    return _compare_array(exp.to_numpy(), act.to_numpy())


def _compare_frame(exp, act):
    if not isinstance(act, pd.DataFrame):
        return False, f"type {type(act).__name__} != DataFrame"
    if list(exp.index) != list(act.index):
        return False, "row labels/order mismatch"
    if list(exp.columns) != list(act.columns):
        return False, "column labels/order mismatch"
    # Try numeric comparison; fall back to exact equality (formatted strings).
    try:
        e = exp.to_numpy(dtype=float)
        a = act.to_numpy(dtype=float)
        if np.allclose(e, a, rtol=RTOL, atol=ATOL, equal_nan=True):
            return True, ""
        d = np.nanmax(np.abs(e - a))
        return False, f"frame max|d|={d:.3e}"
    except (TypeError, ValueError):
        eq = exp.astype(object).equals(act.astype(object))
        if eq:
            return True, ""
        # Locate first differing cell for a useful message.
        for r in exp.index:
            for c in exp.columns:
                if str(exp.at[r, c]) != str(act.at[r, c]):
                    return False, f"cell[{r!r},{c!r}] {exp.at[r, c]!r} vs {act.at[r, c]!r}"
        return False, "frame !="
