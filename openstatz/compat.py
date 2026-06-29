#!/usr/bin/env python
#
# OpenStatz — optional quantstats compatibility shim.
#
# Lets existing code that does ``import quantstats as qs`` run unmodified on top
# of OpenStatz, WITHOUT shipping a package that silently shadows a real
# quantstats install. It is strictly opt-in: nothing happens until you call
# ``install_quantstats_shim()``.
#
#     import openstatz.compat
#     openstatz.compat.install_quantstats_shim()
#     import quantstats as qs          # -> this is OpenStatz
#     qs.stats.sharpe(returns)
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

import sys

_SUBMODULES = ("stats", "utils", "reports", "plots")


def install_quantstats_shim(override: bool = False):
    """Alias ``quantstats`` (and its public submodules) to OpenStatz in sys.modules.

    Parameters
    ----------
    override : bool, default False
        If a real ``quantstats`` is already imported, leave it in place unless
        ``override=True``. Returns the module now bound to ``quantstats``.
    """
    import openstatz

    existing = sys.modules.get("quantstats")
    if existing is not None and existing is not openstatz and not override:
        return existing

    sys.modules["quantstats"] = openstatz
    for sub in _SUBMODULES:
        mod = getattr(openstatz, sub, None)
        if mod is not None:
            sys.modules[f"quantstats.{sub}"] = mod
    return openstatz


def uninstall_quantstats_shim() -> None:
    """Remove the shim entries from sys.modules (best-effort)."""
    import openstatz

    if sys.modules.get("quantstats") is openstatz:
        del sys.modules["quantstats"]
    for sub in _SUBMODULES:
        key = f"quantstats.{sub}"
        if sys.modules.get(key) is getattr(openstatz, sub, None):
            sys.modules.pop(key, None)
