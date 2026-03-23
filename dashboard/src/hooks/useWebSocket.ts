/* WebSocket hook for real-time migration events. */

import { useEffect, useRef, useState, useCallback } from "react";
import type { WsEvent } from "../api/types";

const WS_BASE = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;

export function useMigrationWs(migrationId: string | undefined) {
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const clear = useCallback(() => setEvents([]), []);

  useEffect(() => {
    if (!migrationId) return;

    const url = `${WS_BASE}/ws/migrations/${encodeURIComponent(migrationId)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as WsEvent;
        if (data.type !== "ping") {
          setEvents((prev) => [...prev, data]);
        }
      } catch {
        /* ignore non-JSON frames */
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
      setConnected(false);
    };
  }, [migrationId]);

  return { events, connected, clear };
}
