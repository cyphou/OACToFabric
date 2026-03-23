import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  PlayCircle,
  Sun,
  Moon,
  Heart,
} from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useHealth } from "../hooks/useMigrations";

export default function Layout() {
  const { theme, toggle } = useTheme();
  const { data: health } = useHealth();

  return (
    <div className="layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <LayoutDashboard size={22} />
          <span>OAC Migration</span>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            <LayoutDashboard size={18} />
            Migrations
          </NavLink>
          <NavLink to="/new" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            <PlayCircle size={18} />
            New Migration
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <button className="icon-btn" onClick={toggle} title="Toggle theme">
            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          <span className="health-badge" data-status={health?.status ?? "unknown"}>
            <Heart size={14} />
            {health?.status ?? "…"}
          </span>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
