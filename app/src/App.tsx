import { Dashboard } from "./components/Dashboard";
import { SectionNav } from "./components/SectionNav";
import { ThemeToggle } from "./components/ThemeToggle";

function Mark() {
  return (
    <div className="flex items-center gap-3">
      <span className="h-9 w-9 grid place-items-center rounded-full border border-hair-strong">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 17l5-6 4 3 5-8 4 5" />
        </svg>
      </span>
      <div className="leading-none">
        <div className="serif text-lg text-ink tracking-tight">OpenStatz</div>
        <div className="eyebrow mt-0.5">Tearsheet</div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="no-print sticky top-0 z-20 backdrop-blur-md bg-bg/85 border-b border-hair">
        <div className="max-w-[1240px] mx-auto px-5 h-16 flex items-center justify-between gap-6">
          <Mark />
          <SectionNav />
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
        <Dashboard />
      </main>
    </div>
  );
}
