/* SSE hook for log streaming from a migration. */

import { useEffect, useState, useCallback } from "react";
import type { LogEntry } from "../api/types";

export function useLogStream(migrationId: string | undefined) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [streaming, setStreaming] = useState(false);

  const clear = useCallback(() => setLogs([]), []);

  useEffect(() => {
    if (!migrationId) return;

    const url = `/api/migrations/${encodeURIComponent(migrationId)}/logs`;
    const es = new EventSource(url);
    setStreaming(true);

    es.onmessage = (ev) => {
      try {
        const entry = JSON.parse(ev.data) as LogEntry;
        setLogs((prev) => [...prev, entry]);
      } catch {
        /* ignore */
      }
    };

    es.onerror = () => {
      setStreaming(false);
      es.close();
    };

    return () => {
      es.close();
      setStreaming(false);
    };
  }, [migrationId]);

  return { logs, streaming, clear };
}
