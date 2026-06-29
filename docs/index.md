# OpenStatz

A modern rebuild of [QuantStats](https://github.com/ranaroussi/quantstats): the same trusted
portfolio analytics, a fast pandas + NumPy core, and an optional modern web UI — with
**enforced output parity** to the original library.

## Install

```bash
pip install openstatz            # library
pip install "openstatz[app]"     # + FastAPI server and web API
```

## Three usage modes, one codebase

```python
import openstatz as os

# 1. Drop-in functions
os.stats.sharpe(returns)
os.reports.metrics(returns, mode="full", display=True)

# 2. Pandas extension
os.extend_pandas()
returns.sharpe()

# 3. Web app
#   $ openstatz serve      ->  http://127.0.0.1:8000  (+ the app/ React UI)
```

!!! note "Import alias"
    The documented alias is `os` (`import openstatz as os`), which shadows the stdlib `os`
    inside files that use it. The QuantStats `qs` alias works too. To run existing QuantStats
    code unchanged, `openstatz.compat.install_quantstats_shim()` then `import quantstats as qs`.

## Why a rebuild?

- **100% numerical parity, enforced not promised** — see [Parity contract](parity.md).
- **Same engine = free parity** — compute stays on pandas; vectorized NumPy kernels accelerate
  a few loop-shaped hot spots, each gated by a parity test.
- **The web UI is an optional layer**, not a replacement; the core never imports FastAPI or any
  UI dependency.
