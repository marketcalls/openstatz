// Wire types — mirror openstatz/app/schemas.py (Pydantic v2).
// For an authoritative regeneration: `npm run gen:types` (openapi-typescript).

export interface SeriesPoint {
  time: number; // epoch seconds
  value: number | null;
}

/** chart name -> column name -> points */
export type SeriesBundle = Record<string, Record<string, SeriesPoint[]>>;

export interface MetricRow {
  label: string;
  values: Record<string, number | null>;
  display: Record<string, string>;
}

export interface MetricsTable {
  columns: string[];
  rows: MetricRow[];
}

export interface HeatmapCell {
  year: string;
  month: string;
  value: number | null;
}

export interface MonthlyHeatmap {
  years: string[];
  months: string[];
  cells: HeatmapCell[];
}

export interface EoyRow {
  year: string;
  strategy: number | null;
  benchmark?: number | null;
}

export interface DrawdownRow {
  start: string;
  valley: string;
  end: string;
  days: number | null;
  max_drawdown: number | null;
  drawdown_pct: number | null;
}

export interface WeeklyCell {
  week: number;
  value: number | null;
  label: string;
}

export interface WeeklyHeatmap {
  years: string[];
  by_year: Record<string, WeeklyCell[]>;
}

export interface Tables {
  monthly_heatmap: MonthlyHeatmap;
  weekly_heatmap: WeeklyHeatmap;
  eoy: { rows: EoyRow[] };
  worst_drawdowns: { rows: DrawdownRow[] };
}

export interface Meta {
  columns: string[];
  start: number;
  end: number;
  n_periods: number;
  rf: number;
  compounded: boolean;
  periods_per_year: number;
  has_benchmark: boolean;
}

export interface AnalysisResponse {
  meta: Meta;
  metrics: MetricsTable;
  series: SeriesBundle;
  tables: Tables;
}

export interface AnalyzeRequest {
  dates: string[];
  returns: Record<string, number[]>;
  benchmark?: number[] | null;
  benchmark_name?: string;
  rf?: number;
  compounded?: boolean;
  periods_per_year?: number;
  rolling_window?: number;
}

export interface SymbolRequest {
  symbol: string;
  benchmark_symbol?: string | null;
  provider?: string;
  period?: string;
  rf?: number;
  compounded?: boolean;
  periods_per_year?: number;
  rolling_window?: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  numba: boolean;
}
