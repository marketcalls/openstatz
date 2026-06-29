import type { AnalyzeRequest } from "../api/types";

// Parse a returns CSV into an AnalyzeRequest. Accepts:
//   - a date column + one value column (strategy), optional second value column
//     (benchmark)
//   - values as decimals (0.012), percents ("1.2%"), or prices (auto-converted
//     to returns server-side by _prepare_returns)
//   - comma / semicolon / tab delimited, with or without a header row

export interface CsvResult {
  request: AnalyzeRequest;
  rows: number;
  strategyName: string;
  benchmarkName: string | null;
}

function isNumeric(s: string): boolean {
  const t = s.trim().replace(/%$/, "").replace(/,/g, "");
  return t !== "" && Number.isFinite(Number(t));
}

function parseValue(s: string): number | null {
  const raw = s.trim();
  const t = raw.replace(/%$/, "").replace(/,/g, "");
  const n = Number(t);
  if (!Number.isFinite(n)) return null;
  return raw.endsWith("%") ? n / 100 : n;
}

export function parseReturnsCsv(text: string, filename = "upload.csv"): CsvResult {
  const lines = text.split(/\r?\n/).filter((l) => l.trim() !== "");
  if (lines.length === 0) throw new Error("The file is empty.");

  const first = lines[0];
  const delim = first.includes("\t") ? "\t" : first.includes(";") ? ";" : ",";
  const rows = lines.map((l) => l.split(delim).map((c) => c.trim()));

  // Header present if the 2nd cell of the first row isn't a number.
  let header: string[] | null = null;
  let start = 0;
  if (rows[0].length >= 2 && !isNumeric(rows[0][1])) {
    header = rows[0];
    start = 1;
  }
  if (start >= rows.length) throw new Error("No data rows found.");

  const hasBench = rows[start].length >= 3 && isNumeric(rows[start][2]);
  const strategyName = (header?.[1] || filename.replace(/\.csv$/i, "") || "Strategy").trim();
  const benchmarkName = hasBench ? (header?.[2] || "Benchmark").trim() : null;

  const dates: string[] = [];
  const strategy: number[] = [];
  const benchmark: number[] = [];

  for (let i = start; i < rows.length; i++) {
    const r = rows[i];
    if (r.length < 2) continue;
    const date = r[0].trim();
    const sv = parseValue(r[1]);
    if (date === "" || sv === null) continue;
    dates.push(date);
    strategy.push(sv);
    if (hasBench) {
      const bv = parseValue(r[2]);
      benchmark.push(bv ?? 0);
    }
  }

  if (dates.length < 2) {
    throw new Error("Could not read at least two (date, value) rows. Expected: date, return[, benchmark].");
  }

  const request: AnalyzeRequest = {
    dates,
    returns: { [strategyName]: strategy },
    benchmark: hasBench ? benchmark : null,
    benchmark_name: benchmarkName ?? "Benchmark",
    rf: 0,
    compounded: true,
    periods_per_year: 252,
    rolling_window: 126,
  };

  return { request, rows: dates.length, strategyName, benchmarkName };
}
