#!/usr/bin/env python3
"""Generate a Business Migration ROI PowerPoint deck.

Usage:
    python scripts/generate_business_deck.py [--output path/to/deck.pptx]

Produces a 7-slide executive deck covering:
  1. Title slide
  2. Migration accelerated with GenAI (project matrix + KPIs)
  3. What Can Be Migrated (object coverage)
  4. Platform Coverage (multi-source)
  5. Automation & Time Savings
  6. ROI & Business Impact
  7. Next Steps / Call to Action
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION

# ── Brand colours ──────────────────────────────────────────────────────
MICROSOFT_BLUE = RGBColor(0x00, 0x78, 0xD4)
DARK_BLUE = RGBColor(0x00, 0x2B, 0x5C)
ACCENT_GREEN = RGBColor(0x10, 0x7C, 0x10)
ACCENT_ORANGE = RGBColor(0xFF, 0x8C, 0x00)
ACCENT_TEAL = RGBColor(0x00, 0xB7, 0xC3)
ACCENT_PURPLE = RGBColor(0x6B, 0x2D, 0x8B)
ACCENT_RED = RGBColor(0xD1, 0x34, 0x38)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF3, 0xF2, 0xF1)
MEDIUM_GRAY = RGBColor(0x60, 0x60, 0x60)
BLACK = RGBColor(0x00, 0x00, 0x00)

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


# ── Helpers ────────────────────────────────────────────────────────────

def _set_slide_bg(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_shape(slide, left, top, width, height, fill_color: RGBColor,
               shape_type=MSO_SHAPE.ROUNDED_RECTANGLE):
    shape = slide.shapes.add_shape(shape_type, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def _add_textbox(slide, left, top, width, height, text, font_size=18,
                 bold=False, color=BLACK, alignment=PP_ALIGN.LEFT,
                 font_name="Segoe UI"):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def _add_kpi_card(slide, left, top, width, height, title, value,
                  border_color, bg_color=WHITE):
    card = _add_shape(slide, left, top, width, height, bg_color)
    card.line.color.rgb = border_color
    card.line.width = Pt(3)

    # Title
    _add_textbox(slide, left + Inches(0.15), top + Inches(0.1),
                 width - Inches(0.3), Inches(0.4),
                 title, font_size=11, bold=True, color=border_color,
                 alignment=PP_ALIGN.CENTER)
    # Value
    _add_textbox(slide, left + Inches(0.1), top + Inches(0.45),
                 width - Inches(0.2), Inches(0.5),
                 value, font_size=22, bold=True, color=border_color,
                 alignment=PP_ALIGN.CENTER)


def _add_table(slide, left, top, width, rows_data, col_widths,
               header_color=MICROSOFT_BLUE, stripe_color=LIGHT_GRAY):
    """Add a styled table. rows_data: list of lists (first row = header)."""
    n_rows = len(rows_data)
    n_cols = len(rows_data[0])
    table_height = Inches(0.4) * n_rows
    shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, table_height)
    table = shape.table

    for ci, cw in enumerate(col_widths):
        table.columns[ci].width = cw

    for ri, row in enumerate(rows_data):
        for ci, cell_text in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            p.text = str(cell_text)
            p.font.size = Pt(12)
            p.font.name = "Segoe UI"
            p.alignment = PP_ALIGN.CENTER
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE

            if ri == 0:
                p.font.bold = True
                p.font.color.rgb = WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_color
            else:
                p.font.color.rgb = BLACK
                if ri % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = stripe_color
                else:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = WHITE

    return shape


# ── Slide Builders ─────────────────────────────────────────────────────

def slide_title(prs: Presentation):
    """Slide 1: Title."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    _set_slide_bg(slide, DARK_BLUE)

    _add_textbox(slide, Inches(1), Inches(1.5), Inches(11), Inches(1.2),
                 "OAC → Microsoft Fabric & Power BI",
                 font_size=40, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)

    _add_textbox(slide, Inches(1), Inches(2.8), Inches(11), Inches(0.8),
                 "Business Migration Assessment — ROI & Capabilities",
                 font_size=24, color=ACCENT_TEAL, alignment=PP_ALIGN.CENTER)

    # Tagline
    _add_textbox(slide, Inches(2), Inches(4.2), Inches(9), Inches(0.6),
                 "Fully automated, AI-accelerated migration  •  97% OAC object coverage  •  3,559 tests",
                 font_size=16, color=WHITE, alignment=PP_ALIGN.CENTER)

    # Bottom bar
    _add_shape(slide, Inches(0), Inches(6.8), SLIDE_WIDTH, Inches(0.7),
               MICROSOFT_BLUE, MSO_SHAPE.RECTANGLE)
    _add_textbox(slide, Inches(0.5), Inches(6.85), Inches(12), Inches(0.5),
                 "🚀 GitHub Copilot Accelerated   |   T-SQL → Spark SQL   •   PL/SQL → PySpark   •   "
                 "OAC RPD → Semantic Models   •   Data Quality   •   Auto Tests   •   Doc Generation",
                 font_size=12, color=WHITE, alignment=PP_ALIGN.CENTER)


def slide_migration_matrix(prs: Presentation):
    """Slide 2: Migration accelerated with GenAI — project matrix + KPIs."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, WHITE)

    _add_textbox(slide, Inches(0.5), Inches(0.2), Inches(8), Inches(0.6),
                 "Migration accelerated with GenAI",
                 font_size=30, bold=True, color=DARK_BLUE)

    _add_textbox(slide, Inches(8.5), Inches(0.25), Inches(4.5), Inches(0.5),
                 "Figures from other customers",
                 font_size=16, bold=True, color=ACCENT_ORANGE,
                 alignment=PP_ALIGN.RIGHT)

    # ── Project matrix table ──
    header = ["PROJECT", "TODAY", "TOMORROW", "W/o Copilot", "With Copilot", "Gain"]
    rows = [
        header,
        ["BI Finance", "Azure SQL", "Fabric Lakehouse", "5–7 wks", "3–4 wks", "–40%"],
        ["Enterprise DW\n(US + Brazil)", "Oracle Exadata → OAC", "Fabric Warehouse", "8–12 wks", "5–7 wks", "–40%"],
        ["Noram", "Oracle Analytics Cloud", "Fabric + Power BI", "5–7 wks", "3–4 wks", "–35%"],
        ["Informatica ETL", "Informatica", "Fabric Pipelines", "8–10 wks", "4–5 wks", "–50%"],
        ["Total Estimated", "", "", "8–12 months", "4–6 months", "~50%"],
    ]
    col_widths = [Inches(1.6), Inches(1.6), Inches(1.6), Inches(1.3), Inches(1.3), Inches(0.9)]

    tbl_shape = _add_table(slide, Inches(0.3), Inches(1.0), Inches(8.3),
                           rows, col_widths)
    # Colour the Gain column cells
    table = tbl_shape.table
    for ri in range(1, len(rows)):
        gain_cell = table.cell(ri, 5)
        gain_cell.fill.solid()
        if ri == len(rows) - 1:
            gain_cell.fill.fore_color.rgb = ACCENT_GREEN
            # Total row green bg
            for ci in range(6):
                c = table.cell(ri, ci)
                c.fill.solid()
                c.fill.fore_color.rgb = ACCENT_GREEN
                c.text_frame.paragraphs[0].font.color.rgb = WHITE
                c.text_frame.paragraphs[0].font.bold = True
        else:
            gain_cell.fill.fore_color.rgb = ACCENT_GREEN
            gain_cell.text_frame.paragraphs[0].font.color.rgb = WHITE
            gain_cell.text_frame.paragraphs[0].font.bold = True

    # ── KPI cards on the right ──
    kpi_data = [
        ("Infra TCO Reduction", "–50 to –65%", MICROSOFT_BLUE),
        ("Ops Effort Reduction", "–40 to –60%", ACCENT_GREEN),
        ("Time-to-Insight", "–50 to –70%", ACCENT_TEAL),
        ("Time to Migrate", "–50%", ACCENT_ORANGE),
        ("Payback Period", "9–14 mo.", ACCENT_PURPLE),
    ]
    card_left = Inches(9.0)
    card_top_start = Inches(1.0)
    card_w = Inches(3.8)
    card_h = Inches(1.05)
    card_gap = Inches(0.15)

    for i, (title, value, color) in enumerate(kpi_data):
        _add_kpi_card(slide, card_left,
                      card_top_start + i * (card_h + card_gap),
                      card_w, card_h, title, value, color)

    # Bottom GitHub Copilot bar
    bar = _add_shape(slide, Inches(0), Inches(6.6), SLIDE_WIDTH, Inches(0.9),
                     DARK_BLUE, MSO_SHAPE.RECTANGLE)
    _add_textbox(slide, Inches(0.5), Inches(6.65), Inches(12), Inches(0.35),
                 "🚀 GitHub Copilot Accelerated",
                 font_size=14, bold=True, color=WHITE,
                 alignment=PP_ALIGN.LEFT)

    tags = [
        ("T-SQL → Spark SQL", MICROSOFT_BLUE),
        ("PL/SQL → PySpark", ACCENT_GREEN),
        ("OAC RPD → Semantic Models", ACCENT_ORANGE),
        ("Data Quality", ACCENT_RED),
        ("Refactor & Optimize", ACCENT_TEAL),
        ("Auto Tests", MEDIUM_GRAY),
        ("Doc Generation", MEDIUM_GRAY),
    ]
    tag_left = Inches(0.5)
    for label, color in tags:
        w = Inches(len(label) * 0.11 + 0.3)
        tag = _add_shape(slide, tag_left, Inches(7.05), w, Inches(0.3),
                         color, MSO_SHAPE.ROUNDED_RECTANGLE)
        tag.text_frame.paragraphs[0].text = label
        tag.text_frame.paragraphs[0].font.size = Pt(9)
        tag.text_frame.paragraphs[0].font.color.rgb = WHITE
        tag.text_frame.paragraphs[0].font.bold = True
        tag.text_frame.paragraphs[0].font.name = "Segoe UI"
        tag.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        tag_left += w + Inches(0.1)


def slide_what_can_be_migrated(prs: Presentation):
    """Slide 3: What Can Be Migrated — 97% coverage breakdown."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, WHITE)

    _add_textbox(slide, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
                 "What Can Be Migrated — 97% OAC Object Coverage",
                 font_size=28, bold=True, color=DARK_BLUE)

    _add_textbox(slide, Inches(0.5), Inches(0.75), Inches(12), Inches(0.4),
                 "60 of 62 OAC object types are fully automated  •  2 require manual review (cell-level security, custom OAC plugins)",
                 font_size=13, color=MEDIUM_GRAY)

    # ── Left column: automated categories ──
    categories = [
        ("Schema & Data", [
            "Tables, Views, Columns, Data Types → Fabric Lakehouse (Delta)",
            "Materialized Views → Fabric Warehouse MVs",
            "Oracle Mirroring → Fabric Mirroring (near-real-time)",
        ], MICROSOFT_BLUE),
        ("ETL / Data Pipelines", [
            "OAC Data Flows → Dataflow Gen2 + Fabric Notebooks (PySpark)",
            "PL/SQL Stored Procedures → PySpark notebooks",
            "Pivot/Unpivot, Error Row Routing, Parallel Chains",
        ], ACCENT_GREEN),
        ("Semantic Models", [
            "RPD Logical Model → TMDL (tables, relationships, hierarchies)",
            "OAC Expressions → DAX measures (120+ rules)",
            "Calculation Groups, DAX UDFs, Direct Lake on OneLake",
        ], ACCENT_ORANGE),
        ("Reports & Dashboards", [
            "OAC Analyses → PBIR reports (80+ visual types)",
            "BI Publisher → Paginated Reports (.rdl)",
            "Alerts/Agents → Data Activator triggers",
            "Action Links → Translytical Task Flows + Drillthrough",
        ], ACCENT_TEAL),
        ("Security & Governance", [
            "Application Roles → Fabric Workspace Roles",
            "Row-Level Security → DAX RLS (dynamic, hierarchy-based)",
            "Object-Level Security → OLS definitions",
            "AAD Group Provisioning, Audit Trail Migration",
        ], ACCENT_PURPLE),
    ]

    y = Inches(1.3)
    for cat_name, items, color in categories:
        # Category header
        bar = _add_shape(slide, Inches(0.5), y, Inches(6), Inches(0.35),
                         color, MSO_SHAPE.ROUNDED_RECTANGLE)
        bar.text_frame.paragraphs[0].text = f"  {cat_name}"
        bar.text_frame.paragraphs[0].font.size = Pt(13)
        bar.text_frame.paragraphs[0].font.bold = True
        bar.text_frame.paragraphs[0].font.color.rgb = WHITE
        bar.text_frame.paragraphs[0].font.name = "Segoe UI"
        y += Inches(0.4)

        for item in items:
            _add_textbox(slide, Inches(0.7), y, Inches(5.8), Inches(0.25),
                         f"✓  {item}", font_size=10, color=BLACK)
            y += Inches(0.22)
        y += Inches(0.08)

    # ── Right column: coverage chart (using shapes to simulate) ──
    chart_left = Inches(7.2)

    _add_textbox(slide, chart_left, Inches(1.3), Inches(5.5), Inches(0.4),
                 "Coverage by Migration Layer",
                 font_size=16, bold=True, color=DARK_BLUE)

    layers = [
        ("Schema & Data", 100, MICROSOFT_BLUE),
        ("ETL Pipelines", 95, ACCENT_GREEN),
        ("Semantic Models", 98, ACCENT_ORANGE),
        ("Reports & Dashboards", 97, ACCENT_TEAL),
        ("Security & Governance", 95, ACCENT_PURPLE),
        ("Overall", 97, ACCENT_GREEN),
    ]
    bar_y = Inches(1.85)
    bar_max_w = Inches(4.0)

    for label, pct, color in layers:
        _add_textbox(slide, chart_left, bar_y, Inches(2.0), Inches(0.3),
                     label, font_size=11, bold=True, color=BLACK)
        # Background bar
        _add_shape(slide, chart_left + Inches(2.1), bar_y + Inches(0.02),
                   bar_max_w, Inches(0.25), LIGHT_GRAY, MSO_SHAPE.ROUNDED_RECTANGLE)
        # Fill bar
        fill_w = int(bar_max_w * pct / 100)
        _add_shape(slide, chart_left + Inches(2.1), bar_y + Inches(0.02),
                   fill_w, Inches(0.25), color, MSO_SHAPE.ROUNDED_RECTANGLE)
        # Percentage label
        _add_textbox(slide, chart_left + Inches(2.1) + fill_w + Inches(0.1),
                     bar_y, Inches(0.6), Inches(0.3),
                     f"{pct}%", font_size=12, bold=True, color=color)
        bar_y += Inches(0.38)

    # ── Multi-source connectors box ──
    box_y = Inches(4.5)
    _add_textbox(slide, chart_left, box_y, Inches(5.5), Inches(0.35),
                 "Multi-Source Platform Connectors",
                 font_size=14, bold=True, color=DARK_BLUE)

    sources = [
        ("Oracle Analytics Cloud", "Full (primary)", ACCENT_GREEN),
        ("Tableau", "Full (TWB/TWBX + REST)", ACCENT_GREEN),
        ("IBM Cognos", "Full (report specs + expressions)", ACCENT_GREEN),
        ("Qlik Sense", "Full (load scripts + set analysis)", ACCENT_GREEN),
        ("Essbase", "Full (outlines + calc scripts + MDX)", ACCENT_GREEN),
        ("OBIEE", "Metadata + Catalog API", ACCENT_ORANGE),
    ]
    sy = box_y + Inches(0.4)
    for src, status, color in sources:
        _add_textbox(slide, chart_left + Inches(0.1), sy, Inches(2.2), Inches(0.25),
                     src, font_size=10, bold=True, color=BLACK)
        _add_textbox(slide, chart_left + Inches(2.4), sy, Inches(3.0), Inches(0.25),
                     status, font_size=10, color=color)
        sy += Inches(0.22)


def slide_time_savings(prs: Presentation):
    """Slide 4: Automation & Time Savings."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, WHITE)

    _add_textbox(slide, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
                 "Automation & Time Savings",
                 font_size=28, bold=True, color=DARK_BLUE)

    # ── Before vs After comparison ──
    header = ["Migration Phase", "Manual (Traditional)", "Automated (This Tool)", "Time Saved"]
    rows = [
        header,
        ["Discovery & Inventory", "2–4 weeks", "< 1 day", "90%+"],
        ["Schema Migration (DDL)", "1–2 weeks", "Minutes (auto-generated)", "95%+"],
        ["ETL Pipeline Conversion", "4–8 weeks", "1–2 weeks", "60–75%"],
        ["Semantic Model (RPD → TMDL)", "3–6 weeks", "1–3 days", "85%+"],
        ["Report Migration", "4–8 weeks", "1–2 weeks", "60–75%"],
        ["Security (RLS/OLS)", "1–2 weeks", "Hours", "90%+"],
        ["Validation & Testing", "2–4 weeks", "< 1 week (3,559 auto tests)", "70%+"],
        ["Total End-to-End", "8–12 months", "4–6 months", "~50%"],
    ]
    col_widths = [Inches(2.4), Inches(2.5), Inches(3.2), Inches(1.2)]
    tbl = _add_table(slide, Inches(0.5), Inches(1.0), Inches(9.3), rows, col_widths)
    # Highlight total row
    table = tbl.table
    last = len(rows) - 1
    for ci in range(4):
        c = table.cell(last, ci)
        c.fill.solid()
        c.fill.fore_color.rgb = ACCENT_GREEN
        c.text_frame.paragraphs[0].font.color.rgb = WHITE
        c.text_frame.paragraphs[0].font.bold = True

    # ── Right side: key stats ──
    stats = [
        ("150", "Source Modules", MICROSOFT_BLUE),
        ("3,559", "Automated Tests", ACCENT_GREEN),
        ("120+", "DAX Translation Rules", ACCENT_ORANGE),
        ("80+", "Visual Type Mappings", ACCENT_TEAL),
        ("8", "Specialized Agents", ACCENT_PURPLE),
    ]
    sx = Inches(10.2)
    sy = Inches(1.0)
    for val, label, color in stats:
        card = _add_shape(slide, sx, sy, Inches(2.8), Inches(1.0), WHITE)
        card.line.color.rgb = color
        card.line.width = Pt(2)
        _add_textbox(slide, sx + Inches(0.1), sy + Inches(0.05),
                     Inches(2.6), Inches(0.55),
                     val, font_size=28, bold=True, color=color,
                     alignment=PP_ALIGN.CENTER)
        _add_textbox(slide, sx + Inches(0.1), sy + Inches(0.55),
                     Inches(2.6), Inches(0.35),
                     label, font_size=11, color=MEDIUM_GRAY,
                     alignment=PP_ALIGN.CENTER)
        sy += Inches(1.15)

    # ── Bottom insight ──
    insight = _add_shape(slide, Inches(0.5), Inches(6.0), Inches(12.3), Inches(0.8),
                         LIGHT_GRAY, MSO_SHAPE.ROUNDED_RECTANGLE)
    _add_textbox(slide, Inches(0.8), Inches(6.1), Inches(11.8), Inches(0.6),
                 "💡 GitHub Copilot further accelerates code translation tasks (PL/SQL → PySpark, OAC expressions → DAX) "
                 "by 30–50%, reducing the \"With Copilot\" timelines shown in the project matrix.",
                 font_size=12, color=DARK_BLUE)


def slide_roi(prs: Presentation):
    """Slide 5: ROI & Business Impact."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, WHITE)

    _add_textbox(slide, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
                 "ROI & Business Impact",
                 font_size=28, bold=True, color=DARK_BLUE)

    # ── Large KPI cards across top ──
    top_kpis = [
        ("Infrastructure TCO", "–50 to –65%", "Eliminate Oracle licensing,\nhardware, & DBA overhead", MICROSOFT_BLUE),
        ("Operational Effort", "–40 to –60%", "Automated pipelines replace\nmanual ETL & report builds", ACCENT_GREEN),
        ("Time to Migrate", "–50%", "AI-accelerated migration\n8–12 mo → 4–6 mo", ACCENT_ORANGE),
        ("Time to Insight", "–50 to –70%", "Self-service analytics,\nreal-time dashboards", ACCENT_TEAL),
    ]
    kw = Inches(2.95)
    kh = Inches(1.5)
    kx = Inches(0.5)
    for title, value, detail, color in top_kpis:
        card = _add_shape(slide, kx, Inches(1.0), kw, kh, WHITE)
        card.line.color.rgb = color
        card.line.width = Pt(3)
        _add_textbox(slide, kx + Inches(0.1), Inches(1.05), kw - Inches(0.2), Inches(0.3),
                     title, font_size=12, bold=True, color=color,
                     alignment=PP_ALIGN.CENTER)
        _add_textbox(slide, kx + Inches(0.1), Inches(1.35), kw - Inches(0.2), Inches(0.5),
                     value, font_size=26, bold=True, color=color,
                     alignment=PP_ALIGN.CENTER)
        _add_textbox(slide, kx + Inches(0.1), Inches(1.9), kw - Inches(0.2), Inches(0.5),
                     detail, font_size=10, color=MEDIUM_GRAY,
                     alignment=PP_ALIGN.CENTER)
        kx += kw + Inches(0.15)

    # ── Cost comparison table ──
    _add_textbox(slide, Inches(0.5), Inches(2.8), Inches(6), Inches(0.4),
                 "3-Year Total Cost of Ownership (indicative)",
                 font_size=16, bold=True, color=DARK_BLUE)

    cost_rows = [
        ["Cost Category", "Oracle (Current)", "Microsoft Fabric", "Savings"],
        ["Database Licensing", "$800K–$1.5M/yr", "Included in Fabric", "100%"],
        ["BI Licensing (OAC)", "$200K–$500K/yr", "Power BI Pro/Premium", "40–60%"],
        ["Infrastructure (HW/Cloud)", "$300K–$600K/yr", "Pay-per-use (CU)", "50–70%"],
        ["DBA / ETL Admin", "4–6 FTEs", "1–2 FTEs", "60–75%"],
        ["Report Development", "3–5 FTEs", "1–2 FTEs (self-service)", "50–70%"],
        ["3-Year Net Savings", "", "", "$2M–$6M+"],
    ]
    col_widths_cost = [Inches(2.0), Inches(2.0), Inches(2.2), Inches(1.2)]
    tbl = _add_table(slide, Inches(0.5), Inches(3.3), Inches(7.4),
                     cost_rows, col_widths_cost)
    table = tbl.table
    last = len(cost_rows) - 1
    for ci in range(4):
        c = table.cell(last, ci)
        c.fill.solid()
        c.fill.fore_color.rgb = ACCENT_GREEN
        c.text_frame.paragraphs[0].font.color.rgb = WHITE
        c.text_frame.paragraphs[0].font.bold = True

    # ── Right: payback timeline ──
    _add_textbox(slide, Inches(8.3), Inches(2.8), Inches(4.5), Inches(0.4),
                 "Payback Timeline",
                 font_size=16, bold=True, color=DARK_BLUE)

    milestones = [
        ("Month 1–2", "Discovery + Schema Migration", MICROSOFT_BLUE),
        ("Month 3–4", "ETL + Semantic Model + Reports", ACCENT_GREEN),
        ("Month 5–6", "Security + Validation + Go-Live", ACCENT_ORANGE),
        ("Month 9–14", "Full ROI Payback", ACCENT_PURPLE),
    ]
    my = Inches(3.3)
    for period, desc, color in milestones:
        # Timeline dot
        dot = _add_shape(slide, Inches(8.5), my + Inches(0.05),
                         Inches(0.2), Inches(0.2), color, MSO_SHAPE.OVAL)
        # Line
        if period != "Month 9–14":
            _add_shape(slide, Inches(8.58), my + Inches(0.25),
                       Inches(0.04), Inches(0.6), color, MSO_SHAPE.RECTANGLE)
        _add_textbox(slide, Inches(8.9), my, Inches(1.5), Inches(0.3),
                     period, font_size=12, bold=True, color=color)
        _add_textbox(slide, Inches(8.9), my + Inches(0.25), Inches(4.0), Inches(0.3),
                     desc, font_size=10, color=MEDIUM_GRAY)
        my += Inches(0.7)

    # ── Bottom: risk mitigation ──
    _add_textbox(slide, Inches(0.5), Inches(6.1), Inches(12), Inches(0.4),
                 "Risk Mitigation",
                 font_size=14, bold=True, color=DARK_BLUE)
    risks = ("✓ Incremental migration (wave-based)    "
             "✓ Automated rollback    "
             "✓ 3,559 validation tests    "
             "✓ Data reconciliation (row counts + checksums)    "
             "✓ Visual regression testing")
    _add_textbox(slide, Inches(0.5), Inches(6.5), Inches(12), Inches(0.4),
                 risks, font_size=11, color=ACCENT_GREEN)


def slide_platform_architecture(prs: Presentation):
    """Slide 6: Platform Architecture (simplified)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, WHITE)

    _add_textbox(slide, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
                 "Migration Platform Architecture",
                 font_size=28, bold=True, color=DARK_BLUE)

    _add_textbox(slide, Inches(0.5), Inches(0.75), Inches(12), Inches(0.4),
                 "8 specialized AI agents orchestrated in a DAG pipeline  •  150 Python modules  •  Zero external dependencies for core",
                 font_size=13, color=MEDIUM_GRAY)

    # ── Source platforms ──
    _add_textbox(slide, Inches(0.3), Inches(1.4), Inches(2), Inches(0.35),
                 "SOURCE PLATFORMS", font_size=12, bold=True, color=MEDIUM_GRAY)
    sources = ["Oracle Analytics Cloud", "Oracle Exadata", "Tableau", "IBM Cognos",
               "Qlik Sense", "Essbase"]
    sy = Inches(1.8)
    for src in sources:
        s = _add_shape(slide, Inches(0.3), sy, Inches(2.2), Inches(0.35),
                       MICROSOFT_BLUE, MSO_SHAPE.ROUNDED_RECTANGLE)
        s.text_frame.paragraphs[0].text = src
        s.text_frame.paragraphs[0].font.size = Pt(10)
        s.text_frame.paragraphs[0].font.color.rgb = WHITE
        s.text_frame.paragraphs[0].font.name = "Segoe UI"
        s.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        sy += Inches(0.4)

    # ── Arrow ──
    _add_textbox(slide, Inches(2.7), Inches(2.8), Inches(0.5), Inches(0.5),
                 "→", font_size=30, bold=True, color=ACCENT_GREEN,
                 alignment=PP_ALIGN.CENTER)

    # ── Agent pipeline (center) ──
    _add_textbox(slide, Inches(3.3), Inches(1.4), Inches(3.5), Inches(0.35),
                 "8-AGENT PIPELINE", font_size=12, bold=True, color=MEDIUM_GRAY)
    agents = [
        ("01 Discovery", MICROSOFT_BLUE),
        ("02 Schema", ACCENT_GREEN),
        ("03 ETL", ACCENT_ORANGE),
        ("04 Semantic Model", ACCENT_TEAL),
        ("05 Report", ACCENT_PURPLE),
        ("06 Security", ACCENT_RED),
        ("07 Validation", RGBColor(0x88, 0x88, 0x00)),
        ("08 Orchestrator", DARK_BLUE),
    ]
    ay = Inches(1.8)
    for name, color in agents:
        a = _add_shape(slide, Inches(3.5), ay, Inches(2.2), Inches(0.35),
                       color, MSO_SHAPE.ROUNDED_RECTANGLE)
        a.text_frame.paragraphs[0].text = name
        a.text_frame.paragraphs[0].font.size = Pt(10)
        a.text_frame.paragraphs[0].font.color.rgb = WHITE
        a.text_frame.paragraphs[0].font.name = "Segoe UI"
        a.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        ay += Inches(0.4)

    # ── Arrow ──
    _add_textbox(slide, Inches(5.9), Inches(2.8), Inches(0.5), Inches(0.5),
                 "→", font_size=30, bold=True, color=ACCENT_GREEN,
                 alignment=PP_ALIGN.CENTER)

    # ── AI translation engine (center-right) ──
    _add_textbox(slide, Inches(6.5), Inches(1.4), Inches(3), Inches(0.35),
                 "AI TRANSLATION ENGINE", font_size=12, bold=True, color=MEDIUM_GRAY)
    translations = [
        "Oracle DDL → Delta Tables",
        "PL/SQL → PySpark",
        "OAC Expressions → DAX (120+ rules)",
        "RPD Model → TMDL",
        "OAC Visuals → PBIR (80+ types)",
        "BI Publisher → Paginated (.rdl)",
        "Session Vars → DAX RLS",
        "Alerts → Data Activator",
    ]
    ty = Inches(1.8)
    for t in translations:
        tb = _add_shape(slide, Inches(6.5), ty, Inches(3.3), Inches(0.35),
                        LIGHT_GRAY, MSO_SHAPE.ROUNDED_RECTANGLE)
        tb.text_frame.paragraphs[0].text = t
        tb.text_frame.paragraphs[0].font.size = Pt(9)
        tb.text_frame.paragraphs[0].font.color.rgb = DARK_BLUE
        tb.text_frame.paragraphs[0].font.name = "Segoe UI"
        tb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        ty += Inches(0.4)

    # ── Arrow ──
    _add_textbox(slide, Inches(10.0), Inches(2.8), Inches(0.5), Inches(0.5),
                 "→", font_size=30, bold=True, color=ACCENT_GREEN,
                 alignment=PP_ALIGN.CENTER)

    # ── Target (right) ──
    _add_textbox(slide, Inches(10.5), Inches(1.4), Inches(2.5), Inches(0.35),
                 "FABRIC TARGETS", font_size=12, bold=True, color=MEDIUM_GRAY)
    targets = [
        ("Fabric Lakehouse", ACCENT_GREEN),
        ("Fabric Warehouse", ACCENT_GREEN),
        ("Fabric Pipelines", ACCENT_GREEN),
        ("TMDL Semantic Model", ACCENT_GREEN),
        ("PBIR Reports", ACCENT_GREEN),
        ("Paginated Reports", ACCENT_GREEN),
        ("Data Activator", ACCENT_GREEN),
        ("Power BI Service", ACCENT_GREEN),
    ]
    ty2 = Inches(1.8)
    for tname, color in targets:
        t = _add_shape(slide, Inches(10.5), ty2, Inches(2.2), Inches(0.35),
                       color, MSO_SHAPE.ROUNDED_RECTANGLE)
        t.text_frame.paragraphs[0].text = tname
        t.text_frame.paragraphs[0].font.size = Pt(10)
        t.text_frame.paragraphs[0].font.color.rgb = WHITE
        t.text_frame.paragraphs[0].font.name = "Segoe UI"
        t.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        ty2 += Inches(0.4)

    # ── Bottom note ──
    _add_shape(slide, Inches(0), Inches(5.8), SLIDE_WIDTH, Inches(0.05),
               MICROSOFT_BLUE, MSO_SHAPE.RECTANGLE)
    _add_textbox(slide, Inches(0.5), Inches(5.95), Inches(12), Inches(1.2),
                 "Key differentiators:  Hybrid rules-first + LLM translation  •  "
                 "Wave-based incremental migration  •  "
                 "Automated rollback  •  "
                 "Real-time migration dashboard  •  "
                 "3,559 automated validation tests  •  "
                 "Direct Lake on OneLake support",
                 font_size=12, color=DARK_BLUE)


def slide_next_steps(prs: Presentation):
    """Slide 7: Next Steps / Call to Action."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, DARK_BLUE)

    _add_textbox(slide, Inches(1), Inches(0.8), Inches(11), Inches(0.8),
                 "Next Steps",
                 font_size=36, bold=True, color=WHITE, alignment=PP_ALIGN.CENTER)

    steps = [
        ("1", "Discovery Workshop", "Run automated inventory against your OAC environment\nto produce a complete asset catalog and complexity assessment.", MICROSOFT_BLUE),
        ("2", "Proof of Concept", "Migrate a representative subset (1 subject area, 5–10 reports)\nto validate fidelity, performance, and ROI assumptions.", ACCENT_GREEN),
        ("3", "Wave Planning", "Use complexity scoring to plan 3–5 migration waves with\nautomated effort estimates and risk-based sequencing.", ACCENT_ORANGE),
        ("4", "Production Migration", "Execute wave-by-wave with automated validation,\nrollback safety nets, and real-time progress dashboards.", ACCENT_TEAL),
    ]

    sx = Inches(0.5)
    card_w = Inches(2.9)
    for num, title, desc, color in steps:
        # Number circle
        circle = _add_shape(slide, sx + Inches(1.1), Inches(2.0),
                            Inches(0.7), Inches(0.7), color, MSO_SHAPE.OVAL)
        circle.text_frame.paragraphs[0].text = num
        circle.text_frame.paragraphs[0].font.size = Pt(24)
        circle.text_frame.paragraphs[0].font.bold = True
        circle.text_frame.paragraphs[0].font.color.rgb = WHITE
        circle.text_frame.paragraphs[0].font.name = "Segoe UI"
        circle.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

        _add_textbox(slide, sx, Inches(2.9), card_w, Inches(0.4),
                     title, font_size=16, bold=True, color=color,
                     alignment=PP_ALIGN.CENTER)
        _add_textbox(slide, sx, Inches(3.4), card_w, Inches(1.0),
                     desc, font_size=11, color=WHITE,
                     alignment=PP_ALIGN.CENTER)
        sx += card_w + Inches(0.2)

    # Footer
    _add_textbox(slide, Inches(1), Inches(5.5), Inches(11), Inches(0.8),
                 "Ready to start?   Contact us to schedule a Discovery Workshop.",
                 font_size=20, bold=True, color=ACCENT_TEAL,
                 alignment=PP_ALIGN.CENTER)

    _add_textbox(slide, Inches(1), Inches(6.3), Inches(11), Inches(0.5),
                 "v6.0.0  •  62 phases complete  •  150 modules  •  3,559 tests  •  97% OAC coverage  •  MIT License",
                 font_size=12, color=MEDIUM_GRAY, alignment=PP_ALIGN.CENTER)


# ── Main ───────────────────────────────────────────────────────────────

def build_deck(output_path: str) -> str:
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    slide_title(prs)
    slide_migration_matrix(prs)
    slide_what_can_be_migrated(prs)
    slide_time_savings(prs)
    slide_roi(prs)
    slide_platform_architecture(prs)
    slide_next_steps(prs)

    prs.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate OAC→Fabric Business Migration ROI deck")
    parser.add_argument("--output", "-o", default="output/OAC_to_Fabric_Business_Deck.pptx",
                        help="Output .pptx path (default: output/OAC_to_Fabric_Business_Deck.pptx)")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    path = build_deck(args.output)
    print(f"✅ Business deck generated: {path}")
    print(f"   7 slides • widescreen 16:9 • {os.path.getsize(path):,} bytes")


if __name__ == "__main__":
    main()
