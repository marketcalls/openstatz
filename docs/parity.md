# Parity contract

"100% parity" is a checklist with an automated gate, not a promise.

## What is checked

The golden master (`tests/parity/`) runs the **reference QuantStats** on a deterministic corpus
and pickles every result. The gate then runs **OpenStatz** on the same pickled inputs and asserts:

- **Numbers** match to `rtol=1e-9, atol=1e-12` (every scalar stat and every array/series).
- **The full metrics report** (`reports.metrics(mode="full")`) matches cell-for-cell, including
  row order and labels — the canonical ordered metric set.
- **Tables** (`monthly_returns`, `drawdown_details`) match structurally.
- **Failure modes** match: where QuantStats raises, OpenStatz raises the same exception class.

## The corpus

Single-strategy Series and multi-strategy DataFrame · with/without benchmark · compounded/simple
· daily/monthly frequency.

## Running it

```bash
# Re-baseline against a reference quantstats checkout (committed afterwards):
QUANTSTATS_SRC=/path/to/quantstats python tests/parity/generate_fixtures.py

# The gate (needs only openstatz + the committed fixtures):
pytest tests/parity -q
```

Any change that diverges — a kernel rewrite, a refactor — fails this gate and does not merge.
