#!/usr/bin/env python
#
# Self-contained modern tearsheet — the same React dashboard you get from
# `openstatz serve`, baked into a single offline .html file.
#
# How it works: the built UI (openstatz/app/static) is a single-page app that
# normally fetches its data from the FastAPI server. Here we instead compute the
# analysis bundle with `serializers.serialize_analysis` (pure numpy/pandas — no
# FastAPI), inline the built JS/CSS, and inject the bundle onto `window` so the
# page renders straight from embedded data. No server, no `[app]` extra, no
# network: it works on a plain `pip install openstatz`.
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

import json
import re
import webbrowser
from pathlib import Path
from typing import Any

import pandas as pd

from openstatz.app import serializers

PandasData = pd.Series | pd.DataFrame


def _static_dir() -> Path | None:
    """Locate the built web UI: the packaged copy first, then a dev build."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "static",  # shipped inside the wheel (openstatz/app/static)
        here.parent.parent / "app" / "dist",  # local dev build (repo app/dist)
    ]
    for c in candidates:
        if (c / "index.html").exists():
            return c
    return None


def _embed_json(obj: Any) -> str:
    """JSON safe to drop inside a <script> as a JS object literal.

    `serialize_analysis` already maps NaN/inf -> null, so `allow_nan=False`
    is a guard, not a transform. We additionally neutralise the sequences
    that can break out of a <script> element or a JS string literal: the
    `</` opener and the U+2028 / U+2029 line separators (legal in JSON but
    not in JS string literals).
    """
    text = json.dumps(obj, ensure_ascii=False, allow_nan=False)
    text = text.replace("</", "<\\/")
    text = text.replace(chr(0x2028), "\\u2028")
    text = text.replace(chr(0x2029), "\\u2029")
    return text


def _inline_assets(index_html: str, static: Path) -> str:
    """Replace the hashed <script src> / <link href> with inline tags so the
    report is a single file with no external requests."""

    def inline_script(m: re.Match[str]) -> str:
        src = m.group("src").lstrip("/")
        js = (static / src).read_text(encoding="utf-8")
        # A literal </script> inside the bundle would end the element early.
        js = js.replace("</script", "<\\/script")
        return f'<script type="module">{js}</script>'

    def inline_style(m: re.Match[str]) -> str:
        href = m.group("href").lstrip("/")
        css = (static / href).read_text(encoding="utf-8")
        return f"<style>{css}</style>"

    html = re.sub(
        r'<script\b[^>]*\bsrc="(?P<src>[^"]+)"[^>]*>\s*</script>',
        inline_script,
        index_html,
    )
    html = re.sub(
        r'<link\b[^>]*\bhref="(?P<href>[^"]+\.css)"[^>]*>',
        inline_style,
        html,
    )
    return html


def build_report_html(
    returns: PandasData,
    benchmark: pd.Series | None = None,
    *,
    rf: float = 0.0,
    compounded: bool = True,
    periods_per_year: int = 252,
    rolling_window: int = 126,
    title: str = "OpenStatz Tearsheet",
) -> str:
    """Render the modern dashboard as a single self-contained HTML string."""
    static = _static_dir()
    if static is None:
        raise FileNotFoundError(
            "The built OpenStatz web UI was not found. Reinstall openstatz, or "
            "build it from source with: (cd app && npm ci && npm run build)."
        )

    bundle = serializers.serialize_analysis(
        returns,
        benchmark,
        rf=rf,
        compounded=compounded,
        periods_per_year=periods_per_year,
        rolling_window=rolling_window,
    )

    # version is resolved lazily to avoid an import cycle at package init.
    from openstatz import __version__

    health = {"status": "ok", "version": __version__, "numba": False}

    index_html = (static / "index.html").read_text(encoding="utf-8")
    html = _inline_assets(index_html, static)

    boot = (
        "<script>"
        f"window.__OPENSTATZ_DATA__={_embed_json(bundle)};"
        f"window.__OPENSTATZ_HEALTH__={_embed_json(health)};"
        "</script>"
    )
    # Run the bootstrap before the (deferred) module bundle. Injecting it right
    # before that script guarantees the data global exists when the app mounts.
    if "<script type=\"module\">" in html:
        html = html.replace("<script type=\"module\">", boot + "<script type=\"module\">", 1)
    else:  # pragma: no cover - defensive: no module script found
        html = html.replace("</head>", boot + "</head>", 1)

    if title:
        # lambda replacement so a backslash or `\1` in the title is treated as
        # a literal, not an re backreference.
        html = re.sub(
            r"<title>.*?</title>",
            lambda _m: f"<title>{title}</title>",
            html,
            count=1,
            flags=re.DOTALL,
        )
    return html


def dashboard(
    returns: PandasData,
    benchmark: pd.Series | None = None,
    *,
    output: str | None = "openstatz-report.html",
    rf: float = 0.0,
    compounded: bool = True,
    periods_per_year: int = 252,
    rolling_window: int = 126,
    title: str = "OpenStatz Tearsheet",
    open_browser: bool = False,
) -> str:
    """Generate the modern OpenStatz tearsheet as a self-contained HTML file.

    This is the same web dashboard served by ``openstatz serve``, rendered to a
    single offline file with the analysis baked in — no server and no ``[app]``
    extra required. It works on a plain ``pip install openstatz``.

    Parameters
    ----------
    returns : pd.Series or pd.DataFrame
        Strategy returns (a DataFrame's first column is treated as primary).
    benchmark : pd.Series, optional
        Benchmark returns for comparison.
    output : str or None, default "openstatz-report.html"
        Path to write the HTML file. If ``None`` the HTML is only returned.
    rf : float, default 0.0
        Risk-free rate (decimal).
    compounded : bool, default True
        Compound returns for cumulative calculations.
    periods_per_year : int, default 252
        Periods per year for annualization.
    rolling_window : int, default 126
        Window for rolling Sharpe / volatility / beta series.
    title : str, default "OpenStatz Tearsheet"
        Document title.
    open_browser : bool, default False
        Open the written file in the default browser.

    Returns
    -------
    str
        The full HTML document.

    Examples
    --------
    >>> import openstatz as os
    >>> os.dashboard(returns, benchmark, output="report.html")
    """
    html = build_report_html(
        returns,
        benchmark,
        rf=rf,
        compounded=compounded,
        periods_per_year=periods_per_year,
        rolling_window=rolling_window,
        title=title,
    )

    if output is not None:
        path = Path(output)
        path.write_text(html, encoding="utf-8")
        if open_browser:
            webbrowser.open(path.resolve().as_uri())

    return html
