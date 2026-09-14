import { useCallback, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchStats } from "../services/api.js";
import usePoll from "../hooks/usePoll.js";
import StatCard from "../components/StatCard.jsx";

export default function Statistics() {
  const [stats, setStats] = useState(null);
  const load = useCallback(async () => setStats(await fetchStats()), []);
  usePoll(load, 5000);

  const typeData = useMemo(
    () => Object.entries(stats?.vehicle_type_counts || {}).map(([name, value]) => ({ name, value })),
    [stats]
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Statistics</h2>
        <p className="mt-1 text-sm text-slate-400">
          Aggregates from stored detections only. This screen does not identify vehicle owners.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Total" value={stats?.total_detections ?? "—"} />
        <StatCard label="Today" value={stats?.today_detections ?? "—"} accent="amber" />
        <StatCard label="Unique plates" value={stats?.unique_plates ?? "—"} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-line bg-ink-800/80 p-5 shadow-panel">
          <h3 className="mb-4 text-sm font-medium uppercase tracking-[0.16em] text-slate-400">Hourly today</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.hourly_today || []}>
                <CartesianGrid stroke="#24324d" vertical={false} />
                <XAxis dataKey="hour" stroke="#64748b" />
                <YAxis allowDecimals={false} stroke="#64748b" />
                <Tooltip contentStyle={{ background: "#121a2b", border: "1px solid #24324d" }} />
                <Bar dataKey="count" fill="#22d3ee" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="rounded-2xl border border-line bg-ink-800/80 p-5 shadow-panel">
          <h3 className="mb-4 text-sm font-medium uppercase tracking-[0.16em] text-slate-400">Vehicle type mix</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={typeData} layout="vertical">
                <CartesianGrid stroke="#24324d" horizontal={false} />
                <XAxis type="number" allowDecimals={false} stroke="#64748b" />
                <YAxis type="category" dataKey="name" stroke="#64748b" width={90} />
                <Tooltip contentStyle={{ background: "#121a2b", border: "1px solid #24324d" }} />
                <Bar dataKey="value" fill="#fbbf24" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </div>
  );
}
