"""Generate golden-master parity fixtures from the *reference* quantstats.

Run this once (and re-run only when intentionally re-baselining):

    python tests/parity/generate_fixtures.py

It locates a reference quantstats install. By default it looks for the source
checkout at ``D:/testing/quantstats`` (env override: ``QUANTSTATS_SRC``), then
falls back to any pip-installed ``quantstats``. Every probe result for every
corpus case is pickled into ``fixtures/<case>.pkl``. ``test_parity.py`` then
asserts openstatz reproduces these byte-for-byte (numbers to rtol=1e-9).
"""

from __future__ import annotations

import importlib
import os
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"

# Make the local _corpus / _probes importable when run as a script.
sys.path.insert(0, str(HERE))

from _corpus import build_corpus  # noqa: E402
from _probes import run_probes  # noqa: E402


def _load_reference_quantstats():
    """Import the reference quantstats, preferring a source checkout."""
    src = os.environ.get("QUANTSTATS_SRC", r"D:/testing/quantstats")
    if Path(src, "quantstats", "__init__.py").exists():
        sys.path.insert(0, src)
    # Drop any cached 'quantstats' (e.g. a namespace-package resolution).
    for mod in [m for m in sys.modules if m == "quantstats" or m.startswith("quantstats.")]:
        del sys.modules[mod]
    qs = importlib.import_module("quantstats")
    if getattr(qs.stats, "__file__", None) is None:  # pragma: no cover
        raise RuntimeError(
            "Resolved a namespace-only 'quantstats'. Set QUANTSTATS_SRC to the "
            "quantstats source checkout (the folder that contains quantstats/__init__.py)."
        )
    return qs


def main() -> int:
    qs = _load_reference_quantstats()
    print(f"reference quantstats: {qs.stats.__file__}")
    FIXTURES.mkdir(parents=True, exist_ok=True)

    corpus = build_corpus()
    for case in corpus:
        results = run_probes(qs.stats, qs.reports, case)
        # Persist the inputs alongside the results so the test re-runs on the
        # exact same data without re-deriving the (seeded) corpus.
        payload = {
            "name": case["name"],
            "returns": case["returns"],
            "benchmark": case["benchmark"],
            "compounded": case["compounded"],
            "periods_per_year": case["periods_per_year"],
            "results": results,
        }
        out = FIXTURES / f"{case['name']}.pkl"
        with open(out, "wb") as fh:
            pickle.dump(payload, fh, protocol=4)
        n_ok = sum(
            1
            for v in results.values()
            if not (isinstance(v, tuple) and v and v[0] == "__error__")
        )
        print(f"  wrote {out.name}: {len(results)} probes ({n_ok} value, "
              f"{len(results) - n_ok} error-sentinel)")

    print(f"\nDone. {len(corpus)} fixtures in {FIXTURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
