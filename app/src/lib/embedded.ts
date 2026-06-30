// Static-report bootstrap. When OpenStatz renders a self-contained offline
// tearsheet (openstatz.dashboard(...)), the Python side injects the already
// computed analysis bundle onto `window` BEFORE this bundle runs. In that mode
// the UI renders straight from the embedded data — no FastAPI server, no
// network — so the modern dashboard works on a plain `pip install openstatz`.
//
// When these globals are absent the app behaves exactly as before (live
// `openstatz serve` mode, fetching from /api).

import type { AnalysisResponse, HealthResponse } from "../api/types";

declare global {
  interface Window {
    __OPENSTATZ_DATA__?: AnalysisResponse;
    __OPENSTATZ_HEALTH__?: HealthResponse;
  }
}

export const EMBEDDED_DATA: AnalysisResponse | undefined =
  typeof window !== "undefined" ? window.__OPENSTATZ_DATA__ : undefined;

export const EMBEDDED_HEALTH: HealthResponse | undefined =
  typeof window !== "undefined" ? window.__OPENSTATZ_HEALTH__ : undefined;

/** True when the UI is running as an embedded, server-less static report. */
export const IS_STATIC_REPORT = EMBEDDED_DATA !== undefined;
