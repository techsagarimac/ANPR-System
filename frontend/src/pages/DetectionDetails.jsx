import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import PlateBadge from "../components/PlateBadge.jsx";
import { fetchVehicle, imageSrc } from "../services/api.js";

function Row({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line py-3">
      <dt className="text-sm text-slate-400">{label}</dt>
      <dd className="text-right text-sm text-slate-100">{value ?? "—"}</dd>
    </div>
  );
}

export default function DetectionDetails() {
  const { id } = useParams();
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchVehicle(id)
      .then((data) => {
        if (!cancelled) setRecord(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.status === 404 ? "Detection not found" : err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <div className="rounded-2xl border border-amber-400/30 bg-ink-800 p-8 text-amber-200">
        {error}. <Link to="/detections">Back to detections</Link>
      </div>
    );
  }

  if (!record) {
    return <p className="text-slate-400">Loading detection…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-cyan-400">Detection #{record.id}</p>
          <h2 className="mt-1 text-2xl font-semibold text-white">Detection details</h2>
        </div>
        <PlateBadge plate={record.plate_number} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <figure className="overflow-hidden rounded-2xl border border-line bg-ink-800 shadow-panel">
          <img
            src={imageSrc(record.vehicle_image_url || record.vehicle_image_path)}
            alt="Vehicle crop"
            className="h-72 w-full bg-ink-950 object-contain"
          />
          <figcaption className="px-4 py-3 text-sm text-slate-400">Vehicle crop</figcaption>
        </figure>
        <figure className="overflow-hidden rounded-2xl border border-line bg-ink-800 shadow-panel">
          <img
            src={imageSrc(record.plate_image_url || record.plate_image_path)}
            alt="Plate crop"
            className="h-72 w-full bg-ink-950 object-contain"
          />
          <figcaption className="px-4 py-3 text-sm text-slate-400">Plate crop</figcaption>
        </figure>
      </div>

      <dl className="rounded-2xl border border-line bg-ink-800/80 px-5 shadow-panel">
        <Row label="Vehicle type" value={<span className="capitalize">{record.vehicle_type}</span>} />
        <Row label="Vehicle confidence" value={`${Math.round(record.vehicle_confidence * 100)}%`} />
        <Row label="Plate confidence" value={`${Math.round(record.plate_confidence * 100)}%`} />
        <Row label="OCR confidence" value={`${Math.round(record.ocr_confidence * 100)}%`} />
        <Row label="Raw OCR" value={<span className="font-mono">{record.ocr_raw || "—"}</span>} />
        <Row label="Normalized plate" value={<span className="font-mono">{record.plate_number}</span>} />
        <Row label="Valid format signal" value={record.is_valid_format ? "Yes" : "No"} />
        <Row label="Timestamp" value={new Date(record.timestamp).toLocaleString()} />
        <Row label="Camera" value={record.camera_id} />
        <Row label="Direction" value={record.direction} />
        <Row label="Track ID" value={record.track_id} />
      </dl>
    </div>
  );
}
