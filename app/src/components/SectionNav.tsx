import { useEffect, useState } from "react";

export const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "performance", label: "Performance" },
  { id: "risk", label: "Risk" },
  { id: "monthly", label: "Monthly" },
  { id: "distribution", label: "Distribution" },
  { id: "metrics", label: "Metrics" },
];

// Top-bar section links with scroll-spy highlighting (active = ink, rest = tan).
export function SectionNav() {
  const [active, setActive] = useState(SECTIONS[0].id);

  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(e.target.id);
        }
      },
      { rootMargin: "-45% 0px -50% 0px" },
    );
    for (const s of SECTIONS) {
      const el = document.getElementById(s.id);
      if (el) obs.observe(el);
    }
    return () => obs.disconnect();
  }, []);

  return (
    <nav className="hidden lg:flex items-center gap-7">
      {SECTIONS.map((s) => (
        <a
          key={s.id}
          href={`#${s.id}`}
          className={`text-[0.7rem] font-semibold uppercase tracking-[0.13em] transition-colors ${
            active === s.id ? "text-ink" : "text-muted hover:text-ink"
          }`}
        >
          {s.label}
        </a>
      ))}
    </nav>
  );
}
