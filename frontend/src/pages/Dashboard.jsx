import { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import StatCard from "../components/StatCard.jsx";
import DetectionTable from "../components/DetectionTable.jsx";
import PlateBadge from "../components/PlateBadge.jsx";
import { fetchStats, imageSrc } from "../services/api.js";
import usePoll from "../hooks/usePoll.js";

function pct(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const load = useCallback(async () => {
    setStats(await fetchStats());
  }, []);
  usePoll(load, 4000);

  const typeData = useMemo(
    () =>
      Object.entries(stats?.vehicle_type_counts || {}).map(([name, value]) => ({
        name,
        value,
      })),
    [stats]
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Detection overview</h2>
        <p className="mt-1 text-sm text-slate-400">
          Live counts from the local SQLite store. Images are saved only when a detection is accepted.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total detections" value={stats?.total_detections ?? "—"} hint="Accepted records" />
        <StatCard label="Today" value={stats?.today_detections ?? "—"} hint="UTC calendar day" accent="amber" />
        <StatCard label="Unique plates" value={stats?.unique_plates ?? "—"} hint="Normalized plate text" />
        <StatCard label="Avg OCR confidence" value={stats ? pct(stats.average_ocr_confidence) : "—"} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <section className="rounded-2xl border border-line bg-ink-800/80 p-5 shadow-panel">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-medium uppercase tracking-[0.16em] text-slate-400">Today by hour</h3>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.hourly_today || []}>
                <XAxis dataKey="hour" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" allowDecimals={false} fontSize={11} />
                <Tooltip
                  contentStyle={{ background: "#121a2b", border: "1px solid #24324d", borderRadius: 12 }}
                />
                <Bar dataKey="count" fill="#22d3ee" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-2xl border border-line bg-ink-800/80 p-5 shadow-panel">
          <h3 className="mb-4 text-sm font-medium uppercase tracking-[0.16em] text-slate-400">Vehicle types</h3>
          <div className="space-y-3">
            {typeData.length === 0 ? (
              <p className="text-sm text-slate-500">No vehicle-type counts yet.</p>
            ) : (
              typeData.map((item) => (
                <div key={item.name} className="flex items-center justify-between rounded-xl bg-ink-950/70 px-3 py-2">
                  <span className="capitalize text-slate-200">{item.name}</span>
                  <span className="font-mono text-cyan-300">{item.value}</span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-medium text-white">Recent detections</h3>
          <Link to="/detections" className="text-sm text-cyan-300 hover:text-cyan-200">
            View all
          </Link>
        </div>
        <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {(stats?.recent || []).slice(0, 4).map((row) => (
            <Link
              key={row.id}
              to={`/detections/${row.id}`}
              className="overflow-hidden rounded-2xl border border-line bg-ink-800/80 shadow-panel"
            >
              <div className="h-28 bg-ink-950">
                {row.vehicle_image_url || row.vehicle_image_path ? (
                  <img
                    src={imageSrc(row.vehicle_image_url || row.vehicle_image_path)}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-slate-500">No image</div>
                )}
              </div>
              <div className="space-y-2 p-3">
                <PlateBadge plate={row.plate_number} compact />
                <p className="text-xs capitalize text-slate-400">
                  {row.vehicle_type} · {pct(row.ocr_confidence)}
                </p>
              </div>
            </Link>
          ))}
        </div>
        <DetectionTable items={stats?.recent || []} />
      </section>
    </div>
  );
}
