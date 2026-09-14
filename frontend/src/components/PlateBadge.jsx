export default function PlateBadge({ plate, compact = false }) {
  if (!plate) {
    return (
      <span className="rounded border border-dashed border-line px-2 py-1 font-mono text-xs text-slate-500">
        NO PLATE
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center justify-center rounded-md border border-amber-300 bg-amber-100 font-mono font-semibold tracking-[0.18em] text-slate-900 shadow-sm ${
        compact ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm"
      }`}
    >
      {plate}
    </span>
  );
}
