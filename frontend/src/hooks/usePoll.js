import { useEffect, useState } from "react";

export default function usePoll(callback, intervalMs, enabled = true) {
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;

    async function tick() {
      try {
        await callback();
        if (!cancelled) setError(null);
      } catch (err) {
        if (!cancelled) setError(err);
      }
    }

    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [callback, intervalMs, enabled]);

  return error;
}
