import { useCallback, useEffect, useRef, useState } from "react";
import PlateBadge from "../components/PlateBadge.jsx";
import { fetchLiveStatus, fetchVehicles, startLiveCamera, stopLiveCamera } from "../services/api.js";
import usePoll from "../hooks/usePoll.js";

export default function LiveCamera() {
  const [status, setStatus] = useState(null);
  const [recent, setRecent] = useState([]);
  const [frameUrl, setFrameUrl] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const objectUrl = useRef(null);

  const load = useCallback(async () => {
    const [live, vehicles] = await Promise.all([fetchLiveStatus(), fetchVehicles({ limit: 8 })]);
    setStatus(live);
    setRecent(vehicles.items || []);
  }, []);

  usePoll(load, 1000);

  useEffect(() => {
    let cancelled = false;
    startLiveCamera()
      .then((live) => {
        if (!cancelled) {
          setStatus(live);
          setMessage(live.camera_connected ? "Live camera started." : live.last_error || "Camera is starting…");
        }
      })
      .catch((err) => {
        if (!cancelled) setMessage(err.response?.data?.detail || err.message || "Could not start camera");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let stopped = false;

    async function pullFrame() {
      try {
        const response = await fetch(`/api/stream/snapshot?t=${Date.now()}`, { cache: "no-store" });
        if (!response.ok) return;
        const blob = await response.blob();
        if (stopped) return;
        const next = URL.createObjectURL(blob);
        if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
        objectUrl.current = next;
        setFrameUrl(next);
      } catch {
        /* keep last frame */
      }
    }

    pullFrame();
    const id = setInterval(pullFrame, 80);
    return () => {
      stopped = true;
      clearInterval(id);
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    };
  }, []);

  async function onStart() {
    setBusy(true);
    setMessage("");
    try {
      const live = await startLiveCamera();
      setStatus(live);
      setMessage(live.camera_connected ? "Live camera started." : live.last_error || "Camera engine started.");
    } catch (err) {
      setMessage(err.response?.data?.detail || err.message || "Could not start camera");
    } finally {
      setBusy(false);
    }
  }

  async function onStop() {
    setBusy(true);
    try {
      setStatus(await stopLiveCamera());
      setMessage("Camera stopped.");
    } catch (err) {
      setMessage(err.message || "Could not stop camera");
    } finally {
      setBusy(false);
    }
  }

  const online = Boolean(status?.camera_connected);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Live camera</h2>
          <p className="mt-1 text-sm text-slate-400">
            Point the webcam at a vehicle or number plate. Recognized plates are stored in SQLite with vehicle and plate crops.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full border border-line px-3 py-1 font-mono text-xs text-slate-400">
            {online ? "CAMERA ONLINE" : "CAMERA WAITING"}
          </span>
          <span className="rounded-full border border-line px-3 py-1 font-mono text-xs text-slate-400">
            FPS {status?.fps ?? 0}
          </span>
          <span className="rounded-full border border-line px-3 py-1 font-mono text-xs text-slate-400">
            FRAME {status?.frame_index ?? 0}
          </span>
          <button
            type="button"
            onClick={onStart}
            disabled={busy}
            className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-cyan-300 disabled:opacity-50"
          >
            {busy ? "Starting…" : "Start camera"}
          </button>
          <button
            type="button"
            onClick={onStop}
            disabled={busy}
            className="rounded-xl border border-line px-4 py-2 text-sm text-slate-200 disabled:opacity-50"
          >
            Stop
          </button>
        </div>
      </div>

      {message ? (
        <p className={`text-sm ${online ? "text-emerald-300" : "text-amber-300"}`}>{message}</p>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(280px,0.8fr)]">
        <section className="overflow-hidden rounded-2xl border border-line bg-ink-900 shadow-panel">
          {frameUrl ? (
            <img src={frameUrl} alt="Live annotated camera feed" className="aspect-video w-full bg-ink-950 object-contain" />
          ) : (
            <div className="flex aspect-video items-center justify-center bg-ink-950 text-sm text-slate-500">
              Connecting to camera…
            </div>
          )}
        </section>

        <section className="space-y-4">
          <div className="rounded-2xl border border-line bg-ink-800/80 p-4 shadow-panel">
            <h3 className="mb-3 text-sm font-medium uppercase tracking-[0.16em] text-slate-400">
              Current overlays
            </h3>
            <div className="space-y-3">
              {(status?.overlays || []).length === 0 ? (
                <p className="text-sm text-slate-500">
                  {status?.models_loading
                    ? "Camera is live. Detection models are still loading…"
                    : "No vehicles in the current processed frame."}
                </p>
              ) : (
                status.overlays.map((overlay, index) => (
                  <div key={`${overlay.track_id}-${index}`} className="rounded-xl bg-ink-950/80 p-3">
                    <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
                      <span>Track {overlay.track_id ?? "—"}</span>
                      <span className="capitalize">
                        {overlay.vehicle_type} {Math.round(overlay.vehicle_confidence * 100)}%
                      </span>
                    </div>
                    <PlateBadge plate={overlay.plate_number} />
                    <p className="mt-2 font-mono text-xs text-cyan-200">
                      OCR {overlay.ocr_confidence != null ? `${Math.round(overlay.ocr_confidence * 100)}%` : "—"}
                      {overlay.plate_confidence != null
                        ? ` · plate ${Math.round(overlay.plate_confidence * 100)}%`
                        : ""}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-ink-800/80 p-4 shadow-panel">
            <h3 className="mb-3 text-sm font-medium uppercase tracking-[0.16em] text-slate-400">
              Latest accepted plates
            </h3>
            <div className="space-y-2">
              {recent.map((row) => (
                <div key={row.id} className="flex items-center justify-between gap-3 rounded-xl bg-ink-950/70 px-3 py-2">
                  <PlateBadge plate={row.plate_number} compact />
                  <span className="text-xs capitalize text-slate-400">{row.vehicle_type}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
