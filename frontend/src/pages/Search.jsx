import { useState } from "react";
import DetectionTable from "../components/DetectionTable.jsx";
import { exportCsvUrl, searchDetections } from "../services/api.js";

const emptyFilters = {
  plate_number: "",
  vehicle_type: "",
  date: "",
  date_from: "",
  date_to: "",
};

export default function Search() {
  const [filters, setFilters] = useState(emptyFilters);
  const [results, setResults] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
      setResults(await searchDetections(params));
    } catch (err) {
      setError(err.message || "Search failed");
    } finally {
      setLoading(false);
    }
  }

  const exportHref = exportCsvUrl(filters);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Search records</h2>
        <p className="mt-1 text-sm text-slate-400">
          Filter by plate text, vehicle type, a single date, or a date/time range.
        </p>
      </div>

      <form onSubmit={onSubmit} className="grid gap-4 rounded-2xl border border-line bg-ink-800/80 p-5 shadow-panel md:grid-cols-2 xl:grid-cols-3">
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">Plate number</span>
          <input
            value={filters.plate_number}
            onChange={(event) => update("plate_number", event.target.value.toUpperCase())}
            className="w-full rounded-xl border border-line bg-ink-950 px-3 py-2 font-mono outline-none focus:border-cyan-400"
            placeholder="MH12AB1234"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">Vehicle type</span>
          <select
            value={filters.vehicle_type}
            onChange={(event) => update("vehicle_type", event.target.value)}
            className="w-full rounded-xl border border-line bg-ink-950 px-3 py-2 outline-none focus:border-cyan-400"
          >
            <option value="">Any</option>
            <option value="car">Car</option>
            <option value="motorcycle">Motorcycle</option>
            <option value="bus">Bus</option>
            <option value="truck">Truck</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">Date</span>
          <input
            type="date"
            value={filters.date}
            onChange={(event) => update("date", event.target.value)}
            className="w-full rounded-xl border border-line bg-ink-950 px-3 py-2 outline-none focus:border-cyan-400"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">From</span>
          <input
            type="datetime-local"
            value={filters.date_from}
            onChange={(event) => update("date_from", event.target.value)}
            className="w-full rounded-xl border border-line bg-ink-950 px-3 py-2 outline-none focus:border-cyan-400"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">To</span>
          <input
            type="datetime-local"
            value={filters.date_to}
            onChange={(event) => update("date_to", event.target.value)}
            className="w-full rounded-xl border border-line bg-ink-950 px-3 py-2 outline-none focus:border-cyan-400"
          />
        </label>
        <div className="flex items-end gap-3">
          <button
            type="submit"
            className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-cyan-300"
          >
            {loading ? "Searching…" : "Search"}
          </button>
          <a href={exportHref} className="rounded-xl border border-cyan-400/40 px-4 py-2 text-sm text-cyan-200">
            Export CSV
          </a>
        </div>
      </form>

      {error ? <p className="text-sm text-amber-300">{error}</p> : null}
      <p className="text-sm text-slate-400">{results.total} matching records</p>
      <DetectionTable items={results.items} empty="No records match those filters." />
    </div>
  );
}
