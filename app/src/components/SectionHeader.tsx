// Numbered serif section header — "01  Overview". The number is a real index
// into an ordered tearsheet, so the numbering encodes the reading sequence.
export function SectionHeader({
  n,
  title,
  subtitle,
}: {
  n: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="flex items-baseline gap-4 border-b border-hair pb-3 mb-5">
      <span className="nums text-muted text-sm pt-1">{n}</span>
      <h2 className="serif text-[1.7rem] leading-none text-ink">{title}</h2>
      {subtitle && (
        <span className="ml-auto text-xs text-muted hidden sm:block">{subtitle}</span>
      )}
    </div>
  );
}
