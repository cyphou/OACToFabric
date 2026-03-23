import { Link } from "react-router-dom";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Ban,
} from "lucide-react";
import { useMigrations } from "../hooks/useMigrations";
import type { Migration } from "../api/types";

const STATUS_ICON: Record<string, React.ReactNode> = {
  pending: <Clock size={16} className="text-muted" />,
  running: <Loader2 size={16} className="text-info spin" />,
  completed: <CheckCircle2 size={16} className="text-success" />,
  failed: <XCircle size={16} className="text-danger" />,
  cancelled: <Ban size={16} className="text-muted" />,
};

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="progress-bar">
      <div className="progress-fill" style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  );
}

function MigrationRow({ m }: { m: Migration }) {
  return (
    <Link to={`/migrations/${m.id}`} className="migration-row">
      <div className="row-status">{STATUS_ICON[m.status] ?? STATUS_ICON.pending}</div>
      <div className="row-name">{m.name}</div>
      <div className="row-meta">
        <span className="badge">{m.source_type}</span>
        <span className="badge">{m.mode}</span>
      </div>
      <div className="row-progress">
        <ProgressBar pct={m.progress_pct} />
        <span className="progress-label">{m.progress_pct.toFixed(0)}%</span>
      </div>
      <div className="row-counts">
        {m.succeeded_items}/{m.total_items}
      </div>
      <div className="row-date">{new Date(m.created_at).toLocaleDateString()}</div>
    </Link>
  );
}

export default function MigrationList() {
  const { data: migrations, isLoading, error } = useMigrations();

  if (isLoading) return <div className="page-loading"><Loader2 className="spin" size={32} /> Loading…</div>;
  if (error) return <div className="page-error">Failed to load migrations: {(error as Error).message}</div>;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Migrations</h1>
        <Link to="/new" className="btn btn-primary">+ New Migration</Link>
      </header>

      {!migrations?.length ? (
        <div className="empty-state">
          <p>No migrations yet.</p>
          <Link to="/new" className="btn btn-primary">Create your first migration</Link>
        </div>
      ) : (
        <div className="migration-list">
          <div className="list-header">
            <span />
            <span>Name</span>
            <span>Type</span>
            <span>Progress</span>
            <span>Items</span>
            <span>Created</span>
          </div>
          {migrations.map((m) => (
            <MigrationRow key={m.id} m={m} />
          ))}
        </div>
      )}
    </div>
  );
}
