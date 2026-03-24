"""Generate a standalone HTML migration report.

Produces a self-contained (single-file, no external dependencies) HTML report
with embedded CSS (inspired by the dashboard design system) and inline SVG
charts.  The report mirrors the style of enterprise migration assessment
reports (Tableau-to-Power-BI, etc.).

Usage (standalone)::

    from html_report_generator import generate_html_report
    html = generate_html_report(report_data)
    Path("report.html").write_text(html, encoding="utf-8")

Or as part of the migration pipeline via ``run_migration_test.py``.
"""

from __future__ import annotations

import html as html_lib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ═══════════════════════════════════════════════════════════════════════
# Data containers
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class VisualMappingEntry:
    source_type: str
    pbi_type: str
    count: int = 1
    warnings: list[str] = field(default_factory=list)


@dataclass
class SecurityMappingEntry:
    oac_role: str
    fabric_role: str
    rls_filters: int = 0
    ols_columns: int = 0
    aad_group: str = ""


@dataclass
class ETLMappingEntry:
    step_name: str
    source_type: str
    fabric_target: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class PromptMappingEntry:
    name: str
    source_type: str
    pbi_type: str
    source: str = ""


@dataclass
class ReportData:
    """Everything needed to render the HTML report."""

    # Discovery
    items: list[dict[str, Any]] = field(default_factory=list)
    by_source: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)

    # Schema
    ddl_results: list[dict[str, str]] = field(default_factory=list)

    # Semantic
    tmdl_files: dict[str, str] = field(default_factory=dict)
    translations: list[dict[str, Any]] = field(default_factory=list)
    review_items: list[dict[str, Any]] = field(default_factory=list)

    # Report / Visual mapping
    visual_mappings: list[VisualMappingEntry] = field(default_factory=list)
    prompt_mappings: list[PromptMappingEntry] = field(default_factory=list)
    pbir_pages: int = 0
    pbir_visuals: int = 0

    # Security
    security_mappings: list[SecurityMappingEntry] = field(default_factory=list)
    rls_rules_tmdl: str = ""

    # ETL
    etl_mappings: list[ETLMappingEntry] = field(default_factory=list)

    # Validation
    validation_layers: int = 0
    validation_total: int = 4
    validation_errors: list[str] = field(default_factory=list)

    # Meta
    elapsed_seconds: float = 0.0
    output_dir: str = ""
    timestamp: str = ""


# ═══════════════════════════════════════════════════════════════════════
# SVG helpers – lightweight inline charts
# ═══════════════════════════════════════════════════════════════════════

_PALETTE = [
    "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6",
    "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
    "#6366f1", "#a855f7", "#d946ef", "#0ea5e9",
]


def _svg_donut(data: dict[str, int], *, size: int = 200, hole: float = 0.55) -> str:
    """Return an inline SVG donut chart."""
    total = sum(data.values()) or 1
    r = size / 2 - 4
    cx = cy = size / 2
    inner_r = r * hole
    parts: list[str] = []
    angle = -90  # start at top

    for i, (label, value) in enumerate(data.items()):
        pct = value / total
        sweep = pct * 360
        if sweep < 0.5:
            continue
        start_rad = math.radians(angle)
        end_rad = math.radians(angle + sweep)
        x1 = cx + r * math.cos(start_rad)
        y1 = cy + r * math.sin(start_rad)
        x2 = cx + r * math.cos(end_rad)
        y2 = cy + r * math.sin(end_rad)
        ix1 = cx + inner_r * math.cos(end_rad)
        iy1 = cy + inner_r * math.sin(end_rad)
        ix2 = cx + inner_r * math.cos(start_rad)
        iy2 = cy + inner_r * math.sin(start_rad)
        large = 1 if sweep > 180 else 0
        color = _PALETTE[i % len(_PALETTE)]
        d = (
            f"M {x1:.1f},{y1:.1f} "
            f"A {r:.1f},{r:.1f} 0 {large} 1 {x2:.1f},{y2:.1f} "
            f"L {ix1:.1f},{iy1:.1f} "
            f"A {inner_r:.1f},{inner_r:.1f} 0 {large} 0 {ix2:.1f},{iy2:.1f} Z"
        )
        esc_label = html_lib.escape(label)
        parts.append(
            f'<path d="{d}" fill="{color}" stroke="#fff" stroke-width="1.5">'
            f"<title>{esc_label}: {value} ({pct:.0%})</title></path>"
        )
        angle += sweep

    # centre text
    parts.append(
        f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" '
        f'font-size="22" font-weight="700" fill="var(--text-primary)">{total}</text>'
        f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" '
        f'font-size="11" fill="var(--text-secondary)">assets</text>'
    )

    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;margin:auto">'
        + "".join(parts)
        + "</svg>"
    )
    return svg


def _svg_legend(data: dict[str, int]) -> str:
    items = []
    for i, (label, value) in enumerate(data.items()):
        c = _PALETTE[i % len(_PALETTE)]
        items.append(
            f'<span class="legend-item">'
            f'<span class="legend-dot" style="background:{c}"></span>'
            f'{html_lib.escape(label)} <b>({value})</b></span>'
        )
    return '<div class="legend">' + "".join(items) + "</div>"


def _svg_bar(data: dict[str, int], *, max_width: int = 300) -> str:
    mx = max(data.values()) if data else 1
    rows = []
    for i, (label, value) in enumerate(data.items()):
        w = max(int(value / mx * max_width), 4) if mx else 4
        c = _PALETTE[i % len(_PALETTE)]
        rows.append(
            f'<div class="bar-row">'
            f'<span class="bar-label">{html_lib.escape(label)}</span>'
            f'<div class="bar-track"><div class="bar-fill" '
            f'style="width:{w}px;background:{c}"></div></div>'
            f'<span class="bar-value">{value}</span></div>'
        )
    return '<div class="bar-chart">' + "".join(rows) + "</div>"


def _progress_ring(value: int, total: int, *, size: int = 80) -> str:
    pct = value / total if total else 0
    r = size / 2 - 6
    circ = 2 * math.pi * r
    offset = circ * (1 - pct)
    color = "#22c55e" if pct >= 1 else "#f59e0b" if pct >= 0.5 else "#ef4444"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" class="progress-ring">'
        f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" '
        f'stroke="var(--border)" stroke-width="6"/>'
        f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" '
        f'stroke="{color}" stroke-width="6" stroke-linecap="round" '
        f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}" '
        f'transform="rotate(-90 {size/2} {size/2})"/>'
        f'<text x="{size/2}" y="{size/2 + 5}" text-anchor="middle" '
        f'font-size="16" font-weight="700" fill="var(--text-primary)">'
        f'{value}/{total}</text></svg>'
    )


# ═══════════════════════════════════════════════════════════════════════
# CSS (self-contained, dark/light theme)
# ═══════════════════════════════════════════════════════════════════════

_CSS = """\
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-card: #ffffff;
  --bg-hover: #f1f5f9;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --border: #e2e8f0;
  --clr-primary: #3b82f6;
  --clr-primary-hover: #2563eb;
  --clr-success: #22c55e;
  --clr-danger: #ef4444;
  --clr-warning: #f59e0b;
  --clr-info: #3b82f6;
  --radius: 8px;
  --radius-sm: 4px;
  --shadow: 0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.1), 0 2px 4px -2px rgba(0,0,0,.1);
  --font: "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
}
[data-theme="dark"] {
  --bg-primary: #0f172a; --bg-secondary: #1e293b; --bg-card: #1e293b;
  --bg-hover: #334155; --text-primary: #f1f5f9; --text-secondary: #cbd5e1;
  --text-muted: #64748b; --border: #334155;
  --shadow: 0 1px 3px rgba(0,0,0,.4), 0 1px 2px rgba(0,0,0,.3);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.4), 0 2px 4px -2px rgba(0,0,0,.3);
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-family: var(--font); background: var(--bg-secondary); color: var(--text-primary); }
body { max-width: 1200px; margin: 0 auto; padding: 24px 20px 60px; }

/* Header */
.report-header {
  background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 100%);
  color: #fff; border-radius: var(--radius); padding: 40px 36px;
  margin-bottom: 28px; box-shadow: var(--shadow-md);
}
.report-header h1 { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.report-header .subtitle { font-size: 15px; opacity: .85; margin-bottom: 20px; }
.meta-row { display: flex; gap: 32px; flex-wrap: wrap; font-size: 13px; opacity: .9; }
.meta-row span b { font-weight: 600; }
.theme-toggle {
  position: fixed; top: 16px; right: 16px; z-index: 100;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 20px;
  padding: 6px 14px; font-size: 13px; cursor: pointer; box-shadow: var(--shadow);
  color: var(--text-primary);
}

/* Nav */
.toc { background: var(--bg-card); border-radius: var(--radius); padding: 20px 24px;
  margin-bottom: 24px; box-shadow: var(--shadow); }
.toc h2 { font-size: 16px; margin-bottom: 12px; }
.toc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }
.toc a { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: var(--radius-sm);
  font-size: 14px; color: var(--clr-primary); text-decoration: none; transition: background .15s; }
.toc a:hover { background: var(--bg-hover); }
.toc .num { display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; font-size: 11px; font-weight: 700; border-radius: 50%;
  background: var(--clr-primary); color: #fff; flex-shrink: 0; }

/* Section */
.section { background: var(--bg-card); border-radius: var(--radius); padding: 28px 28px 24px;
  margin-bottom: 20px; box-shadow: var(--shadow); }
.section h2 { font-size: 20px; font-weight: 700; margin-bottom: 16px; padding-bottom: 10px;
  border-bottom: 2px solid var(--border); display: flex; align-items: center; gap: 10px; }
.section h3 { font-size: 16px; font-weight: 600; margin: 18px 0 10px; color: var(--text-secondary); }

/* Stat grid */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px;
  margin-bottom: 18px; }
.stat-card { background: var(--bg-secondary); border-radius: var(--radius); padding: 16px 18px;
  text-align: center; }
.stat-card .value { font-size: 28px; font-weight: 700; color: var(--clr-primary); }
.stat-card .label { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

/* Tables */
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
th { text-align: left; padding: 10px 12px; font-weight: 600; font-size: 12px;
  text-transform: uppercase; letter-spacing: .5px; color: var(--text-muted);
  border-bottom: 2px solid var(--border); white-space: nowrap; }
td { padding: 9px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
tr:hover td { background: var(--bg-hover); }
.mono { font-family: "Cascadia Code", "Fira Code", monospace; font-size: 12px; }
.truncate { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Badges */
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-blue { background: #dbeafe; color: #1d4ed8; }
.badge-green { background: #dcfce7; color: #166534; }
.badge-amber { background: #fef3c7; color: #92400e; }
.badge-red { background: #fee2e2; color: #991b1b; }
.badge-purple { background: #ede9fe; color: #5b21b6; }
.badge-gray { background: #f1f5f9; color: #475569; }
[data-theme="dark"] .badge-blue { background: #1e3a5f; color: #93c5fd; }
[data-theme="dark"] .badge-green { background: #14532d; color: #86efac; }
[data-theme="dark"] .badge-amber { background: #78350f; color: #fde68a; }
[data-theme="dark"] .badge-red { background: #7f1d1d; color: #fca5a5; }
[data-theme="dark"] .badge-purple { background: #3b0764; color: #c4b5fd; }
[data-theme="dark"] .badge-gray { background: #334155; color: #94a3b8; }

/* Charts */
.chart-container { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; justify-content: center; }
.legend { display: flex; flex-wrap: wrap; gap: 8px 16px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.bar-chart { display: flex; flex-direction: column; gap: 6px; }
.bar-row { display: flex; align-items: center; gap: 8px; }
.bar-label { width: 140px; text-align: right; font-size: 13px; flex-shrink: 0; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; }
.bar-track { height: 20px; background: var(--bg-secondary); border-radius: 4px; flex: 1; max-width: 300px; }
.bar-fill { height: 100%; border-radius: 4px; transition: width .3s; }
.bar-value { font-size: 13px; font-weight: 600; width: 36px; }

/* Confidence */
.conf-high { color: #16a34a; font-weight: 600; }
.conf-med { color: #d97706; font-weight: 600; }
.conf-low { color: #dc2626; font-weight: 600; }

/* Collapsible */
details { margin-top: 12px; }
details summary { cursor: pointer; font-weight: 600; font-size: 14px; color: var(--clr-primary);
  padding: 8px 0; user-select: none; }
details summary:hover { text-decoration: underline; }
details[open] summary { margin-bottom: 8px; }

/* Code blocks */
pre { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius-sm);
  padding: 14px 16px; overflow-x: auto; font-family: "Cascadia Code", "Fira Code", monospace;
  font-size: 12px; line-height: 1.5; margin: 8px 0 12px; }

/* Two-col layout */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } }

/* Progress ring */
.progress-ring { display: block; margin: 0 auto 8px; }

/* Footer */
.report-footer { text-align: center; padding: 24px 0 12px; font-size: 12px; color: var(--text-muted); }

/* Print */
@media print {
  body { max-width: 100%; padding: 0; }
  .theme-toggle, .toc { display: none; }
  .section { break-inside: avoid; box-shadow: none; border: 1px solid #ddd; }
}
"""

_JS = """\
document.getElementById('themeToggle').addEventListener('click', function() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  html.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
  this.textContent = current === 'dark' ? '🌙 Dark' : '☀️ Light';
});
"""


# ═══════════════════════════════════════════════════════════════════════
# HTML builder
# ═══════════════════════════════════════════════════════════════════════

def _esc(s: Any) -> str:
    return html_lib.escape(str(s))


def _conf_class(v: float) -> str:
    if v >= 0.8:
        return "conf-high"
    if v >= 0.5:
        return "conf-med"
    return "conf-low"


def _stat(value: Any, label: str) -> str:
    return f'<div class="stat-card"><div class="value">{_esc(value)}</div><div class="label">{_esc(label)}</div></div>'


def generate_html_report(rd: ReportData) -> str:
    """Generate the complete standalone HTML report."""
    ts = rd.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total = len(rd.items)

    # ── Header ────────────────────────────────────────────────────────
    header = f"""
    <div class="report-header">
      <h1>OAC → Fabric &amp; Power BI Migration Report</h1>
      <p class="subtitle">Automated migration assessment &amp; conversion results</p>
      <div class="meta-row">
        <span><b>Generated:</b> {_esc(ts)}</span>
        <span><b>Assets:</b> {total}</span>
        <span><b>Elapsed:</b> {rd.elapsed_seconds:.1f}s</span>
        <span><b>Output:</b> {_esc(rd.output_dir)}</span>
      </div>
    </div>"""

    # ── TOC ───────────────────────────────────────────────────────────
    sections = [
        ("executive-summary", "Executive Summary"),
        ("discovery", "Discovery &amp; Inventory"),
        ("schema", "Schema Migration (DDL)"),
        ("semantic", "Semantic Model (TMDL)"),
        ("reports", "Report &amp; Visual Migration"),
        ("security", "Security Migration"),
        ("etl", "ETL &amp; Pipeline Migration"),
        ("validation", "Validation Results"),
    ]
    toc_items = "".join(
        f'<a href="#{sid}"><span class="num">{i}</span>{name}</a>'
        for i, (sid, name) in enumerate(sections, 1)
    )
    toc = f'<div class="toc"><h2>Contents</h2><div class="toc-grid">{toc_items}</div></div>'

    # ── 1. Executive Summary ──────────────────────────────────────────
    n_ddl = len(rd.ddl_results)
    n_tmdl = len(rd.tmdl_files)
    n_translations = len(rd.translations)
    n_reviews = len(rd.review_items)
    n_visuals = rd.pbir_visuals
    n_security = len(rd.security_mappings)
    n_etl = len(rd.etl_mappings)
    n_prompts = len(rd.prompt_mappings)

    exec_stats = (
        _stat(total, "Assets Discovered")
        + _stat(n_ddl, "DDL Tables")
        + _stat(n_tmdl, "TMDL Files")
        + _stat(n_translations, "Expressions Translated")
        + _stat(n_visuals, "Visuals Mapped")
        + _stat(n_prompts, "Prompts → Slicers")
        + _stat(n_security, "Security Roles")
        + _stat(n_etl, "ETL Steps Mapped")
    )

    # readiness score
    scored = 0
    scored_total = 0
    if n_ddl:
        scored += 1
        scored_total += 1
    elif rd.by_type.get("physicalTable", 0):
        scored_total += 1
    if n_tmdl:
        scored += 1
        scored_total += 1
    elif rd.by_type.get("logicalTable", 0):
        scored_total += 1
    if n_visuals:
        scored += 1
        scored_total += 1
    elif rd.by_type.get("analysis", 0):
        scored_total += 1
    if n_security:
        scored += 1
        scored_total += 1
    elif rd.by_type.get("securityRole", 0):
        scored_total += 1
    if rd.validation_layers:
        scored += 1
        scored_total += 1
    else:
        scored_total += 1
    readiness_pct = int(scored / scored_total * 100) if scored_total else 0

    exec_section = f"""
    <div class="section" id="executive-summary">
      <h2>📊 Executive Summary</h2>
      <div class="stat-grid">{exec_stats}</div>
      <div class="two-col" style="margin-top:16px">
        <div style="text-align:center">
          <h3>Migration Readiness</h3>
          {_progress_ring(scored, scored_total, size=100)}
          <p style="font-size:24px;font-weight:700;color:var(--clr-primary)">{readiness_pct}%</p>
          <p style="font-size:13px;color:var(--text-muted)">{scored}/{scored_total} layers converted</p>
        </div>
        <div style="text-align:center">
          <h3>Assets by Source</h3>
          {_svg_donut(rd.by_source, size=180)}
          {_svg_legend(rd.by_source)}
        </div>
      </div>
    </div>"""

    # ── 2. Discovery ──────────────────────────────────────────────────
    type_donut = _svg_donut(rd.by_type, size=200)
    type_legend = _svg_legend(rd.by_type)
    source_bar = _svg_bar(rd.by_source)

    inv_rows = ""
    for i, item in enumerate(rd.items, 1):
        atype = item.get("asset_type", "")
        badge_cls = {
            "physicalTable": "badge-blue", "logicalTable": "badge-green",
            "analysis": "badge-purple", "dashboard": "badge-purple",
            "securityRole": "badge-red", "prompt": "badge-amber",
            "filter": "badge-amber", "dataModel": "badge-green",
            "initBlock": "badge-gray", "subjectArea": "badge-gray",
            "presentationTable": "badge-gray",
        }.get(atype, "badge-gray")
        inv_rows += (
            f"<tr><td>{i}</td><td>{_esc(item.get('name', ''))}</td>"
            f'<td><span class="badge {badge_cls}">{_esc(atype)}</span></td>'
            f"<td>{_esc(item.get('source', ''))}</td>"
            f'<td class="mono truncate">{_esc(item.get("source_path", ""))}</td></tr>'
        )

    discovery_section = f"""
    <div class="section" id="discovery">
      <h2>🔍 Discovery &amp; Inventory</h2>
      <div class="stat-grid">
        {_stat(total, "Total Assets")}
        {_stat(len(rd.by_source), "Source Platforms")}
        {_stat(len(rd.by_type), "Asset Types")}
        {_stat(rd.by_type.get("physicalTable", 0), "Physical Tables")}
        {_stat(rd.by_type.get("logicalTable", 0), "Logical Tables")}
        {_stat(rd.by_type.get("analysis", 0) + rd.by_type.get("dashboard", 0), "Reports / Dashboards")}
      </div>
      <div class="two-col">
        <div style="text-align:center">
          <h3>By Asset Type</h3>
          {type_donut}
          {type_legend}
        </div>
        <div>
          <h3>By Source Platform</h3>
          {source_bar}
        </div>
      </div>
      <details>
        <summary>Full Inventory ({total} assets)</summary>
        <table>
          <thead><tr><th>#</th><th>Name</th><th>Type</th><th>Source</th><th>Path</th></tr></thead>
          <tbody>{inv_rows}</tbody>
        </table>
      </details>
    </div>"""

    # ── 3. Schema ─────────────────────────────────────────────────────
    ddl_rows = ""
    for i, d in enumerate(rd.ddl_results, 1):
        ddl_rows += (
            f"<tr><td>{i}</td><td class='mono'>{_esc(d['table'])}</td>"
            f"<td>{_esc(d.get('source', ''))}</td>"
            f'<td><span class="badge badge-blue">Lakehouse (Delta)</span></td></tr>'
        )

    ddl_details = ""
    for d in rd.ddl_results:
        ddl_details += f"<h4 class='mono'>{_esc(d['table'])}</h4><pre>{_esc(d['ddl'].strip())}</pre>"

    schema_section = f"""
    <div class="section" id="schema">
      <h2>🗄️ Schema Migration (DDL)</h2>
      <div class="stat-grid">
        {_stat(n_ddl, "Tables Generated")}
        {_stat(sum(1 for d in rd.ddl_results if d.get("source") == "rpd"), "From RPD")}
        {_stat(sum(1 for d in rd.ddl_results if d.get("source") == "qlik"), "From Qlik")}
      </div>
      <table>
        <thead><tr><th>#</th><th>Table</th><th>Source</th><th>Target</th></tr></thead>
        <tbody>{ddl_rows}</tbody>
      </table>
      <details>
        <summary>Generated DDL Statements</summary>
        {ddl_details}
      </details>
    </div>"""

    # ── 4. Semantic ───────────────────────────────────────────────────
    tmdl_files_rows = ""
    for fname, content in sorted(rd.tmdl_files.items()):
        tmdl_files_rows += (
            f"<tr><td class='mono'>{_esc(fname)}</td>"
            f"<td>{len(content):,}</td></tr>"
        )

    tx_rows = ""
    for i, tx in enumerate(rd.translations, 1):
        src = str(tx.get("original", ""))
        dax = str(tx.get("dax", ""))
        conf = tx.get("confidence", 0)
        method = tx.get("method", "")
        cls = _conf_class(conf)
        tx_rows += (
            f"<tr><td>{i}</td>"
            f'<td class="mono truncate">{_esc(src[:80])}</td>'
            f'<td class="mono truncate">{_esc(dax[:80])}</td>'
            f'<td class="{cls}">{conf:.0%}</td>'
            f"<td>{_esc(method)}</td></tr>"
        )

    review_rows = ""
    for r in rd.review_items:
        review_rows += (
            f"<tr><td>{_esc(r.get('type', ''))}</td>"
            f"<td>{_esc(r.get('table', ''))}</td>"
            f"<td>{_esc(r.get('column', r.get('hierarchy', '')))}</td>"
            f"<td>{_esc(r.get('reason', ''))}</td></tr>"
        )

    # confidence distribution
    high = sum(1 for t in rd.translations if t.get("confidence", 0) >= 0.8)
    med = sum(1 for t in rd.translations if 0.5 <= t.get("confidence", 0) < 0.8)
    low = sum(1 for t in rd.translations if t.get("confidence", 0) < 0.5)
    conf_donut = _svg_donut({"High (≥80%)": high, "Medium (50-79%)": med, "Low (<50%)": low}, size=140)
    conf_legend = _svg_legend({"High (≥80%)": high, "Medium (50-79%)": med, "Low (<50%)": low})

    semantic_section = f"""
    <div class="section" id="semantic">
      <h2>📐 Semantic Model (TMDL)</h2>
      <div class="stat-grid">
        {_stat(n_tmdl, "TMDL Files")}
        {_stat(n_translations, "Expressions")}
        {_stat(n_reviews, "Need Review")}
        {_stat(high, "High Confidence")}
      </div>
      <div class="two-col" style="margin-bottom:12px">
        <div>
          <h3>TMDL Files</h3>
          <table>
            <thead><tr><th>File</th><th>Size (chars)</th></tr></thead>
            <tbody>{tmdl_files_rows}</tbody>
          </table>
        </div>
        <div style="text-align:center">
          <h3>Expression Confidence</h3>
          {conf_donut}
          {conf_legend}
        </div>
      </div>
      <details>
        <summary>Expression Translations ({n_translations})</summary>
        <table>
          <thead><tr><th>#</th><th>Source</th><th>DAX</th><th>Conf.</th><th>Method</th></tr></thead>
          <tbody>{tx_rows}</tbody>
        </table>
      </details>
      {"<details><summary>Items Requiring Review (" + str(n_reviews) + ")</summary><table><thead><tr><th>Type</th><th>Table</th><th>Column</th><th>Reason</th></tr></thead><tbody>" + review_rows + "</tbody></table></details>" if review_rows else ""}
    </div>"""

    # ── 5. Report / Visual ────────────────────────────────────────────
    vm_rows = ""
    for vm in rd.visual_mappings:
        warn = ", ".join(vm.warnings) if vm.warnings else "—"
        vm_rows += (
            f"<tr><td>{_esc(vm.source_type)}</td>"
            f"<td>{_esc(vm.pbi_type)}</td>"
            f"<td>{vm.count}</td>"
            f"<td>{_esc(warn)}</td></tr>"
        )

    pm_rows = ""
    for pm in rd.prompt_mappings:
        pm_rows += (
            f"<tr><td>{_esc(pm.name)}</td>"
            f"<td>{_esc(pm.source_type)}</td>"
            f"<td>{_esc(pm.pbi_type)}</td>"
            f"<td>{_esc(pm.source)}</td></tr>"
        )

    report_section = f"""
    <div class="section" id="reports">
      <h2>📊 Report &amp; Visual Migration</h2>
      <div class="stat-grid">
        {_stat(rd.by_type.get("analysis", 0), "Analyses")}
        {_stat(rd.by_type.get("dashboard", 0), "Dashboards")}
        {_stat(len(rd.visual_mappings), "Visual Types Mapped")}
        {_stat(n_prompts, "Prompts → Slicers")}
        {_stat(rd.pbir_pages, "PBIR Pages")}
        {_stat(rd.pbir_visuals, "PBIR Visuals")}
      </div>
      <h3>Visual Type Mapping</h3>
      <table>
        <thead><tr><th>Source Type</th><th>Power BI Type</th><th>Count</th><th>Warnings</th></tr></thead>
        <tbody>{vm_rows if vm_rows else "<tr><td colspan='4' style='color:var(--text-muted)'>No visual mappings</td></tr>"}</tbody>
      </table>
      {"<h3>Prompt → Slicer Mapping</h3><table><thead><tr><th>Prompt</th><th>Source Type</th><th>PBI Type</th><th>Source</th></tr></thead><tbody>" + pm_rows + "</tbody></table>" if pm_rows else ""}
    </div>"""

    # ── 6. Security ───────────────────────────────────────────────────
    sec_rows = ""
    for sm in rd.security_mappings:
        sec_rows += (
            f"<tr><td>{_esc(sm.oac_role)}</td>"
            f"<td>{_esc(sm.fabric_role)}</td>"
            f"<td>{sm.rls_filters}</td>"
            f"<td>{sm.ols_columns}</td>"
            f"<td class='mono'>{_esc(sm.aad_group)}</td></tr>"
        )

    security_section = f"""
    <div class="section" id="security">
      <h2>🔒 Security Migration</h2>
      <div class="stat-grid">
        {_stat(n_security, "Roles Mapped")}
        {_stat(sum(s.rls_filters for s in rd.security_mappings), "RLS Filters")}
        {_stat(sum(s.ols_columns for s in rd.security_mappings), "OLS Permissions")}
      </div>
      <table>
        <thead><tr><th>OAC Role</th><th>Fabric Role</th><th>RLS Filters</th><th>OLS Columns</th><th>AAD Group</th></tr></thead>
        <tbody>{sec_rows if sec_rows else "<tr><td colspan='5' style='color:var(--text-muted)'>No security roles</td></tr>"}</tbody>
      </table>
      {"<details><summary>RLS TMDL</summary><pre>" + _esc(rd.rls_rules_tmdl) + "</pre></details>" if rd.rls_rules_tmdl else ""}
    </div>"""

    # ── 7. ETL ────────────────────────────────────────────────────────
    etl_rows = ""
    for em in rd.etl_mappings:
        warn = ", ".join(em.warnings) if em.warnings else "—"
        etl_rows += (
            f"<tr><td>{_esc(em.step_name)}</td>"
            f"<td>{_esc(em.source_type)}</td>"
            f"<td>{_esc(em.fabric_target)}</td>"
            f"<td>{_esc(warn)}</td></tr>"
        )

    etl_section = f"""
    <div class="section" id="etl">
      <h2>⚙️ ETL &amp; Pipeline Migration</h2>
      <div class="stat-grid">
        {_stat(n_etl, "Steps Mapped")}
        {_stat(sum(1 for e in rd.etl_mappings if "notebook" in e.fabric_target.lower()), "Notebooks")}
        {_stat(sum(1 for e in rd.etl_mappings if "copy" in e.fabric_target.lower()), "Copy Activities")}
      </div>
      <table>
        <thead><tr><th>Step</th><th>Source Type</th><th>Fabric Target</th><th>Warnings</th></tr></thead>
        <tbody>{etl_rows if etl_rows else "<tr><td colspan='4' style='color:var(--text-muted)'>No ETL data flows to migrate</td></tr>"}</tbody>
      </table>
    </div>"""

    # ── 8. Validation ─────────────────────────────────────────────────
    val_ring = _progress_ring(rd.validation_layers, rd.validation_total, size=90)
    val_errs = ""
    if rd.validation_errors:
        val_errs = "<ul>" + "".join(f"<li>{_esc(e)}</li>" for e in rd.validation_errors) + "</ul>"

    validation_section = f"""
    <div class="section" id="validation">
      <h2>✅ Validation Results</h2>
      <div style="display:flex;align-items:center;gap:32px;flex-wrap:wrap">
        <div style="text-align:center">
          {val_ring}
          <p style="font-size:13px;color:var(--text-muted)">Layers Passed</p>
        </div>
        <div class="stat-grid" style="flex:1">
          {_stat(rd.validation_layers, "Passed")}
          {_stat(rd.validation_total - rd.validation_layers, "Failed")}
          {_stat(len(rd.validation_errors), "Errors")}
        </div>
      </div>
      {val_errs}
      <p style="margin-top:12px;font-size:13px;color:var(--text-muted)">
        Detailed validation reports available in the <code>validation/</code> output directory.
      </p>
    </div>"""

    # ── Footer ────────────────────────────────────────────────────────
    footer = (
        '<div class="report-footer">'
        "Generated by <b>OAC-to-Fabric Migration Accelerator</b> — "
        f"{_esc(ts)}</div>"
    )

    # ── Assemble ──────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OAC → Fabric Migration Report</title>
  <style>{_CSS}</style>
</head>
<body>
  <button class="theme-toggle" id="themeToggle">🌙 Dark</button>
  {header}
  {toc}
  {exec_section}
  {discovery_section}
  {schema_section}
  {semantic_section}
  {report_section}
  {security_section}
  {etl_section}
  {validation_section}
  {footer}
  <script>{_JS}</script>
</body>
</html>"""
    return html
