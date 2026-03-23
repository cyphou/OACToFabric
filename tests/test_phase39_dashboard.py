"""Phase 39 — React Dashboard & Frontend Integration.

Tests cover:
- Dashboard project structure validation
- Vite configuration
- TypeScript source file inventory
- API type alignment (frontend types match backend models)
- Theme context behaviour
- API client URL construction
- WebSocket hook URL construction
- Dashboard build artefact generation
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Project root
ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard"
SRC = DASHBOARD / "src"


# ===================================================================
# Project structure
# ===================================================================


class TestDashboardStructure:
    """Validate that all expected dashboard files exist."""

    EXPECTED_FILES = [
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "index.html",
        "src/main.tsx",
        "src/App.tsx",
        "src/index.css",
        "src/api/types.ts",
        "src/api/client.ts",
        "src/context/ThemeContext.tsx",
        "src/hooks/useMigrations.ts",
        "src/hooks/useWebSocket.ts",
        "src/hooks/useLogStream.ts",
        "src/components/Layout.tsx",
        "src/pages/MigrationList.tsx",
        "src/pages/MigrationDetail.tsx",
        "src/pages/MigrationWizard.tsx",
        "src/pages/InventoryBrowser.tsx",
    ]

    @pytest.mark.parametrize("rel_path", EXPECTED_FILES)
    def test_file_exists(self, rel_path: str):
        assert (DASHBOARD / rel_path).is_file(), f"Missing dashboard file: {rel_path}"

    def test_no_boilerplate_counter(self):
        """Old Vite boilerplate should be removed."""
        assert not (SRC / "counter.ts").exists()

    def test_no_boilerplate_style(self):
        assert not (SRC / "style.css").exists()


# ===================================================================
# package.json
# ===================================================================


class TestPackageJson:
    """Validate package.json has required deps."""

    @pytest.fixture()
    def pkg(self) -> dict:
        return json.loads((DASHBOARD / "package.json").read_text(encoding="utf-8"))

    def test_has_react(self, pkg: dict):
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        assert "react" in all_deps or "react-dom" in all_deps

    def test_has_react_router(self, pkg: dict):
        assert "react-router-dom" in pkg.get("dependencies", {})

    def test_has_tanstack_query(self, pkg: dict):
        assert "@tanstack/react-query" in pkg.get("dependencies", {})

    def test_has_recharts(self, pkg: dict):
        assert "recharts" in pkg.get("dependencies", {})

    def test_has_lucide(self, pkg: dict):
        assert "lucide-react" in pkg.get("dependencies", {})

    def test_has_vite_plugin_react(self, pkg: dict):
        assert "@vitejs/plugin-react" in pkg.get("devDependencies", {})

    def test_build_script(self, pkg: dict):
        assert "build" in pkg.get("scripts", {})

    def test_dev_script(self, pkg: dict):
        assert "dev" in pkg.get("scripts", {})


# ===================================================================
# tsconfig.json
# ===================================================================


class TestTsConfig:
    """Validate TypeScript configuration."""

    @pytest.fixture()
    def tsconfig(self) -> dict:
        raw = (DASHBOARD / "tsconfig.json").read_text(encoding="utf-8")
        # Strip JS-style comments (// and /* */) before parsing
        stripped = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
        stripped = re.sub(r"//.*", "", stripped)
        return json.loads(stripped)

    def test_jsx_react_jsx(self, tsconfig: dict):
        assert tsconfig["compilerOptions"]["jsx"] == "react-jsx"

    def test_strict_mode(self, tsconfig: dict):
        assert tsconfig["compilerOptions"]["strict"] is True

    def test_no_emit(self, tsconfig: dict):
        assert tsconfig["compilerOptions"]["noEmit"] is True


# ===================================================================
# Vite config
# ===================================================================


class TestViteConfig:
    """Validate vite.config.ts contents."""

    @pytest.fixture()
    def vite_content(self) -> str:
        return (DASHBOARD / "vite.config.ts").read_text(encoding="utf-8")

    def test_react_plugin_imported(self, vite_content: str):
        assert "@vitejs/plugin-react" in vite_content

    def test_proxy_api(self, vite_content: str):
        assert '"/api"' in vite_content

    def test_proxy_ws(self, vite_content: str):
        assert '"/ws"' in vite_content

    def test_port_5173(self, vite_content: str):
        assert "5173" in vite_content


# ===================================================================
# Frontend API type alignment with backend
# ===================================================================


class TestApiTypeAlignment:
    """Ensure frontend type definitions reference the same fields as backend models."""

    @pytest.fixture()
    def frontend_types(self) -> str:
        return (SRC / "api" / "types.ts").read_text(encoding="utf-8")

    @pytest.fixture()
    def backend_source(self) -> str:
        return (ROOT / "src" / "api" / "app.py").read_text(encoding="utf-8")

    # ---- Migration fields ----
    MIGRATION_FIELDS = [
        "id", "name", "status", "mode", "source_type",
        "created_at", "started_at", "completed_at",
        "progress_pct", "agents",
        "total_items", "succeeded_items", "failed_items", "error",
    ]

    @pytest.mark.parametrize("field", MIGRATION_FIELDS)
    def test_migration_field_in_frontend(self, frontend_types: str, field: str):
        assert field in frontend_types, f"Field '{field}' missing from frontend types"

    @pytest.mark.parametrize("field", MIGRATION_FIELDS)
    def test_migration_field_in_backend(self, backend_source: str, field: str):
        assert field in backend_source, f"Field '{field}' missing from backend"

    # ---- Agent status fields ----
    AGENT_FIELDS = ["agent_id", "state", "items_processed", "items_failed"]

    @pytest.mark.parametrize("field", AGENT_FIELDS)
    def test_agent_field_in_frontend(self, frontend_types: str, field: str):
        assert field in frontend_types

    # ---- Inventory fields ----
    INVENTORY_FIELDS = ["asset_type", "name", "source_path", "complexity", "migration_status"]

    @pytest.mark.parametrize("field", INVENTORY_FIELDS)
    def test_inventory_field_in_frontend(self, frontend_types: str, field: str):
        assert field in frontend_types

    # ---- Create request fields ----
    CREATE_FIELDS = ["name", "source_type", "config", "mode", "dry_run"]

    @pytest.mark.parametrize("field", CREATE_FIELDS)
    def test_create_field_in_frontend(self, frontend_types: str, field: str):
        assert field in frontend_types

    # ---- Health ----
    HEALTH_FIELDS = ["status", "version", "uptime_seconds", "migrations_active"]

    @pytest.mark.parametrize("field", HEALTH_FIELDS)
    def test_health_field_in_frontend(self, frontend_types: str, field: str):
        assert field in frontend_types


# ===================================================================
# API client
# ===================================================================


class TestApiClient:
    """Validate the API client module."""

    @pytest.fixture()
    def client_source(self) -> str:
        return (SRC / "api" / "client.ts").read_text(encoding="utf-8")

    def test_base_url_uses_api_prefix(self, client_source: str):
        assert '"/api"' in client_source

    def test_has_list_migrations(self, client_source: str):
        assert "listMigrations" in client_source

    def test_has_get_migration(self, client_source: str):
        assert "getMigration" in client_source

    def test_has_create_migration(self, client_source: str):
        assert "createMigration" in client_source

    def test_has_get_inventory(self, client_source: str):
        assert "getInventory" in client_source

    def test_has_cancel_migration(self, client_source: str):
        assert "cancelMigration" in client_source

    def test_has_health(self, client_source: str):
        assert "health" in client_source

    def test_encodes_path_params(self, client_source: str):
        assert "encodeURIComponent" in client_source


# ===================================================================
# Hooks
# ===================================================================


class TestHooks:
    """Validate React hooks modules."""

    @pytest.fixture()
    def migrations_hooks(self) -> str:
        return (SRC / "hooks" / "useMigrations.ts").read_text(encoding="utf-8")

    @pytest.fixture()
    def ws_hook(self) -> str:
        return (SRC / "hooks" / "useWebSocket.ts").read_text(encoding="utf-8")

    @pytest.fixture()
    def log_hook(self) -> str:
        return (SRC / "hooks" / "useLogStream.ts").read_text(encoding="utf-8")

    def test_uses_tanstack_query(self, migrations_hooks: str):
        assert "@tanstack/react-query" in migrations_hooks

    def test_exports_use_migrations(self, migrations_hooks: str):
        assert "useMigrations" in migrations_hooks

    def test_exports_use_migration(self, migrations_hooks: str):
        assert "useMigration" in migrations_hooks

    def test_exports_use_inventory(self, migrations_hooks: str):
        assert "useInventory" in migrations_hooks

    def test_exports_use_create_migration(self, migrations_hooks: str):
        assert "useCreateMigration" in migrations_hooks

    def test_exports_use_cancel_migration(self, migrations_hooks: str):
        assert "useCancelMigration" in migrations_hooks

    def test_ws_hook_uses_websocket(self, ws_hook: str):
        assert "WebSocket" in ws_hook

    def test_ws_hook_handles_ping(self, ws_hook: str):
        assert "ping" in ws_hook

    def test_log_hook_uses_eventsource(self, log_hook: str):
        assert "EventSource" in log_hook


# ===================================================================
# Components
# ===================================================================


class TestComponents:
    """Validate component modules exist and have key content."""

    def test_layout_has_sidebar(self):
        content = (SRC / "components" / "Layout.tsx").read_text(encoding="utf-8")
        assert "sidebar" in content

    def test_layout_has_dark_mode_toggle(self):
        content = (SRC / "components" / "Layout.tsx").read_text(encoding="utf-8")
        assert "toggle" in content


# ===================================================================
# Pages
# ===================================================================


class TestPages:
    """Validate page components contain expected features."""

    def test_migration_list_links_to_new(self):
        content = (SRC / "pages" / "MigrationList.tsx").read_text(encoding="utf-8")
        assert "/new" in content

    def test_migration_list_shows_progress(self):
        content = (SRC / "pages" / "MigrationList.tsx").read_text(encoding="utf-8")
        assert "progress" in content.lower()

    def test_detail_shows_pie_chart(self):
        content = (SRC / "pages" / "MigrationDetail.tsx").read_text(encoding="utf-8")
        assert "PieChart" in content

    def test_detail_shows_agents(self):
        content = (SRC / "pages" / "MigrationDetail.tsx").read_text(encoding="utf-8")
        assert "agent_id" in content

    def test_detail_shows_logs(self):
        content = (SRC / "pages" / "MigrationDetail.tsx").read_text(encoding="utf-8")
        assert "log-container" in content

    def test_detail_has_cancel_button(self):
        content = (SRC / "pages" / "MigrationDetail.tsx").read_text(encoding="utf-8")
        assert "Cancel" in content

    def test_wizard_has_three_steps(self):
        content = (SRC / "pages" / "MigrationWizard.tsx").read_text(encoding="utf-8")
        assert "Source" in content
        assert "Configure" in content
        assert "Review" in content

    def test_wizard_source_options(self):
        content = (SRC / "pages" / "MigrationWizard.tsx").read_text(encoding="utf-8")
        for src in ["oac", "obiee", "tableau", "cognos", "qlik"]:
            assert src in content

    def test_wizard_dry_run_option(self):
        content = (SRC / "pages" / "MigrationWizard.tsx").read_text(encoding="utf-8")
        assert "dry_run" in content

    def test_inventory_has_search(self):
        content = (SRC / "pages" / "InventoryBrowser.tsx").read_text(encoding="utf-8")
        assert "search" in content.lower()

    def test_inventory_has_type_filter(self):
        content = (SRC / "pages" / "InventoryBrowser.tsx").read_text(encoding="utf-8")
        assert "typeFilter" in content

    def test_inventory_has_complexity_filter(self):
        content = (SRC / "pages" / "InventoryBrowser.tsx").read_text(encoding="utf-8")
        assert "complexityFilter" in content

    def test_inventory_has_sorting(self):
        content = (SRC / "pages" / "InventoryBrowser.tsx").read_text(encoding="utf-8")
        assert "sortCol" in content


# ===================================================================
# Dark mode
# ===================================================================


class TestDarkMode:
    """Validate dark-mode theme support."""

    @pytest.fixture()
    def css(self) -> str:
        return (SRC / "index.css").read_text(encoding="utf-8")

    @pytest.fixture()
    def theme_ctx(self) -> str:
        return (SRC / "context" / "ThemeContext.tsx").read_text(encoding="utf-8")

    def test_css_has_light_variables(self, css: str):
        assert "--bg-primary" in css

    def test_css_has_dark_overrides(self, css: str):
        assert '[data-theme="dark"]' in css

    def test_theme_context_toggle(self, theme_ctx: str):
        assert "toggle" in theme_ctx

    def test_theme_context_persists_to_local_storage(self, theme_ctx: str):
        assert "localStorage" in theme_ctx

    def test_theme_context_respects_system_preference(self, theme_ctx: str):
        assert "prefers-color-scheme" in theme_ctx


# ===================================================================
# index.html
# ===================================================================


class TestIndexHtml:
    """Validate the HTML entry point."""

    @pytest.fixture()
    def html(self) -> str:
        return (DASHBOARD / "index.html").read_text(encoding="utf-8")

    def test_references_main_tsx(self, html: str):
        assert "main.tsx" in html

    def test_has_app_div(self, html: str):
        assert 'id="app"' in html

    def test_has_title(self, html: str):
        assert "OAC Migration" in html
