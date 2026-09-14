import { useCallback, useState } from "react";
import DetectionTable from "../components/DetectionTable.jsx";
import { exportCsvUrl, fetchVehicles } from "../services/api.js";
import usePoll from "../hooks/usePoll.js";

export default function Detections() {
  const [page, setPage] = useState(0);
  const [data, setData] = useState({ items: [], total: 0 });
  const limit = 15;

  const load = useCallback(async () => {
    setData(await fetchVehicles({ skip: page * limit, limit }));
  }, [page]);

  usePoll(load, 4000);

  const maxPage = Math.max(0, Math.ceil((data.total || 0) / limit) - 1);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Recent detections</h2>
          <p className="mt-1 text-sm text-slate-400">{data.total} accepted records in SQLite.</p>
        </div>
        <a
          href={exportCsvUrl()}
          className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-cyan-300"
        >
          Export CSV
        </a>
      </div>
      <DetectionTable items={data.items} />
      <div className="flex items-center justify-end gap-3 text-sm">
        <button
          type="button"
          disabled={page <= 0}
          onClick={() => setPage((value) => Math.max(0, value - 1))}
          className="rounded-lg border border-line px-3 py-1 disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-slate-400">
          Page {page + 1} of {maxPage + 1}
        </span>
        <button
          type="button"
          disabled={page >= maxPage}
          onClick={() => setPage((value) => value + 1)}
          className="rounded-lg border border-line px-3 py-1 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
