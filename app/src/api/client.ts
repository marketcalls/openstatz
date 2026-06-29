import type {
  AnalysisResponse,
  AnalyzeRequest,
  HealthResponse,
  SymbolRequest,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function analyze(req: AnalyzeRequest): Promise<AnalysisResponse> {
  return post<AnalysisResponse>("/api/analyze", req);
}

export function analyzeSymbol(req: SymbolRequest): Promise<AnalysisResponse> {
  return post<AnalysisResponse>("/api/analyze/symbol", req);
}

export async function health(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/api/health`);
  if (!res.ok) throw new Error(`health ${res.status}`);
  return res.json() as Promise<HealthResponse>;
}
