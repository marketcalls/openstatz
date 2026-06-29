"""Opt-in quantstats-compat shim: `import quantstats` resolves to OpenStatz."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openstatz  # noqa: E402
from openstatz import compat  # noqa: E402


@pytest.fixture
def clean_quantstats_modules():
    # Snapshot and restore any real quantstats entries so the shim test never
    # leaks into other tests (e.g. the parity fixtures generator).
    saved = {k: v for k, v in sys.modules.items() if k == "quantstats" or k.startswith("quantstats.")}
    for k in list(saved):
        del sys.modules[k]
    try:
        yield
    finally:
        for k in [k for k in list(sys.modules) if k == "quantstats" or k.startswith("quantstats.")]:
            del sys.modules[k]
        sys.modules.update(saved)


def test_shim_aliases_quantstats_to_openstatz(clean_quantstats_modules):
    compat.install_quantstats_shim()
    import quantstats as qs

    assert qs is openstatz
    assert qs.stats is openstatz.stats

    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0, 0.01, 200), index=pd.bdate_range("2020-01-01", periods=200))
    assert qs.stats.sharpe(r) == openstatz.stats.sharpe(r)

    compat.uninstall_quantstats_shim()
    assert "quantstats" not in sys.modules


def test_shim_respects_existing_quantstats(clean_quantstats_modules):
    sentinel = object()
    sys.modules["quantstats"] = sentinel  # pretend a real quantstats is imported
    result = compat.install_quantstats_shim(override=False)
    assert result is sentinel
    assert sys.modules["quantstats"] is sentinel

    # override=True replaces it.
    result = compat.install_quantstats_shim(override=True)
    assert result is openstatz
