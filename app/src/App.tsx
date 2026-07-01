import { useState } from "react";
import { Dashboard } from "./components/Dashboard";
import { Compare } from "./components/Compare";
import { SectionNav } from "./components/SectionNav";
import { ThemeToggle } from "./components/ThemeToggle";
import { IS_STATIC_REPORT } from "./lib/embedded";

type View = "single" | "compare";

function Mark() {
  return (
    <a
      href="https://openalgo.in"
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-3 group"
      title="openalgo.in"
    >
      <span className="h-9 w-9 grid place-items-center rounded-full border border-hair-strong group-hover:border-ink transition-colors">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 17l5-6 4 3 5-8 4 5" />
        </svg>
      </span>
      <div className="leading-none">
        <div className="serif text-lg text-ink tracking-tight">OpenStatz</div>
        <div className="eyebrow mt-0.5">openalgo.in</div>
      </div>
    </a>
  );
}

function ViewToggle({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  const btn = (v: View) =>
    `text-xs font-semibold uppercase tracking-[0.1em] px-3 py-1.5 rounded-md transition-colors ${
      view === v ? "bg-accent text-accent-ink" : "text-muted hover:text-ink"
    }`;
  return (
    <div className="flex items-center gap-1 rounded-lg border border-hair p-1">
      <button className={btn("single")} onClick={() => onChange("single")}>Tearsheet</button>
      <button className={btn("compare")} onClick={() => onChange("compare")}>Compare</button>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState<View>("single");
  // A static offline report holds one strategy, so Compare (needs a live server)
  // is only offered in server mode.
  const showCompare = !IS_STATIC_REPORT;
  const active: View = showCompare ? view : "single";

  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="no-print sticky top-0 z-20 backdrop-blur-md bg-bg/85 border-b border-hair">
        <div className="max-w-[1240px] mx-auto px-5 h-16 flex items-center justify-between gap-4">
          <Mark />
          <div className="flex items-center gap-5">
            {active === "single" && <SectionNav />}
            {showCompare && <ViewToggle view={active} onChange={setView} />}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.print()}
              className="text-xs font-semibold uppercase tracking-[0.12em] px-3.5 py-2 rounded-md border border-hair text-muted hover:text-ink hover:border-hair-strong transition-colors"
            >
              Export PDF
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="max-w-[1240px] mx-auto px-5 py-7">
        {active === "compare" ? <Compare /> : <Dashboard />}
      </main>
    </div>
  );
}
