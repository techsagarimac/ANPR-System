import { Link } from "react-router-dom";
import PlateBadge from "./PlateBadge.jsx";
import { imageSrc } from "../services/api.js";

function formatTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function confidence(value) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export default function DetectionTable({ items, empty = "No detections yet." }) {
  if (!items?.length) {
    return (
      <div className="rounded-2xl border border-dashed border-line bg-ink-800/50 px-6 py-16 text-center text-slate-400">
        {empty}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-ink-800/80 shadow-panel">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-ink-700/80 text-xs uppercase tracking-[0.14em] text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">Vehicle</th>
              <th className="px-4 py-3 font-medium">Plate</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Timestamp</th>
              <th className="px-4 py-3 font-medium">OCR</th>
              <th className="px-4 py-3 font-medium">Camera</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {items.map((row) => (
              <tr key={row.id} className="hover:bg-ink-700/40">
                <td className="px-4 py-3">
                  <Link to={`/detections/${row.id}`} className="flex items-center gap-3">
                    <div className="h-12 w-16 overflow-hidden rounded-lg bg-ink-950">
                      {row.vehicle_image_url || row.vehicle_image_path ? (
                        <img
                          src={imageSrc(row.vehicle_image_url || row.vehicle_image_path)}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-[10px] text-slate-500">
                          N/A
                        </div>
                      )}
                    </div>
                    <span className="text-cyan-300">#{row.id}</span>
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <PlateBadge plate={row.plate_number} compact />
                </td>
                <td className="px-4 py-3 capitalize text-slate-200">{row.vehicle_type}</td>
                <td className="px-4 py-3 text-slate-300">{formatTime(row.timestamp)}</td>
                <td className="px-4 py-3 font-mono text-cyan-200">{confidence(row.ocr_confidence)}</td>
                <td className="px-4 py-3 text-slate-400">{row.camera_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
