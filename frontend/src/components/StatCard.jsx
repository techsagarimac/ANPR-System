export default function StatCard({ label, value, hint, accent = "cyan" }) {
  const ring = accent === "amber" ? "shadow-[inset_0_0_0_1px_rgba(251,191,36,0.25)]" : "shadow-[inset_0_0_0_1px_rgba(34,211,238,0.18)]";
  const valueColor = accent === "amber" ? "text-amber-300" : "text-cyan-300";

  return (
    <div className={`rounded-2xl bg-ink-800/90 p-5 shadow-panel ${ring}`}>
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className={`mt-3 text-3xl font-semibold ${valueColor}`}>{value}</p>
      {hint ? <p className="mt-2 text-sm text-slate-400">{hint}</p> : null}
    </div>
  );
}
