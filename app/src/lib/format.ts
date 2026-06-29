// The single number-formatting layer (architecture section 8). Every numeric
// cell and axis routes through here so %, decimals, separators, and negative
// styling are consistent across the whole UI.

const NBSP = " ";

export function fmtNumber(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** value is a fraction (0.1234 -> "12.34%"). */
export function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(v * 100).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}%`;
}

export function fmtSignedPct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const s = fmtPct(v, digits);
  return v > 0 ? `+${s}` : s;
}

export function fmtDate(epochSeconds: number): string {
  const d = new Date(epochSeconds * 1000);
  return d.toISOString().slice(0, 10);
}

export function fmtCompact(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString("en-US", { notation: "compact", maximumFractionDigits: 1 });
}

/** P&L color class — green/red reserved strictly for gains/losses. */
export function pnlClass(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v) || v === 0) return "text-ink";
  return v > 0 ? "text-pnl-pos" : "text-pnl-neg";
}

/** Right-pad a label/value gap with a non-breaking space for alignment. */
export function pad(s: string): string {
  return s.replace(/ /g, NBSP);
}
