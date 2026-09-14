import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  timeout: 20000,
});

export async function fetchHealth() {
  const { data } = await api.get("/health");
  return data;
}

export async function fetchStats() {
  const { data } = await api.get("/dashboard/stats");
  return data;
}

export async function fetchVehicles(params = {}) {
  const { data } = await api.get("/vehicles", { params });
  return data;
}

export async function fetchVehicle(id) {
  const { data } = await api.get(`/vehicles/${id}`);
  return data;
}

export async function searchDetections(params = {}) {
  const { data } = await api.get("/search", { params });
  return data;
}

export async function fetchLiveStatus() {
  const { data } = await api.get("/stream/status");
  return data;
}

export async function startLiveCamera(source) {
  const { data } = await api.post("/stream/start", source ? { source } : {});
  return data;
}

export async function stopLiveCamera() {
  const { data } = await api.post("/stream/stop");
  return data;
}

export function liveSnapshotUrl(nonce) {
  return `/api/stream/snapshot?t=${nonce}`;
}

export function liveMjpegUrl(nonce) {
  return `/api/stream/mjpeg?t=${nonce}`;
}

export function exportCsvUrl(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) search.set(key, value);
  });
  const query = search.toString();
  return `/api/export/csv${query ? `?${query}` : ""}`;
}

export function imageSrc(path) {
  if (!path) return null;
  if (path.startsWith("http") || path.startsWith("/")) return path;
  return `/${path}`;
}
