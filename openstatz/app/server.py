#!/usr/bin/env python
#
# OpenStatz FastAPI server — the optional [app] adapter.
#
# Responsibilities: parse a typed request into pandas objects, call the library
# core, serialize the result, and return it. NO analytics math lives here.
#
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

import pandas as pd

from openstatz import __version__
from openstatz.app import serializers
from openstatz.app.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    HealthResponse,
    SymbolRequest,
)


def _build_returns(req: AnalyzeRequest) -> pd.Series | pd.DataFrame:
    idx = pd.to_datetime(pd.Index(req.dates))
    names = list(req.returns.keys())
    if not names:
        raise ValueError("`returns` must contain at least one strategy series.")
    for name, vals in req.returns.items():
        if len(vals) != len(idx):
            raise ValueError(
                f"series '{name}' length {len(vals)} != dates length {len(idx)}"
            )
    if len(names) == 1:
        name = names[0]
        return pd.Series(req.returns[name], index=idx, name=name)
    return pd.DataFrame({n: req.returns[n] for n in names}, index=idx)


def _build_benchmark(req: AnalyzeRequest):
    if req.benchmark is None:
        return None
    idx = pd.to_datetime(pd.Index(req.dates))
    if len(req.benchmark) != len(idx):
        raise ValueError("benchmark length != dates length")
    return pd.Series(req.benchmark, index=idx, name=req.benchmark_name)


def create_app():
    """Construct the FastAPI application (imported lazily by run_server)."""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    from openstatz._kernels import using_numba

    app = FastAPI(
        title="OpenStatz API",
        version=__version__,
        description="Portfolio analytics — library core served as JSON.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__, numba=using_numba())

    @app.post("/api/analyze", response_model=AnalysisResponse)
    def analyze(req: AnalyzeRequest) -> AnalysisResponse:
        try:
            returns = _build_returns(req)
            benchmark = _build_benchmark(req)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        bundle = serializers.serialize_analysis(
            returns,
            benchmark,
            rf=req.rf,
            compounded=req.compounded,
            periods_per_year=req.periods_per_year,
            rolling_window=req.rolling_window,
        )
        return AnalysisResponse.model_validate(bundle)

    @app.post("/api/analyze/symbol", response_model=AnalysisResponse)
    def analyze_symbol(req: SymbolRequest) -> AnalysisResponse:
        from openstatz import providers

        try:
            returns = providers.download_returns(
                req.symbol, provider=req.provider, period=req.period
            )
        except KeyError as exc:  # unknown provider
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - network/provider failure
            raise HTTPException(
                status_code=502, detail=f"provider fetch failed for {req.symbol!r}: {exc}"
            ) from exc

        if returns is None or len(returns) == 0 or float(returns.abs().sum()) == 0.0:
            raise HTTPException(status_code=404, detail=f"no data for symbol {req.symbol!r}")
        returns = returns.copy()
        returns.name = req.symbol

        benchmark = None
        if req.benchmark_symbol:
            try:
                benchmark = providers.download_returns(
                    req.benchmark_symbol, provider=req.provider, period=req.period
                )
                benchmark = benchmark.copy()
                benchmark.name = req.benchmark_symbol
                # Align benchmark to the strategy's dates.
                benchmark = benchmark.reindex(returns.index).fillna(0)
            except Exception:  # noqa: BLE001 - benchmark is best-effort
                benchmark = None

        bundle = serializers.serialize_analysis(
            returns,
            benchmark,
            rf=req.rf,
            compounded=req.compounded,
            periods_per_year=req.periods_per_year,
            rolling_window=req.rolling_window,
        )
        return AnalysisResponse.model_validate(bundle)

    _mount_ui(app)
    return app


def _static_dir():
    """Locate the built web UI: the packaged copy first, then a dev build."""
    from pathlib import Path

    here = Path(__file__).resolve().parent
    candidates = [
        here / "static",  # shipped inside the wheel (openstatz/app/static)
        here.parent.parent / "app" / "dist",  # local dev build (repo app/dist)
    ]
    for c in candidates:
        if (c / "index.html").exists():
            return c
    return None


def _mount_ui(app) -> None:
    """Serve the pre-built React UI from the same origin as the API, so end
    users need no Node.js — just `pip install openstatz[app]` and `openstatz serve`."""
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    static = _static_dir()
    if static is None:
        return

    # Hashed assets under /assets; index.html for everything else (single page).
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def _index():
        return FileResponse(static / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def _spa(path: str):
        candidate = static / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static / "index.html")


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    import uvicorn

    if reload:
        uvicorn.run("openstatz.app.server:create_app", host=host, port=port, reload=True, factory=True)
    else:
        uvicorn.run(create_app(), host=host, port=port)
