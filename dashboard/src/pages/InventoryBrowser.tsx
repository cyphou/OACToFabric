import { useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Search, Loader2, Filter } from "lucide-react";
import { useInventory } from "../hooks/useMigrations";

const COMPLEXITY_ORDER: Record<string, number> = { Low: 1, Medium: 2, High: 3, Critical: 4 };

export default function InventoryBrowser() {
  const { id } = useParams<{ id: string }>();
  const { data: inventory, isLoading, error } = useInventory(id!);

  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [complexityFilter, setComplexityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortCol, setSortCol] = useState<"name" | "asset_type" | "complexity">("name");
  const [sortAsc, setSortAsc] = useState(true);

  const assetTypes = useMemo(() => {
    if (!inventory) return [];
    return [...new Set(inventory.items.map((i) => i.asset_type))].sort();
  }, [inventory]);

  const statuses = useMemo(() => {
    if (!inventory) return [];
    return [...new Set(inventory.items.map((i) => i.migration_status))].sort();
  }, [inventory]);

  const filtered = useMemo(() => {
    if (!inventory) return [];
    let items = inventory.items;
    if (search) {
      const q = search.toLowerCase();
      items = items.filter(
        (i) => i.name.toLowerCase().includes(q) || i.source_path.toLowerCase().includes(q),
      );
    }
    if (typeFilter) items = items.filter((i) => i.asset_type === typeFilter);
    if (complexityFilter) items = items.filter((i) => i.complexity === complexityFilter);
    if (statusFilter) items = items.filter((i) => i.migration_status === statusFilter);

    items = [...items].sort((a, b) => {
      let cmp = 0;
      if (sortCol === "complexity") {
        cmp = (COMPLEXITY_ORDER[a.complexity] ?? 0) - (COMPLEXITY_ORDER[b.complexity] ?? 0);
      } else {
        cmp = a[sortCol].localeCompare(b[sortCol]);
      }
      return sortAsc ? cmp : -cmp;
    });
    return items;
  }, [inventory, search, typeFilter, complexityFilter, statusFilter, sortCol, sortAsc]);

  const toggleSort = (col: typeof sortCol) => {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(true); }
  };

  if (isLoading) return <div className="page-loading"><Loader2 className="spin" size={32} /></div>;
  if (error || !inventory) return <div className="page-error">Failed to load inventory</div>;

  return (
    <div className="page">
      <header className="page-header">
        <Link to={`/migrations/${id}`} className="btn btn-ghost"><ArrowLeft size={18} /> Back</Link>
        <h1>Inventory ({inventory.total} items)</h1>
      </header>

      {/* Filters */}
      <div className="filter-bar">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            className="input"
            placeholder="Search by name or path…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <Filter size={16} />
          <select className="input input-sm" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="">All types</option>
            {assetTypes.map((t) => <option key={t}>{t}</option>)}
          </select>
          <select className="input input-sm" value={complexityFilter} onChange={(e) => setComplexityFilter(e.target.value)}>
            <option value="">All complexity</option>
            <option>Low</option><option>Medium</option><option>High</option><option>Critical</option>
          </select>
          <select className="input input-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {statuses.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="card" style={{ overflow: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th className="sortable" onClick={() => toggleSort("name")}>
                Name {sortCol === "name" ? (sortAsc ? "▲" : "▼") : ""}
              </th>
              <th className="sortable" onClick={() => toggleSort("asset_type")}>
                Type {sortCol === "asset_type" ? (sortAsc ? "▲" : "▼") : ""}
              </th>
              <th>Path</th>
              <th className="sortable" onClick={() => toggleSort("complexity")}>
                Complexity {sortCol === "complexity" ? (sortAsc ? "▲" : "▼") : ""}
              </th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr><td colSpan={5} className="text-muted" style={{ textAlign: "center" }}>No items match filters</td></tr>
            ) : (
              filtered.map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td><span className="badge">{item.asset_type}</span></td>
                  <td className="text-muted">{item.source_path}</td>
                  <td><span className={`complexity-badge complexity-${item.complexity.toLowerCase()}`}>{item.complexity}</span></td>
                  <td><span className={`status-badge status-${item.migration_status}`}>{item.migration_status}</span></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="text-muted" style={{ marginTop: 8 }}>
        Showing {filtered.length} of {inventory.total} items
      </p>
    </div>
  );
}
