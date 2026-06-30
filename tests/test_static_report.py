"""
Tests for the self-contained modern tearsheet (openstatz.dashboard).

These render the prebuilt React UI into a single offline HTML file with the
analysis embedded. They require the built UI to be present
(openstatz/app/static or app/dist); if it is not, the suite skips rather than
fails so a source checkout without `npm run build` still passes.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import pytest

import openstatz as osz
from openstatz.app import static_report

pytestmark = pytest.mark.skipif(
    static_report._static_dir() is None,
    reason="built web UI not present (run: cd app && npm run build)",
)


@pytest.fixture
def returns():
    idx = pd.bdate_range("2019-01-01", periods=600)
    rng = np.random.default_rng(7)
    return pd.Series(rng.normal(0.0006, 0.011, len(idx)), index=idx, name="Strategy")


@pytest.fixture
def bench(returns):
    rng = np.random.default_rng(11)
    return pd.Series(rng.normal(0.0004, 0.009, len(returns)), index=returns.index, name="^NSEI")


def _embedded_payload(html: str) -> dict:
    m = re.search(
        r"window\.__OPENSTATZ_DATA__=(\{.*?\});window\.__OPENSTATZ_HEALTH__",
        html,
        re.DOTALL,
    )
    assert m, "embedded data bundle not found"
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_dashboard_is_self_contained(returns, bench):
    html = osz.dashboard(returns, bench, output=None)
    # No external asset requests — everything inlined into one file.
    assert 'src="/assets' not in html
    assert 'href="/assets' not in html
    assert "<style>" in html
    assert '<script type="module">' in html


def test_dashboard_embeds_data_before_bundle(returns, bench):
    html = osz.dashboard(returns, bench, output=None)
    assert "window.__OPENSTATZ_DATA__=" in html
    assert "window.__OPENSTATZ_HEALTH__=" in html
    # Bootstrap must run before the (deferred) module bundle mounts the app.
    assert html.index("window.__OPENSTATZ_DATA__=") < html.index('<script type="module">')


def test_embedded_payload_shape(returns, bench):
    payload = _embedded_payload(osz.dashboard(returns, bench, output=None))
    assert set(payload) >= {"meta", "metrics", "series", "tables"}
    assert payload["meta"]["has_benchmark"] is True
    assert payload["meta"]["columns"][0] == "Strategy"
    assert len(payload["metrics"]["rows"]) > 0


def test_dashboard_without_benchmark(returns):
    payload = _embedded_payload(osz.dashboard(returns, output=None))
    assert payload["meta"]["has_benchmark"] is False


def test_dashboard_writes_file(returns, bench, tmp_path):
    out = tmp_path / "report.html"
    html = osz.dashboard(returns, bench, output=str(out), title="My Tearsheet")
    assert out.exists()
    assert out.read_text(encoding="utf-8") == html
    assert "<title>My Tearsheet</title>" in html


def test_embed_json_neutralizes_script_breakout():
    # A `</script>` and the U+2028/U+2029 separators must be escaped so they can
    # neither close the <script> element nor break the JS string.
    s = static_report._embed_json({"x": "a</script>b", "y": "c d e"})
    assert "</script>" not in s
    assert "<\\/script>" in s
    assert " " not in s and " " not in s
    assert "\\u2028" in s and "\\u2029" in s
