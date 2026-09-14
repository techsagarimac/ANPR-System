import { NavLink, Outlet } from "react-router-dom";
import { useCallback, useState } from "react";
import { Activity, Camera, LayoutDashboard, Search, BarChart3, CarFront } from "lucide-react";
import { fetchHealth } from "../services/api.js";
import usePoll from "../hooks/usePoll.js";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/live", label: "Live Camera", icon: Camera },
  { to: "/detections", label: "Recent Detections", icon: CarFront },
  { to: "/search", label: "Search", icon: Search },
  { to: "/statistics", label: "Statistics", icon: BarChart3 },
];

export default function Layout() {
  const [health, setHealth] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const loadHealth = useCallback(async () => {
    setHealth(await fetchHealth());
  }, []);

  usePoll(loadHealth, 5000);

  const statusColor =
    health?.status === "ok" ? "bg-emerald-400" : health?.status === "degraded" ? "bg-amber-400" : "bg-slate-500";

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="border-b border-line bg-ink-900/95 lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between px-5 py-5">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-cyan-400">ANPR</p>
            <h1 className="text-lg font-semibold text-white">Operations Console</h1>
          </div>
          <button
            type="button"
            className="rounded-lg border border-line px-3 py-1 text-sm lg:hidden"
            onClick={() => setMenuOpen((value) => !value)}
          >
            Menu
          </button>
        </div>
        <nav className={`${menuOpen ? "block" : "hidden"} px-3 pb-5 lg:block`}>
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `mb-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${
                  isActive ? "bg-cyan-400/10 text-cyan-200" : "text-slate-300 hover:bg-ink-700"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden border-t border-line px-5 py-4 text-xs text-slate-400 lg:block">
          <div className="mb-2 flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${statusColor}`} />
            <span className="uppercase tracking-[0.16em]">System</span>
          </div>
          <p>Camera: {health?.camera || "unknown"}</p>
          <p>Vehicle model: {health?.vehicle_model || "unloaded"}</p>
          <p>Plate model: {health?.plate_model || "unloaded"}</p>
          <p>OCR: {health?.ocr || "unloaded"}</p>
        </div>
      </aside>
      <div className="min-h-screen">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-ink-950/80 px-4 py-4 backdrop-blur md:px-8">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Activity size={16} className="text-cyan-400" />
            Authorized educational vehicle monitoring
          </div>
          <div className="font-mono text-xs text-slate-500">No owner lookup · No face recognition</div>
        </header>
        <main className="px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
