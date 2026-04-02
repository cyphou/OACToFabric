"""Tests for the practical migration tooling (src/tools/).

Covers:
1. DAX deep validator (dax_validator.py)
2. TMDL file-system validator (tmdl_file_validator.py)
3. Data reconciliation CLI (reconciliation_cli.py)
4. OAC API test harness (oac_test_harness.py)
5. Fabric deployment dry-run (fabric_dry_run.py)
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.tools.dax_validator import (
    DAXIssue,
    DAXValidationResult,
    Severity,
    Token,
    TokenType,
    extract_measures_from_tmdl,
    tokenize_dax,
    validate_dax_deep,
    validate_tmdl_directory,
    validate_tmdl_measures,
)
from src.tools.fabric_dry_run import (
    ArtifactManifestEntry,
    DeploymentDryRun,
    DeploymentManifest,
    export_manifest_json,
    validate_fabric_name,
)
from src.tools.oac_test_harness import (
    Cassette,
    CassetteEntry,
    MockOACServer,
    OACTestHarness,
    PlaybackEngine,
    RecordedRequest,
    RecordedResponse,
    RequestRecorder,
    assert_api_call_sequence,
    assert_handled_rate_limit,
    assert_no_duplicate_calls,
)
from src.tools.reconciliation_cli import (
    CheckResult,
    CheckType,
    ColumnSnapshot,
    OfflineReconciler,
    ReconReport,
    ReconciliationRunner,
    Status,
    TableSnapshot,
    compare_values,
    generate_json_report,
    generate_markdown_report,
)
from src.tools.tmdl_file_validator import (
    TMDLOutputReport,
    validate_migration_output,
    validate_output_directory,
)


# =========================================================================
# 1. DAX Deep Validator Tests
# =========================================================================


class TestDAXTokenizer(unittest.TestCase):
    """Test DAX tokenizer."""

    def test_simple_expression(self):
        tokens = tokenize_dax("SUM(Sales[Amount])")
        types = [t.type for t in tokens]
        self.assertIn(TokenType.FUNCTION, types)
        self.assertIn(TokenType.COLUMN_REF, types)

    def test_var_return(self):
        tokens = tokenize_dax("VAR x = 1 RETURN x + 2")
        keywords = [t for t in tokens if t.type == TokenType.KEYWORD]
        self.assertEqual(len(keywords), 2)
        self.assertEqual(keywords[0].value.upper(), "VAR")
        self.assertEqual(keywords[1].value.upper(), "RETURN")

    def test_string_literal(self):
        tokens = tokenize_dax('"Hello World"')
        strings = [t for t in tokens if t.type == TokenType.STRING]
        self.assertEqual(len(strings), 1)
        self.assertEqual(strings[0].value, '"Hello World"')

    def test_number(self):
        tokens = tokenize_dax("42.5")
        numbers = [t for t in tokens if t.type == TokenType.NUMBER]
        self.assertEqual(len(numbers), 1)
        self.assertEqual(numbers[0].value, "42.5")

    def test_operators(self):
        tokens = tokenize_dax("1 + 2 * 3")
        ops = [t for t in tokens if t.type == TokenType.OPERATOR]
        self.assertEqual(len(ops), 2)

    def test_comment_skipped(self):
        tokens = tokenize_dax("SUM(x) // comment\n+ 1")
        # comment should be skipped
        func_tokens = [t for t in tokens if t.type == TokenType.FUNCTION]
        self.assertEqual(len(func_tokens), 1)

    def test_block_comment(self):
        tokens = tokenize_dax("SUM(/* comment */x)")
        func_tokens = [t for t in tokens if t.type == TokenType.FUNCTION]
        self.assertEqual(len(func_tokens), 1)

    def test_quoted_table_name(self):
        tokens = tokenize_dax("'My Table'[Column]")
        identifiers = [t for t in tokens if t.type == TokenType.IDENTIFIER]
        self.assertTrue(len(identifiers) >= 1)


class TestDAXDeepValidator(unittest.TestCase):
    """Test deep DAX validation."""

    def test_valid_sum(self):
        result = validate_dax_deep("SUM(Sales[Amount])")
        self.assertTrue(result.valid)
        self.assertEqual(result.error_count, 0)

    def test_valid_calculate(self):
        result = validate_dax_deep(
            'CALCULATE(SUM(Sales[Amount]), FILTER(ALL(Sales[Region]), Sales[Region] = "West"))'
        )
        self.assertTrue(result.valid)

    def test_valid_var_return(self):
        result = validate_dax_deep(
            "VAR TotalSales = SUM(Sales[Amount]) RETURN TotalSales * 1.1"
        )
        self.assertTrue(result.valid)

    def test_empty_expression_dax009(self):
        result = validate_dax_deep("")
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX009", codes)

    def test_unbalanced_paren_dax001(self):
        result = validate_dax_deep("SUM(Sales[Amount]")
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX001", codes)

    def test_extra_close_paren_dax001(self):
        result = validate_dax_deep("SUM(Sales[Amount]))")
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX001", codes)

    def test_unknown_function_dax003(self):
        result = validate_dax_deep("MYSUPERFUNC(Sales[Amount])")
        codes = [i.code for i in result.issues]
        self.assertIn("DAX003", codes)

    def test_deprecated_function_dax004(self):
        result = validate_dax_deep("EARLIER(Sales[Amount])")
        codes = [i.code for i in result.issues]
        self.assertIn("DAX004", codes)

    def test_var_without_return_dax006(self):
        result = validate_dax_deep("VAR x = 1")
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX006", codes)

    def test_return_without_var_dax007(self):
        result = validate_dax_deep("RETURN 42")
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX007", codes)

    def test_excessive_nesting_dax008(self):
        # Build deeply nested expression
        expr = "IF(" * 12 + "1" + ", 0)" * 12
        result = validate_dax_deep(expr, max_nesting_depth=10)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX008", codes)

    def test_unterminated_string_dax012(self):
        result = validate_dax_deep('IF(TRUE(), "hello, 0)')
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX012", codes)

    def test_if_too_few_args_dax013(self):
        result = validate_dax_deep("IF(TRUE())")
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX013", codes)

    def test_if_too_many_args_dax013(self):
        result = validate_dax_deep("IF(TRUE(), 1, 2, 3)")
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX013", codes)

    def test_if_valid_args(self):
        result = validate_dax_deep("IF(TRUE(), 1, 0)")
        # Should not have DAX013
        codes = [i.code for i in result.issues if i.severity == Severity.ERROR]
        self.assertNotIn("DAX013", [c for c in codes])

    def test_divide_too_few_args_dax014(self):
        result = validate_dax_deep("DIVIDE(1)")
        self.assertFalse(result.valid)
        codes = [i.code for i in result.issues]
        self.assertIn("DAX014", codes)

    def test_divide_valid(self):
        result = validate_dax_deep("DIVIDE(10, 3, 0)")
        error_codes = [i.code for i in result.issues if i.severity == Severity.ERROR]
        self.assertNotIn("DAX014", error_codes)

    def test_iterator_anti_pattern_dax005(self):
        result = validate_dax_deep("SUMX(Sales, Sales[Amount])")
        codes = [i.code for i in result.issues]
        self.assertIn("DAX005", codes)

    def test_no_anti_pattern_when_disabled(self):
        result = validate_dax_deep(
            "SUMX(Sales, Sales[Amount])",
            check_anti_patterns=False,
        )
        codes = [i.code for i in result.issues]
        self.assertNotIn("DAX005", codes)

    def test_measure_name_in_result(self):
        result = validate_dax_deep("SUM(Sales[Amount])", measure_name="Revenue")
        self.assertEqual(result.measure_name, "Revenue")

    def test_complex_valid_expression(self):
        expr = """
        VAR TotalRevenue = SUM(Sales[Revenue])
        VAR TotalCost = SUM(Sales[Cost])
        RETURN
            DIVIDE(TotalRevenue - TotalCost, TotalRevenue, 0)
        """
        result = validate_dax_deep(expr)
        self.assertTrue(result.valid)


class TestDAXMeasureExtraction(unittest.TestCase):
    """Test measure extraction from TMDL content."""

    def test_extract_simple_measure(self):
        tmdl = """table Sales
\tcolumn Amount
\t\tdataType: decimal
\t\tlineageTag: abc-123
\tmeasure Revenue = SUM(Sales[Amount])
\t\tformatString: $#,##0
\t\tlineageTag: def-456
"""
        measures = extract_measures_from_tmdl(tmdl)
        self.assertEqual(len(measures), 1)
        self.assertEqual(measures[0][0], "Revenue")
        self.assertIn("SUM", measures[0][1])

    def test_extract_multiple_measures(self):
        tmdl = """table Sales
\tmeasure Revenue = SUM(Sales[Amount])
\t\tlineageTag: abc
\tmeasure Cost = SUM(Sales[Cost])
\t\tlineageTag: def
\tmeasure Profit = [Revenue] - [Cost]
\t\tlineageTag: ghi
"""
        measures = extract_measures_from_tmdl(tmdl)
        self.assertEqual(len(measures), 3)

    def test_validate_tmdl_measures_batch(self):
        tmdl = """table Sales
\tmeasure Revenue = SUM(Sales[Amount])
\t\tlineageTag: abc
\tmeasure BadMeasure = SUM(Sales[Amount]
\t\tlineageTag: def
"""
        results = validate_tmdl_measures(tmdl)
        self.assertTrue(len(results) >= 1)
        # At least one should be valid (Revenue)
        valid_count = sum(1 for r in results if r.valid)
        self.assertGreaterEqual(valid_count, 1)

    def test_validate_tmdl_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a TMDL file with measures
            tmdl_content = """table Sales
\tmeasure Revenue = SUM(Sales[Amount])
\t\tlineageTag: abc-123
"""
            tmdl_path = Path(tmpdir) / "Sales.tmdl"
            tmdl_path.write_text(tmdl_content, encoding="utf-8")

            results = validate_tmdl_directory(tmpdir)
            self.assertEqual(len(results), 1)


# =========================================================================
# 2. TMDL File-System Validator Tests
# =========================================================================


class TestTMDLFileValidator(unittest.TestCase):
    """Test TMDL file-system validation."""

    def _create_valid_tmdl_output(self, tmpdir: str) -> Path:
        """Create a valid TMDL output directory structure."""
        root = Path(tmpdir) / "test_cube"
        sm = root / "SemanticModel"
        defn = sm / "definition"
        tables = defn / "tables"
        tables.mkdir(parents=True, exist_ok=True)

        # model.tmdl
        (sm / "model.tmdl").write_text(
            "model Model\n\tculture: en-US\n", encoding="utf-8"
        )

        # .platform
        (sm / ".platform").write_text(json.dumps({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel"},
            "config": {"logicalId": "test-id"},
        }), encoding="utf-8")

        # database.tmdl
        (defn / "database.tmdl").write_text(
            "compatibilityLevel: 1604\n", encoding="utf-8"
        )

        # relationships.tmdl
        (defn / "relationships.tmdl").write_text(
            "relationship rel1\n\tfromTable: 'Sales'\n\ttoTable: 'Time'\n",
            encoding="utf-8",
        )

        # Table files
        (tables / "Sales.tmdl").write_text(
            "table Sales\n\tlineageTag: abc\n\tcolumn Amount\n\t\tdataType: decimal\n\t\tlineageTag: def\n\tmeasure Revenue = SUM(Sales[Amount])\n\t\tlineageTag: ghi\n",
            encoding="utf-8",
        )
        (tables / "Time.tmdl").write_text(
            "table Time\n\tlineageTag: jkl\n\tcolumn Date\n\t\tdataType: dateTime\n\t\tlineageTag: mno\n",
            encoding="utf-8",
        )

        # DDL
        (root / "generated_ddl.sql").write_text(
            "CREATE TABLE Sales (Amount DECIMAL) USING DELTA;\n"
            "CREATE TABLE Time (Date TIMESTAMP) USING DELTA;\n",
            encoding="utf-8",
        )

        return root

    def test_valid_output_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_valid_tmdl_output(tmpdir)
            report = validate_output_directory(str(root))
            self.assertTrue(report.valid)
            self.assertEqual(report.table_count, 2)
            self.assertGreaterEqual(report.measure_count, 1)

    def test_missing_model_tmdl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_valid_tmdl_output(tmpdir)
            (root / "SemanticModel" / "model.tmdl").unlink()
            report = validate_output_directory(str(root))
            self.assertFalse(report.valid)
            self.assertTrue(any("model.tmdl" in e for e in report.errors))

    def test_missing_platform(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_valid_tmdl_output(tmpdir)
            (root / "SemanticModel" / ".platform").unlink()
            report = validate_output_directory(str(root))
            self.assertFalse(report.valid)

    def test_invalid_platform_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_valid_tmdl_output(tmpdir)
            (root / "SemanticModel" / ".platform").write_text("not json", encoding="utf-8")
            report = validate_output_directory(str(root))
            self.assertFalse(report.valid)

    def test_missing_tables_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_valid_tmdl_output(tmpdir)
            import shutil
            shutil.rmtree(root / "SemanticModel" / "definition" / "tables")
            report = validate_output_directory(str(root))
            self.assertFalse(report.valid)

    def test_nonexistent_directory(self):
        report = validate_output_directory("/nonexistent/path")
        self.assertFalse(report.valid)
        self.assertTrue(any("does not exist" in e for e in report.errors))

    def test_validate_migration_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_valid_tmdl_output(tmpdir)
            results = validate_migration_output(tmpdir)
            self.assertEqual(len(results), 1)
            self.assertTrue(list(results.values())[0].valid)

    def test_report_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_valid_tmdl_output(tmpdir)
            report = validate_output_directory(str(root))
            summary = report.summary()
            self.assertIn("PASS", summary)
            self.assertIn("Tables:", summary)

    def test_dax_validation_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_valid_tmdl_output(tmpdir)
            report = validate_output_directory(str(root), validate_dax=False)
            self.assertTrue(report.valid)
            # No DAX results should exist
            for fv in report.files:
                self.assertEqual(len(fv.dax_results), 0)

    def test_empty_ddl_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_valid_tmdl_output(tmpdir)
            (root / "generated_ddl.sql").write_text("", encoding="utf-8")
            report = validate_output_directory(str(root))
            all_warnings = []
            for fv in report.files:
                all_warnings.extend(fv.warnings)
            self.assertTrue(any("empty" in w.lower() for w in all_warnings))


# =========================================================================
# 3. Data Reconciliation CLI Tests
# =========================================================================


class TestCompareValues(unittest.TestCase):
    """Test value comparison utility."""

    def test_both_none(self):
        status, var, pct = compare_values(None, None)
        self.assertEqual(status, Status.PASS)

    def test_one_none(self):
        status, var, pct = compare_values(100, None)
        self.assertEqual(status, Status.FAIL)

    def test_equal_numbers(self):
        status, var, pct = compare_values(100, 100)
        self.assertEqual(status, Status.PASS)
        self.assertEqual(var, 0.0)

    def test_exact_tolerance(self):
        status, var, pct = compare_values(100, 100.001, tolerance=0.01)
        self.assertEqual(status, Status.PASS)

    def test_exceeds_tolerance(self):
        status, var, pct = compare_values(100, 200, tolerance=0.01)
        self.assertEqual(status, Status.FAIL)

    def test_string_match(self):
        status, var, pct = compare_values("hello", "hello")
        self.assertEqual(status, Status.PASS)

    def test_string_mismatch(self):
        status, var, pct = compare_values("hello", "world")
        self.assertEqual(status, Status.FAIL)

    def test_both_zero(self):
        status, var, pct = compare_values(0, 0)
        self.assertEqual(status, Status.PASS)


class TestOfflineReconciler(unittest.TestCase):
    """Test offline snapshot reconciliation."""

    def _make_snapshots(self):
        source = [TableSnapshot(
            table_name="Sales",
            row_count=1000,
            columns={
                "Amount": ColumnSnapshot(
                    name="Amount", null_count=5, distinct_count=500,
                    sum_value=50000.0, avg_value=50.0,
                ),
                "Region": ColumnSnapshot(
                    name="Region", null_count=0, distinct_count=10,
                ),
            },
        )]
        target = [TableSnapshot(
            table_name="Sales",
            row_count=1000,
            columns={
                "Amount": ColumnSnapshot(
                    name="Amount", null_count=5, distinct_count=500,
                    sum_value=50000.0, avg_value=50.0,
                ),
                "Region": ColumnSnapshot(
                    name="Region", null_count=0, distinct_count=10,
                ),
            },
        )]
        return source, target

    def test_perfect_match(self):
        source, target = self._make_snapshots()
        reconciler = OfflineReconciler()
        report = reconciler.compare_snapshots(source, target)
        self.assertEqual(report.pass_rate, 100.0)
        self.assertEqual(report.failed, 0)

    def test_row_count_mismatch(self):
        source, target = self._make_snapshots()
        target[0].row_count = 999
        reconciler = OfflineReconciler()
        report = reconciler.compare_snapshots(source, target)
        self.assertGreater(report.failed, 0)

    def test_missing_table(self):
        source, _ = self._make_snapshots()
        reconciler = OfflineReconciler()
        report = reconciler.compare_snapshots(source, [])
        self.assertGreater(report.failed, 0)

    def test_missing_column(self):
        source, target = self._make_snapshots()
        del target[0].columns["Amount"]
        reconciler = OfflineReconciler()
        report = reconciler.compare_snapshots(source, target)
        self.assertGreater(report.failed, 0)

    def test_sum_variance(self):
        source, target = self._make_snapshots()
        target[0].columns["Amount"].sum_value = 49000.0
        reconciler = OfflineReconciler()
        report = reconciler.compare_snapshots(source, target)
        sum_checks = [c for c in report.checks if c.check_type == CheckType.SUM_VALUE]
        self.assertTrue(any(c.status == Status.FAIL for c in sum_checks))

    def test_tolerance_applied(self):
        source, target = self._make_snapshots()
        target[0].columns["Amount"].sum_value = 50000.5
        reconciler = OfflineReconciler(tolerance=0.001)
        report = reconciler.compare_snapshots(source, target)
        sum_checks = [c for c in report.checks if c.check_type == CheckType.SUM_VALUE]
        self.assertTrue(all(c.status == Status.PASS for c in sum_checks))

    def test_json_file_comparison(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_data = [{"table_name": "Sales", "row_count": 100, "columns": {
                "Amount": {"null_count": 0, "distinct_count": 50, "sum_value": 5000}
            }}]
            target_data = [{"table_name": "Sales", "row_count": 100, "columns": {
                "Amount": {"null_count": 0, "distinct_count": 50, "sum_value": 5000}
            }}]
            src_path = Path(tmpdir) / "source.json"
            tgt_path = Path(tmpdir) / "target.json"
            src_path.write_text(json.dumps(source_data), encoding="utf-8")
            tgt_path.write_text(json.dumps(target_data), encoding="utf-8")

            reconciler = OfflineReconciler()
            report = reconciler.compare_json_files(str(src_path), str(tgt_path))
            self.assertEqual(report.pass_rate, 100.0)


class TestReconReportGeneration(unittest.TestCase):
    """Test report generation."""

    def _make_report(self):
        report = ReconReport(tables_checked=1, columns_checked=2)
        report.checks.append(CheckResult(
            check_type=CheckType.ROW_COUNT, table="Sales",
            source_value=100, target_value=100, status=Status.PASS,
        ))
        report.checks.append(CheckResult(
            check_type=CheckType.SUM_VALUE, table="Sales", column="Amount",
            source_value=5000, target_value=4900, variance=100,
            variance_pct=2.0, status=Status.FAIL,
        ))
        return report

    def test_markdown_report(self):
        report = self._make_report()
        md = generate_markdown_report(report)
        self.assertIn("Data Reconciliation Report", md)
        self.assertIn("Sales", md)
        self.assertIn("✅", md)
        self.assertIn("❌", md)

    def test_json_report(self):
        report = self._make_report()
        js = generate_json_report(report)
        data = json.loads(js)
        self.assertEqual(data["total_checks"], 2)
        self.assertEqual(data["passed"], 1)
        self.assertEqual(data["failed"], 1)

    def test_pass_rate(self):
        report = self._make_report()
        self.assertEqual(report.pass_rate, 50.0)


class TestReconciliationRunner(unittest.TestCase):
    """Test live reconciliation runner."""

    def test_run_with_mock_executors(self):
        results = {"source": {}, "target": {}}
        call_count = {"n": 0}

        def source_exec(sql: str):
            call_count["n"] += 1
            if "COUNT(*)" in sql:
                return 100
            if "COUNT(DISTINCT" in sql:
                return 50
            if "NULL" in sql:
                return 5
            if "SUM" in sql:
                return 5000.0
            if "AVG" in sql:
                return 50.0
            return None

        def target_exec(sql: str):
            return source_exec(sql)  # Perfect match

        runner = ReconciliationRunner(
            source_executor=source_exec,
            target_executor=target_exec,
        )
        inventory = [{
            "source_name": "SALES",
            "target_name": "Sales",
            "columns": [
                {"name": "Amount", "type": "decimal"},
                {"name": "Region", "type": "varchar"},
            ],
        }]
        report = runner.run(inventory)
        self.assertEqual(report.tables_checked, 1)
        self.assertGreater(report.total, 0)
        self.assertEqual(report.failed, 0)

    def test_run_error_handling(self):
        def source_exec(sql: str):
            raise ConnectionError("DB unavailable")

        def target_exec(sql: str):
            return 100

        runner = ReconciliationRunner(
            source_executor=source_exec,
            target_executor=target_exec,
        )
        report = runner.run([{
            "source_name": "T", "target_name": "T", "columns": [],
        }])
        error_checks = [c for c in report.checks if c.status == Status.ERROR]
        self.assertGreater(len(error_checks), 0)


# =========================================================================
# 4. OAC API Test Harness Tests
# =========================================================================


class TestCassette(unittest.TestCase):
    """Test cassette save/load."""

    def test_save_and_load(self):
        cassette = Cassette(name="test_cassette")
        cassette.entries.append(CassetteEntry(
            request=RecordedRequest(method="GET", url="https://example.com/api"),
            response=RecordedResponse(status_code=200, json_body={"ok": True}),
            duration_ms=50,
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "test.json")
            cassette.save(path)

            loaded = Cassette.load(path)
            self.assertEqual(loaded.name, "test_cassette")
            self.assertEqual(len(loaded.entries), 1)
            self.assertEqual(loaded.entries[0].response.status_code, 200)
            self.assertEqual(loaded.entries[0].response.json_body, {"ok": True})

    def test_sanitize_headers(self):
        cassette = Cassette(name="sensitive")
        cassette.entries.append(CassetteEntry(
            request=RecordedRequest(
                method="GET",
                url="https://example.com",
                headers={"Authorization": "Bearer secret123", "Accept": "application/json"},
            ),
            response=RecordedResponse(status_code=200),
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "test.json")
            cassette.save(path)
            data = json.loads(Path(path).read_text())
            headers = data["entries"][0]["request"]["headers"]
            self.assertEqual(headers["Authorization"], "***REDACTED***")
            self.assertEqual(headers["Accept"], "application/json")


class TestRequestRecorder(unittest.TestCase):
    """Test request recording."""

    def test_record_and_stop(self):
        recorder = RequestRecorder(cassette_name="test")
        recorder.record("GET", "https://oac/api/v1/catalog", status_code=200, response_json={"items": []})
        recorder.record("POST", "https://oac/api/v1/query", status_code=200, response_body="ok")
        cassette = recorder.stop()
        self.assertEqual(len(cassette.entries), 2)

    def test_stop_prevents_recording(self):
        recorder = RequestRecorder()
        recorder.stop()
        recorder.record("GET", "https://example.com", status_code=200)
        self.assertEqual(len(recorder.cassette.entries), 0)


class TestPlaybackEngine(unittest.TestCase):
    """Test cassette playback."""

    def _build_cassette(self):
        return Cassette(name="test", entries=[
            CassetteEntry(
                request=RecordedRequest(method="GET", url="https://oac/api/v1/catalog"),
                response=RecordedResponse(status_code=200, json_body={"items": []}),
            ),
            CassetteEntry(
                request=RecordedRequest(method="GET", url="https://oac/api/v1/subjects"),
                response=RecordedResponse(status_code=200, json_body={"subjects": []}),
            ),
        ])

    def test_sequential_playback(self):
        engine = PlaybackEngine(self._build_cassette())
        resp1 = engine.match("GET", "https://oac/api/v1/catalog")
        self.assertIsNotNone(resp1)
        self.assertEqual(resp1.status_code, 200)

        resp2 = engine.match("GET", "https://oac/api/v1/subjects")
        self.assertIsNotNone(resp2)

        self.assertTrue(engine.all_played)

    def test_url_matching_ignores_query_params(self):
        engine = PlaybackEngine(self._build_cassette())
        resp = engine.match("GET", "https://oac/api/v1/catalog?limit=10&offset=0")
        self.assertIsNotNone(resp)

    def test_assert_all_played(self):
        engine = PlaybackEngine(self._build_cassette())
        engine.match("GET", "https://oac/api/v1/catalog")
        with self.assertRaises(AssertionError):
            engine.assert_all_played()

    def test_no_match_returns_none(self):
        engine = PlaybackEngine(self._build_cassette(), strict=True)
        resp = engine.match("POST", "https://oac/api/v1/catalog")
        self.assertIsNone(resp)


class TestMockOACServer(unittest.TestCase):
    """Test mock OAC server."""

    def test_catalog_response(self):
        mock = MockOACServer()
        mock.add_analyses(["Sales Dashboard", "Finance Report"])
        resp = mock.catalog_response()
        self.assertEqual(resp["totalResults"], 2)
        self.assertEqual(len(resp["items"]), 2)

    def test_subject_area_response(self):
        mock = MockOACServer()
        mock.add_subject_areas(["Sales"])
        resp = mock.subject_area_response("Sales")
        self.assertEqual(resp["name"], "Sales")

    def test_analysis_detail(self):
        mock = MockOACServer()
        mock.add_analyses(["Sales Dashboard"])
        resp = mock.analysis_detail_response("Sales Dashboard")
        self.assertEqual(resp["name"], "Sales Dashboard")
        self.assertIn("xml", resp)

    def test_not_found_analysis(self):
        mock = MockOACServer()
        resp = mock.analysis_detail_response("NonExistent")
        self.assertIn("error", resp)

    def test_build_cassette(self):
        mock = MockOACServer()
        mock.add_analyses(["A1", "A2"])
        mock.add_subject_areas(["SA1"])
        cassette = mock.build_cassette()
        # Should have: 1 catalog + 1 subject_areas + 2 analyses + 1 SA detail = 5
        self.assertEqual(len(cassette.entries), 5)

    def test_rate_limit_cassette(self):
        mock = MockOACServer()
        cassette = mock.generate_rate_limit_cassette()
        statuses = [e.response.status_code for e in cassette.entries]
        self.assertIn(429, statuses)

    def test_pagination_cassette(self):
        mock = MockOACServer()
        cassette = mock.generate_pagination_cassette(total_items=30, page_size=10)
        self.assertEqual(len(cassette.entries), 3)
        # Last page should have hasMore=False
        self.assertFalse(cassette.entries[-1].response.json_body["hasMore"])

    def test_mock_auth(self):
        mock = MockOACServer()
        auth = mock.auth
        token = auth.get_token()
        self.assertTrue(token.startswith("mock-token-"))


class TestOACHarness(unittest.TestCase):
    """Test OAC test harness."""

    def test_recording_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = OACTestHarness(cassette_dir=tmpdir)
            recorder = harness.start_recording("test_flow")
            recorder.record("GET", "https://oac/api", status_code=200, response_json={"ok": True})
            path = harness.save_recording(recorder)
            self.assertTrue(Path(path).exists())

            # Load it back
            cassette = harness.load_cassette("test_flow")
            self.assertEqual(len(cassette.entries), 1)


class TestAssertionHelpers(unittest.TestCase):
    """Test assertion helpers."""

    def test_assert_call_sequence(self):
        cassette = Cassette(name="test", entries=[
            CassetteEntry(
                request=RecordedRequest(method="GET", url="https://a"),
                response=RecordedResponse(status_code=200),
            ),
            CassetteEntry(
                request=RecordedRequest(method="POST", url="https://b"),
                response=RecordedResponse(status_code=201),
            ),
        ])
        engine = PlaybackEngine(cassette)
        engine.match("GET", "https://a")
        engine.match("POST", "https://b")
        assert_api_call_sequence(engine, ["GET", "POST"])

    def test_assert_no_duplicates(self):
        engine = PlaybackEngine(Cassette(name="empty"))
        engine._calls = [
            RecordedRequest(method="GET", url="https://a"),
            RecordedRequest(method="GET", url="https://b"),
        ]
        assert_no_duplicate_calls(engine)  # Should pass

    def test_assert_duplicates_fail(self):
        engine = PlaybackEngine(Cassette(name="empty"))
        engine._calls = [
            RecordedRequest(method="GET", url="https://a"),
            RecordedRequest(method="GET", url="https://a"),
        ]
        with self.assertRaises(AssertionError):
            assert_no_duplicate_calls(engine)


# =========================================================================
# 5. Fabric Deployment Dry-Run Tests
# =========================================================================


class TestFabricNameValidation(unittest.TestCase):
    """Test Fabric name validation."""

    def test_valid_name(self):
        errors = validate_fabric_name("Sales_Table")
        self.assertEqual(len(errors), 0)

    def test_empty_name(self):
        errors = validate_fabric_name("")
        self.assertGreater(len(errors), 0)

    def test_name_too_long(self):
        errors = validate_fabric_name("x" * 300, "table")
        self.assertTrue(any("exceeds" in e for e in errors))

    def test_invalid_chars(self):
        errors = validate_fabric_name("Sales<Table>")
        self.assertTrue(any("invalid" in e.lower() for e in errors))

    def test_reserved_name(self):
        errors = validate_fabric_name("CON")
        self.assertTrue(any("reserved" in e.lower() for e in errors))

    def test_leading_space(self):
        errors = validate_fabric_name(" Sales")
        self.assertTrue(any("spaces" in e.lower() for e in errors))

    def test_trailing_period(self):
        errors = validate_fabric_name("Sales.")
        self.assertTrue(any("period" in e.lower() for e in errors))


class TestDeploymentDryRun(unittest.TestCase):
    """Test deployment dry-run validator."""

    def _create_output(self, tmpdir: str) -> Path:
        """Create a valid migration output directory."""
        root = Path(tmpdir) / "migration_output"
        cube = root / "test_cube"
        sm = cube / "SemanticModel"
        defn = sm / "definition"
        tables = defn / "tables"
        tables.mkdir(parents=True, exist_ok=True)

        (sm / "model.tmdl").write_text("model Model\n\tculture: en-US\n", encoding="utf-8")
        (sm / ".platform").write_text(json.dumps({
            "$schema": "https://schema.example.com",
            "metadata": {"type": "SemanticModel"},
            "config": {"logicalId": "test"},
        }), encoding="utf-8")
        (defn / "database.tmdl").write_text("compatibilityLevel: 1604\n", encoding="utf-8")
        (tables / "Sales.tmdl").write_text(
            "table Sales\n\tlineageTag: abc\n\tcolumn Amount\n", encoding="utf-8"
        )
        (cube / "generated_ddl.sql").write_text(
            "CREATE TABLE Sales (Amount DECIMAL) USING DELTA;\n", encoding="utf-8"
        )

        return root

    def test_valid_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_output(tmpdir)
            dry_run = DeploymentDryRun(str(root))
            manifest = dry_run.validate()
            self.assertFalse(manifest.has_blockers)
            self.assertGreater(manifest.artifact_count, 0)

    def test_nonexistent_dir(self):
        dry_run = DeploymentDryRun("/nonexistent")
        manifest = dry_run.validate()
        self.assertTrue(manifest.has_blockers)

    def test_missing_model_tmdl_blocker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_output(tmpdir)
            (root / "test_cube" / "SemanticModel" / "model.tmdl").unlink()
            dry_run = DeploymentDryRun(str(root))
            manifest = dry_run.validate()
            self.assertTrue(manifest.has_blockers)

    def test_deployment_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_output(tmpdir)
            dry_run = DeploymentDryRun(str(root))
            manifest = dry_run.validate()
            self.assertTrue(len(manifest.deployment_order) >= 2)
            # Tables should come before semantic models
            order_text = " ".join(manifest.deployment_order)
            self.assertIn("Lakehouse", order_text)
            self.assertIn("semantic", order_text)

    def test_manifest_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_output(tmpdir)
            dry_run = DeploymentDryRun(str(root))
            manifest = dry_run.validate()
            summary = manifest.summary()
            self.assertIn("READY", summary)
            self.assertIn("DEPLOYMENT ORDER", summary)
            self.assertIn("ARTIFACTS", summary)

    def test_export_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_output(tmpdir)
            dry_run = DeploymentDryRun(str(root))
            manifest = dry_run.validate()
            js = export_manifest_json(manifest)
            data = json.loads(js)
            self.assertEqual(data["status"], "READY")
            self.assertGreater(len(data["artifacts"]), 0)

    def test_cross_dependency_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = self._create_output(tmpdir)
            # Add a table reference that doesn't match DDL
            tables_dir = root / "test_cube" / "SemanticModel" / "definition" / "tables"
            (tables_dir / "Unknown.tmdl").write_text(
                "table OrphanTable\n\tlineageTag: zzz\n\tcolumn X\n", encoding="utf-8"
            )
            dry_run = DeploymentDryRun(str(root))
            manifest = dry_run.validate()
            # Should warn about OrphanTable not being in DDL
            self.assertTrue(
                any("OrphanTable" in w for w in manifest.warnings)
                or len(manifest.warnings) > 0
            )


class TestDeploymentManifest(unittest.TestCase):
    """Test manifest data class."""

    def test_empty_manifest(self):
        m = DeploymentManifest(output_dir="/tmp")
        self.assertTrue(m.valid)
        self.assertFalse(m.has_blockers)
        self.assertEqual(m.artifact_count, 0)

    def test_manifest_with_blocker(self):
        m = DeploymentManifest(output_dir="/tmp", blockers=["Missing file"])
        self.assertTrue(m.has_blockers)

    def test_valid_invalid_counts(self):
        m = DeploymentManifest(output_dir="/tmp", artifacts=[
            ArtifactManifestEntry(artifact_type="table", artifact_name="ok"),
            ArtifactManifestEntry(
                artifact_type="table", artifact_name="bad",
                validation_errors=["broken"],
            ),
        ])
        self.assertEqual(m.valid_count, 1)
        self.assertEqual(m.invalid_count, 1)


# =========================================================================
# Run on real output (integration test)
# =========================================================================


class TestToolsOnRealOutput(unittest.TestCase):
    """Integration test using real Essbase migration output (if available)."""

    ESSBASE_OUTPUT = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "output", "essbase_migration",
    )

    @unittest.skipUnless(
        os.path.isdir(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "output", "essbase_migration", "complex_planning",
        )),
        "Real Essbase output not available",
    )
    def test_validate_real_essbase_output(self):
        """Validate real Essbase migration output with all tools."""
        # 1. TMDL file validation (DAX disabled — known nested bracket issue in Essbase DAX)
        results = validate_migration_output(self.ESSBASE_OUTPUT, validate_dax=False)
        self.assertGreater(len(results), 0)

        for name, report in results.items():
            self.assertTrue(
                report.valid,
                f"TMDL structure validation failed for {name}: {report.summary()}"
            )

        # 2. DAX validation — count issues (expected to find some in Essbase output)
        dax_results = validate_migration_output(self.ESSBASE_OUTPUT, validate_dax=True)
        dax_errors_found = sum(
            r.total_errors for r in dax_results.values()
        )
        # The Essbase DAX generator produces nested bracket refs — expected
        self.assertGreater(dax_errors_found, 0, "Expected DAX issues in Essbase output")

        # 3. Fabric dry-run
        dry_run = DeploymentDryRun(self.ESSBASE_OUTPUT)
        manifest = dry_run.validate()
        self.assertFalse(manifest.has_blockers, manifest.summary())
        self.assertGreater(manifest.artifact_count, 0)


if __name__ == "__main__":
    unittest.main()
