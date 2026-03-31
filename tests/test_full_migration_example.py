"""Tests for the full migration example and HTML report generation.

Covers:
  - Discovery (all 5 connectors)
  - Schema DDL generation
  - Semantic model (TMDL) generation
  - Visual mapping & PBIR generation
  - Prompt → slicer conversion
  - Security role mapping
  - ETL step mapping
  - Validation agent
  - HTML report generation
  - Markdown report generation
  - MigrationResult summary
  - End-to-end pipeline
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from examples.full_migration_example import (
    MigrationResult,
    _build_markdown_summary,
    _parse_cognos,
    _parse_essbase,
    _parse_oac,
    _parse_qlik,
    _parse_tableau,
    build_semantic_model,
    convert_prompts,
    discover_all,
    generate_report,
    generate_schema,
    map_etl,
    map_security,
    map_visuals,
    run_full_migration,
    run_validation,
)
from src.core.models import AssetType, InventoryItem

EXAMPLES_DIR = PROJECT_ROOT / "examples"
OAC_SIMPLE = EXAMPLES_DIR / "oac_samples" / "simple_sales.xml"
OAC_COMPLEX = EXAMPLES_DIR / "oac_samples" / "complex_enterprise.xml"
ESSBASE_SIMPLE = EXAMPLES_DIR / "essbase_samples" / "simple_budget.xml"
COGNOS_SIMPLE = EXAMPLES_DIR / "cognos_samples" / "simple_list_report.xml"
COGNOS_COMPLEX = EXAMPLES_DIR / "cognos_samples" / "complex_dashboard.xml"
QLIK_SIMPLE = EXAMPLES_DIR / "qlik_samples" / "simple_load.qvs"
QLIK_COMPLEX = EXAMPLES_DIR / "qlik_samples" / "complex_pipeline.qvs"
TABLEAU_SIMPLE = EXAMPLES_DIR / "tableau_samples" / "simple_chart.twb"
TABLEAU_COMPLEX = EXAMPLES_DIR / "tableau_samples" / "complex_enterprise.twb"


# ═══════════════════════════════════════════════════════════════════════
# Discovery tests (one per connector)
# ═══════════════════════════════════════════════════════════════════════


class TestOACDiscovery(unittest.TestCase):
    def test_simple_sales_produces_items(self):
        items = _parse_oac(OAC_SIMPLE)
        self.assertGreater(len(items), 0)

    def test_complex_enterprise_all_asset_types(self):
        items = _parse_oac(OAC_COMPLEX)
        types = {i.asset_type for i in items}
        self.assertIn(AssetType.PHYSICAL_TABLE, types)
        self.assertIn(AssetType.LOGICAL_TABLE, types)

    def test_oac_items_have_source_rpd(self):
        items = _parse_oac(OAC_SIMPLE)
        for item in items:
            self.assertEqual(item.source, "rpd")

    def test_complex_enterprise_has_security_roles(self):
        items = _parse_oac(OAC_COMPLEX)
        roles = [i for i in items if i.asset_type == AssetType.SECURITY_ROLE]
        self.assertGreater(len(roles), 0)


class TestEssbaseDiscovery(unittest.TestCase):
    def test_simple_budget(self):
        items = _parse_essbase(ESSBASE_SIMPLE)
        self.assertGreater(len(items), 0)

    def test_items_are_logical_tables(self):
        items = _parse_essbase(ESSBASE_SIMPLE)
        for item in items:
            self.assertEqual(item.asset_type, AssetType.LOGICAL_TABLE)
            self.assertEqual(item.source, "essbase")

    def test_dimensions_have_members(self):
        items = _parse_essbase(ESSBASE_SIMPLE)
        for item in items:
            self.assertIn("members", item.metadata)


class TestCognosDiscovery(unittest.TestCase):
    def test_simple_list_report(self):
        items = _parse_cognos(COGNOS_SIMPLE)
        self.assertGreater(len(items), 0)

    def test_complex_has_visuals(self):
        items = _parse_cognos(COGNOS_COMPLEX)
        analyses = [i for i in items if i.asset_type == AssetType.ANALYSIS]
        self.assertGreater(len(analyses), 0)

    def test_complex_has_prompts(self):
        items = _parse_cognos(COGNOS_COMPLEX)
        prompts = [i for i in items if i.asset_type == AssetType.PROMPT]
        self.assertGreater(len(prompts), 0)


class TestQlikDiscovery(unittest.TestCase):
    def test_simple_load(self):
        items = _parse_qlik(QLIK_SIMPLE)
        self.assertGreater(len(items), 0)

    def test_complex_pipeline_tables(self):
        items = _parse_qlik(QLIK_COMPLEX)
        tables = [i for i in items if i.asset_type == AssetType.PHYSICAL_TABLE]
        self.assertGreater(len(tables), 0)

    def test_qlik_source_tag(self):
        items = _parse_qlik(QLIK_SIMPLE)
        for item in items:
            self.assertEqual(item.source, "qlik")


class TestTableauDiscovery(unittest.TestCase):
    def test_simple_chart(self):
        items = _parse_tableau(TABLEAU_SIMPLE)
        self.assertGreater(len(items), 0)

    def test_complex_has_worksheets(self):
        items = _parse_tableau(TABLEAU_COMPLEX)
        ws = [i for i in items if i.asset_type == AssetType.ANALYSIS]
        self.assertGreater(len(ws), 0)

    def test_complex_has_dashboards(self):
        items = _parse_tableau(TABLEAU_COMPLEX)
        dash = [i for i in items if i.asset_type == AssetType.DASHBOARD]
        self.assertGreater(len(dash), 0)

    def test_tableau_source_tag(self):
        items = _parse_tableau(TABLEAU_SIMPLE)
        for item in items:
            self.assertEqual(item.source, "tableau")


class TestDiscoverAll(unittest.TestCase):
    def test_discover_all_samples(self):
        items = discover_all(EXAMPLES_DIR)
        self.assertGreater(len(items), 50)

    def test_discover_all_multiple_sources(self):
        items = discover_all(EXAMPLES_DIR)
        sources = {i.source for i in items}
        self.assertGreaterEqual(len(sources), 4)

    def test_discover_specific_files(self):
        items = discover_all(EXAMPLES_DIR, specific_files=[OAC_SIMPLE])
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertEqual(item.source, "rpd")

    def test_discover_ignores_non_parseable(self):
        items = discover_all(EXAMPLES_DIR, specific_files=[EXAMPLES_DIR / "README.md"])
        self.assertEqual(len(items), 0)


# ═══════════════════════════════════════════════════════════════════════
# Schema DDL tests
# ═══════════════════════════════════════════════════════════════════════


class TestSchemaGeneration(unittest.TestCase):
    def setUp(self):
        self.items = discover_all(EXAMPLES_DIR)

    def test_ddl_generated_for_physical_tables(self):
        ddl = generate_schema(self.items)
        self.assertGreater(len(ddl), 0)

    def test_ddl_entries_have_required_keys(self):
        ddl = generate_schema(self.items)
        for d in ddl:
            self.assertIn("table", d)
            self.assertIn("ddl", d)
            self.assertIn("source", d)

    def test_ddl_contains_create_table(self):
        ddl = generate_schema(self.items)
        for d in ddl:
            self.assertIn("CREATE TABLE", d["ddl"].upper())

    def test_no_ddl_for_logical_tables(self):
        logical_only = [i for i in self.items if i.asset_type == AssetType.LOGICAL_TABLE]
        ddl = generate_schema(logical_only)
        self.assertEqual(len(ddl), 0)


# ═══════════════════════════════════════════════════════════════════════
# Semantic model (TMDL) tests
# ═══════════════════════════════════════════════════════════════════════


class TestSemanticModel(unittest.TestCase):
    def setUp(self):
        self.items = discover_all(EXAMPLES_DIR)

    def test_tmdl_generated(self):
        result = build_semantic_model(self.items)
        self.assertIsNotNone(result)

    def test_tmdl_has_files(self):
        result = build_semantic_model(self.items)
        self.assertGreater(len(result["files"]), 0)

    def test_tmdl_has_translations(self):
        result = build_semantic_model(self.items)
        self.assertGreater(len(result["translation_log"]), 0)

    def test_tmdl_files_contain_model_content(self):
        result = build_semantic_model(self.items)
        all_content = "".join(result["files"].values())
        self.assertGreater(len(all_content), 100)

    def test_empty_items_returns_none(self):
        result = build_semantic_model([])
        self.assertIsNone(result)


# ═══════════════════════════════════════════════════════════════════════
# Visual mapping & PBIR tests
# ═══════════════════════════════════════════════════════════════════════


class TestVisualMapping(unittest.TestCase):
    def setUp(self):
        self.items = discover_all(EXAMPLES_DIR)

    def test_visual_mappings_produced(self):
        mappings, specs = map_visuals(self.items)
        self.assertGreater(len(mappings), 0)

    def test_visual_specs_produced(self):
        mappings, specs = map_visuals(self.items)
        self.assertGreater(len(specs), 0)

    def test_mapping_entries_have_fields(self):
        mappings, _ = map_visuals(self.items)
        for m in mappings:
            self.assertIn("source_type", m)
            self.assertIn("pbi_type", m)
            self.assertIn("count", m)


class TestPromptConversion(unittest.TestCase):
    def setUp(self):
        self.items = discover_all(EXAMPLES_DIR)

    def test_prompts_converted(self):
        entries, slicers = convert_prompts(self.items)
        self.assertGreater(len(entries), 0)

    def test_prompt_entries_have_name(self):
        entries, _ = convert_prompts(self.items)
        for e in entries:
            self.assertIn("name", e)
            self.assertIn("pbi_type", e)


class TestPBIRGeneration(unittest.TestCase):
    def setUp(self):
        self.items = discover_all(EXAMPLES_DIR)
        _, self.slicers = convert_prompts(self.items)

    def test_pbir_generated(self):
        result = generate_report(self.items, self.slicers)
        self.assertIsNotNone(result)

    def test_pbir_has_pages(self):
        result = generate_report(self.items, self.slicers)
        self.assertGreater(result.page_count, 0)

    def test_pbir_has_visuals(self):
        result = generate_report(self.items, self.slicers)
        self.assertGreater(result.visual_count, 0)

    def test_no_pbir_without_analyses(self):
        tables_only = [i for i in self.items if i.asset_type == AssetType.PHYSICAL_TABLE]
        result = generate_report(tables_only, [])
        self.assertIsNone(result)


# ═══════════════════════════════════════════════════════════════════════
# Security tests
# ═══════════════════════════════════════════════════════════════════════


class TestSecurityMapping(unittest.TestCase):
    def setUp(self):
        self.items = discover_all(EXAMPLES_DIR)

    def test_security_roles_mapped(self):
        entries, rls = map_security(self.items)
        self.assertGreater(len(entries), 0)

    def test_security_entry_fields(self):
        entries, _ = map_security(self.items)
        for e in entries:
            self.assertIn("oac_role", e)
            self.assertIn("fabric_role", e)

    def test_no_roles_returns_empty(self):
        no_roles = [i for i in self.items if i.asset_type != AssetType.SECURITY_ROLE]
        entries, rls = map_security(no_roles)
        self.assertEqual(len(entries), 0)
        self.assertEqual(rls, "")


# ═══════════════════════════════════════════════════════════════════════
# ETL tests
# ═══════════════════════════════════════════════════════════════════════


class TestETLMapping(unittest.TestCase):
    def setUp(self):
        self.items = discover_all(EXAMPLES_DIR)

    def test_etl_steps_mapped(self):
        entries = map_etl(self.items)
        self.assertGreater(len(entries), 0)

    def test_etl_entry_fields(self):
        entries = map_etl(self.items)
        for e in entries:
            self.assertIn("step_name", e)
            self.assertIn("fabric_target", e)

    def test_no_physical_tables_returns_empty(self):
        logical_only = [i for i in self.items if i.asset_type == AssetType.LOGICAL_TABLE]
        entries = map_etl(logical_only)
        self.assertEqual(len(entries), 0)


# ═══════════════════════════════════════════════════════════════════════
# Validation tests
# ═══════════════════════════════════════════════════════════════════════


class TestValidation(unittest.TestCase):
    def test_validation_succeeds(self):
        items = discover_all(EXAMPLES_DIR)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(run_validation(items, Path(tmpdir)))
        self.assertIn("succeeded", result)
        self.assertGreaterEqual(result["succeeded"], 0)


# ═══════════════════════════════════════════════════════════════════════
# HTML report tests
# ═══════════════════════════════════════════════════════════════════════


class TestHTMLReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir_obj = tempfile.TemporaryDirectory()
        cls.tmpdir = cls._tmpdir_obj.name
        cls.result = asyncio.run(run_full_migration(
            specific_files=[OAC_SIMPLE],
            output_dir=Path(cls.tmpdir),
        ))
        cls.html = (Path(cls.tmpdir) / "migration_report.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir_obj.cleanup()

    def test_html_report_generated(self):
        self.assertIn("<!DOCTYPE html>", self.html)

    def test_html_report_contains_sections(self):
        self.assertIn("Executive Summary", self.html)
        self.assertIn("Discovery", self.html)
        self.assertIn("Schema Migration", self.html)
        self.assertIn("Semantic Model", self.html)
        self.assertIn("Validation", self.html)

    def test_html_report_has_dark_mode_toggle(self):
        self.assertIn("themeToggle", self.html)

    def test_html_report_has_stats(self):
        self.assertIn("stat-card", self.html)
        self.assertIn("Assets Discovered", self.html)

    def test_html_report_self_contained(self):
        self.assertNotIn('<link rel="stylesheet"', self.html)
        self.assertNotIn('<script src=', self.html)
        self.assertIn("<style>", self.html)

    def test_html_report_contains_svg_charts(self):
        self.assertIn("<svg", self.html)


class TestMarkdownReport(unittest.TestCase):
    def test_markdown_report_generated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(run_full_migration(
                specific_files=[OAC_SIMPLE],
                output_dir=Path(tmpdir),
            ))
            md = Path(result.md_report_path).read_text(encoding="utf-8")
            self.assertIn("# Migration Report", md)
            self.assertIn("Assets discovered", md)


# ═══════════════════════════════════════════════════════════════════════
# MigrationResult tests
# ═══════════════════════════════════════════════════════════════════════


class TestMigrationResult(unittest.TestCase):
    def test_summary_contains_key_metrics(self):
        r = MigrationResult(
            items=[],
            by_source={"rpd": 5, "qlik": 3},
            ddl_results=[{"table": "t1", "ddl": "CREATE TABLE", "source": "rpd"}],
            tmdl_files={"model.tmdl": "content"},
            translations=[{"original": "x", "dax": "y", "confidence": 0.9, "method": "rule"}],
            visual_mappings=[],
            prompt_mappings=[],
            security_mappings=[],
            etl_mappings=[],
            elapsed_seconds=1.23,
            html_report_path="/tmp/report.html",
        )
        s = r.summary()
        self.assertIn("1.2s", s)
        self.assertIn("DDL tables", s)
        self.assertIn("TMDL files", s)

    def test_empty_result_summary(self):
        r = MigrationResult()
        s = r.summary()
        self.assertIn("Migration complete", s)


class TestBuildMarkdownSummary(unittest.TestCase):
    def test_builds_valid_markdown(self):
        r = MigrationResult(
            items=[],
            by_source={"rpd": 10},
            by_type={"physicalTable": 5, "logicalTable": 5},
            ddl_results=[],
            tmdl_files={},
            translations=[],
            visual_mappings=[],
            prompt_mappings=[],
            security_mappings=[],
            etl_mappings=[],
            elapsed_seconds=0.5,
        )
        md = _build_markdown_summary(r)
        self.assertIn("# Migration Report", md)
        self.assertIn("rpd", md)
        self.assertIn("physicalTable", md)


# ═══════════════════════════════════════════════════════════════════════
# End-to-end pipeline tests
# ═══════════════════════════════════════════════════════════════════════


class TestEndToEndPipeline(unittest.TestCase):
    """Run the full pipeline against a single OAC sample."""

    def test_full_pipeline_single_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(run_full_migration(
                specific_files=[OAC_SIMPLE],
                output_dir=Path(tmpdir),
            ))
            self.assertGreater(len(result.items), 0)
            self.assertGreater(len(result.ddl_results), 0)
            self.assertGreater(len(result.tmdl_files), 0)
            self.assertGreater(result.elapsed_seconds, 0)
            self.assertTrue(Path(result.html_report_path).exists())

    def test_full_pipeline_complex_enterprise(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(run_full_migration(
                specific_files=[OAC_COMPLEX],
                output_dir=Path(tmpdir),
            ))
            self.assertGreater(len(result.items), 20)
            self.assertGreater(len(result.security_mappings), 0)
            self.assertGreater(len(result.translations), 0)

    def test_full_pipeline_all_connectors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(run_full_migration(
                output_dir=Path(tmpdir),
            ))
            # Should discover from at least 4 different sources
            self.assertGreaterEqual(len(result.by_source), 4)
            self.assertGreater(len(result.items), 100)
            # All pipeline outputs should exist
            self.assertGreater(len(result.ddl_results), 0)
            self.assertGreater(len(result.tmdl_files), 0)
            self.assertGreater(len(result.visual_mappings), 0)
            self.assertGreater(len(result.etl_mappings), 0)
            self.assertGreater(len(result.prompt_mappings), 0)
            # Reports generated
            self.assertTrue(Path(result.html_report_path).exists())
            self.assertTrue(Path(result.md_report_path).exists())

    def test_output_directory_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "nested" / "output"
            result = asyncio.run(run_full_migration(
                specific_files=[OAC_SIMPLE],
                output_dir=out,
            ))
            self.assertTrue(out.exists())

    def test_output_artifacts_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(run_full_migration(
                specific_files=[OAC_COMPLEX],
                output_dir=Path(tmpdir),
            ))
            # DDL file
            self.assertTrue((Path(tmpdir) / "generated_ddl.sql").exists())
            # TMDL directory
            self.assertTrue((Path(tmpdir) / "SemanticModel").exists())
            # HTML report
            self.assertTrue((Path(tmpdir) / "migration_report.html").exists())
            # Markdown report
            self.assertTrue((Path(tmpdir) / "migration_report.md").exists())

    def test_output_artifacts_with_all_connectors(self):
        """All connectors together produce PBIR output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = asyncio.run(run_full_migration(
                output_dir=Path(tmpdir),
            ))
            # With all connectors, PBIR should be generated (Cognos/Tableau have visuals)
            self.assertTrue((Path(tmpdir) / "PBIR").exists())


class TestHTMLReportContent(unittest.TestCase):
    """Detailed HTML report content validation."""

    @classmethod
    def setUpClass(cls):
        cls._tmpdir_obj = tempfile.TemporaryDirectory()
        cls.tmpdir = cls._tmpdir_obj.name
        cls.result = asyncio.run(run_full_migration(
            output_dir=Path(cls.tmpdir),
        ))
        cls.html = (Path(cls.tmpdir) / "migration_report.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir_obj.cleanup()

    def test_html_is_valid_structure(self):
        self.assertIn("<!DOCTYPE html>", self.html)
        self.assertIn("<html", self.html)
        self.assertIn("</html>", self.html)

    def test_has_all_8_sections(self):
        self.assertIn('id="executive-summary"', self.html)
        self.assertIn('id="discovery"', self.html)
        self.assertIn('id="schema"', self.html)
        self.assertIn('id="semantic"', self.html)
        self.assertIn('id="reports"', self.html)
        self.assertIn('id="security"', self.html)
        self.assertIn('id="etl"', self.html)
        self.assertIn('id="validation"', self.html)

    def test_has_table_of_contents(self):
        self.assertIn("toc-grid", self.html)

    def test_donut_charts_present(self):
        # SVG donut + legend
        self.assertIn("<svg", self.html)
        self.assertIn("legend", self.html)

    def test_stat_cards_present(self):
        self.assertIn("stat-card", self.html)

    def test_css_embedded(self):
        self.assertIn("<style>", self.html)
        self.assertIn("--bg-primary", self.html)

    def test_js_embedded(self):
        self.assertIn("<script>", self.html)
        self.assertIn("themeToggle", self.html)

    def test_no_external_resources(self):
        self.assertNotIn('href="http', self.html)
        self.assertNotIn('<link rel="stylesheet" href', self.html)
        self.assertNotIn('<script src="http', self.html)

    def test_print_styles(self):
        self.assertIn("@media print", self.html)

    def test_responsive_styles(self):
        self.assertIn("@media (max-width", self.html)

    def test_source_platforms_mentioned(self):
        # Should mention at least some source platforms
        any_source = any(s in self.html for s in ["rpd", "essbase", "cognos", "qlik", "tableau"])
        self.assertTrue(any_source)

    def test_confidence_indicators(self):
        self.assertIn("conf-", self.html)

    def test_badge_styles(self):
        self.assertIn("badge", self.html)


if __name__ == "__main__":
    unittest.main()
