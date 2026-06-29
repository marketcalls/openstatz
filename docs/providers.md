# Data providers

OpenStatz fetches a returns series for a symbol through a small pluggable interface
(`openstatz/providers.py`). The default wraps yfinance (the same path QuantStats uses).

```python
import openstatz as os

# Default: yfinance
r = os.providers.download_returns("SPY", period="5y")

# OpenAlgo (needs the `openalgo` SDK and a running OpenAlgo server)
from openstatz.providers import OpenAlgoProvider, register_provider
register_provider(OpenAlgoProvider(api_key="YOUR_KEY", host="http://127.0.0.1:5000"))
r = os.providers.download_returns(
    "RELIANCE", provider="openalgo", start_date="2023-01-01", end_date="2024-01-01"
)
```

## Writing a provider

Implement the `ReturnsProvider` protocol (a `name` and a `returns(symbol, **kwargs) -> pd.Series`)
and `register_provider(...)`. Backends should be imported lazily inside `returns()` so the core
library stays importable without them.
