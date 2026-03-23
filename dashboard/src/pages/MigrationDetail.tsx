import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Package,
  Loader2,
  CheckCircle2,
  XCircle,
  Ban,
  ScrollText,
  Wifi,
  WifiOff,
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { useMigration, useCancelMigration } from "../hooks/useMigrations";
import { useLogStream } from "../hooks/useLogStream";
import { useMigrationWs } from "../hooks/useWebSocket";

const STATUS_COLORS: Record<string, string> = {
  idle: "var(--clr-muted)",
  running: "var(--clr-info)",
  completed: "var(--clr-success)",
  failed: "var(--clr-danger)",
};

const PIE_COLORS = ["var(--clr-success)", "var(--clr-danger)", "var(--clr-muted)"];

export default function MigrationDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: migration, isLoading, error } = useMigration(id!);
  const cancel = useCancelMigration();
  const { logs, streaming } = useLogStream(id);
  const { connected } = useMigrationWs(id);

  if (isLoading) return <div className="page-loading"><Loader2 className="spin" size={32} /></div>;
  if (error || !migration) return <div className="page-error">Migration not found</div>;

  const pieData = [
    { name: "Succeeded", value: migration.succeeded_items },
    { name: "Failed", value: migration.failed_items },
    { name: "Remaining", value: Math.max(0, migration.total_items - migration.succeeded_items - migration.failed_items) },
  ].filter((d) => d.value > 0);

  const canCancel = migration.status === "pending" || migration.status === "running";

  return (
    <div className="page">
      <header className="page-header">
        <Link to="/" className="btn btn-ghost"><ArrowLeft size={18} /> Back</Link>
        <h1>{migration.name}</h1>
        <div className="header-actions">
          <span className="ws-indicator" title={connected ? "WebSocket connected" : "WebSocket disconnected"}>
            {connected ? <Wifi size={16} className="text-success" /> : <WifiOff size={16} className="text-muted" />}
          </span>
          <Link to={`/migrations/${id}/inventory`} className="btn btn-secondary">
            <Package size={16} /> Inventory
          </Link>
          {canCancel && (
            <button className="btn btn-danger" onClick={() => cancel.mutate(id!)} disabled={cancel.isPending}>
              <Ban size={16} /> Cancel
            </button>
          )}
        </div>
      </header>

      {/* Status cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-label">Status</span>
          <span className={`stat-value status-${migration.status}`}>{migration.status}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Progress</span>
          <span className="stat-value">{migration.progress_pct.toFixed(1)}%</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Succeeded</span>
          <span className="stat-value text-success">{migration.succeeded_items}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Failed</span>
          <span className="stat-value text-danger">{migration.failed_items}</span>
        </div>
      </div>

      {/* Chart + Agents side-by-side */}
      <div className="detail-grid">
        {/* Pie chart */}
        <section className="card">
          <h2>Item Breakdown</h2>
          {pieData.length === 0 ? (
            <p className="text-muted">No items processed yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </section>

        {/* Agent status table */}
        <section className="card">
          <h2>Agents</h2>
          {migration.agents.length === 0 ? (
            <p className="text-muted">No agent activity yet.</p>
          ) : (
            <table className="table">
              <thead>
                <tr><th>Agent</th><th>State</th><th>Processed</th><th>Failed</th></tr>
              </thead>
              <tbody>
                {migration.agents.map((a) => (
                  <tr key={a.agent_id}>
                    <td>{a.agent_id}</td>
                    <td>
                      <span className="agent-dot" style={{ background: STATUS_COLORS[a.state] ?? STATUS_COLORS.idle }} />
                      {a.state}
                    </td>
                    <td>{a.items_processed}</td>
                    <td>{a.items_failed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      {/* Error */}
      {migration.error && (
        <section className="card card-danger">
          <h2><XCircle size={18} /> Error</h2>
          <pre className="error-pre">{migration.error}</pre>
        </section>
      )}

      {/* Log stream */}
      <section className="card">
        <h2>
          <ScrollText size={18} /> Logs
          {streaming && <Loader2 size={14} className="spin" style={{ marginLeft: 8 }} />}
        </h2>
        <div className="log-container">
          {logs.length === 0 ? (
            <p className="text-muted">No logs yet.</p>
          ) : (
            logs.map((l, i) => (
              <div key={i} className={`log-line log-${l.level.toLowerCase()}`}>
                <span className="log-ts">{new Date(l.timestamp).toLocaleTimeString()}</span>
                {l.agent_id && <span className="log-agent">[{l.agent_id}]</span>}
                <span className="log-msg">{l.message}</span>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Meta info */}
      <section className="card">
        <h2>Details</h2>
        <dl className="meta-list">
          <dt>ID</dt><dd>{migration.id}</dd>
          <dt>Mode</dt><dd>{migration.mode}</dd>
          <dt>Source</dt><dd>{migration.source_type}</dd>
          <dt>Created</dt><dd>{new Date(migration.created_at).toLocaleString()}</dd>
          {migration.started_at && <><dt>Started</dt><dd>{new Date(migration.started_at).toLocaleString()}</dd></>}
          {migration.completed_at && (
            <>
              <dt>Completed</dt>
              <dd>
                {new Date(migration.completed_at).toLocaleString()}
                {migration.status === "completed" && <CheckCircle2 size={14} className="text-success" style={{ marginLeft: 4 }} />}
              </dd>
            </>
          )}
        </dl>
      </section>
    </div>
  );
}
