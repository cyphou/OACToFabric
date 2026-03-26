"""Tests for governance_engine module."""

from __future__ import annotations

import pytest

from src.agents.security.governance_engine import (
    DEFAULT_GOVERNANCE_CONFIG,
    GovernanceFinding,
    GovernanceReport,
    check_naming,
    detect_pii,
    map_sensitivity_label,
    redact_credentials,
    run_governance_scan,
    scan_tables_for_pii,
)


# ---------------------------------------------------------------------------
# Naming checks
# ---------------------------------------------------------------------------

class TestCheckNaming:
    def test_name_too_long(self):
        long_name = "a" * 200
        findings = check_naming(long_name, "table")
        assert any(f.category == "naming" for f in findings)

    def test_measure_missing_prefix(self):
        findings = check_naming("TotalSales", "measure")
        assert any("prefix" in f.message for f in findings)

    def test_measure_with_prefix_ok(self):
        findings = check_naming("m_TotalSales", "measure")
        prefix_findings = [f for f in findings if "prefix" in f.message]
        assert len(prefix_findings) == 0

    def test_table_style_check(self):
        findings = check_naming("my_table", "table", {"table_style": "PascalCase", "max_name_length": 128})
        assert any("PascalCase" in f.message for f in findings)

    def test_column_snake_case(self):
        findings = check_naming("OrderDate", "column", {"column_style": "snake_case", "max_name_length": 128})
        assert any("snake_case" in f.message for f in findings)


# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------

class TestPIIDetection:
    def test_email_detected(self):
        findings = detect_pii("email")
        assert any(f.category == "pii" and "email" in f.message for f in findings)

    def test_ssn_detected(self):
        findings = detect_pii("ssn")
        assert any("ssn" in f.message.lower() for f in findings)

    def test_phone_detected(self):
        findings = detect_pii("phone")
        assert len(findings) >= 1

    def test_credit_card_detected(self):
        findings = detect_pii("credit_card")
        assert len(findings) >= 1

    def test_no_pii(self):
        findings = detect_pii("order_total")
        assert len(findings) == 0

    def test_salary_detected(self):
        findings = detect_pii("salary")
        assert any("salary" in f.message.lower() for f in findings)


class TestScanTablesForPII:
    def test_finds_columns(self):
        tables = [
            {"name": "Users", "columns": [
                {"name": "email", "data_type": "varchar"},
                {"name": "id", "data_type": "int"},
            ]},
        ]
        pii = scan_tables_for_pii(tables)
        assert len(pii) >= 1
        assert pii[0]["pii_type"] == "email"

    def test_no_pii_tables(self):
        tables = [
            {"name": "Products", "columns": [
                {"name": "sku", "data_type": "varchar"},
                {"name": "price", "data_type": "decimal"},
            ]},
        ]
        assert scan_tables_for_pii(tables) == []


# ---------------------------------------------------------------------------
# Credential redaction
# ---------------------------------------------------------------------------

class TestRedactCredentials:
    def test_password(self):
        text = "password=MySecret123"
        result, count = redact_credentials(text)
        assert "MySecret123" not in result
        assert "REDACTED" in result
        assert count >= 1

    def test_bearer_token(self):
        text = "Bearer eyJhbGciOiJIUzI1NiJ9.test"
        result, count = redact_credentials(text)
        assert "eyJhbGci" not in result

    def test_connection_string(self):
        text = 'connection_string="Server=x;Password=y"'
        result, count = redact_credentials(text)
        assert "REDACTED" in result

    def test_no_credentials(self):
        text = "SELECT * FROM table WHERE id = 1"
        result, count = redact_credentials(text)
        assert result == text
        assert count == 0

    def test_api_key(self):
        text = "api_key=abc123def456"
        result, count = redact_credentials(text)
        assert "abc123def456" not in result


# ---------------------------------------------------------------------------
# Sensitivity labels
# ---------------------------------------------------------------------------

class TestSensitivityLabel:
    def test_administrator(self):
        assert map_sensitivity_label("Administrator") == "Highly Confidential"

    def test_viewer(self):
        assert map_sensitivity_label("Viewer") == "General"

    def test_unknown_role(self):
        assert map_sensitivity_label("CustomRole") == "General"


# ---------------------------------------------------------------------------
# Full governance scan
# ---------------------------------------------------------------------------

class TestRunGovernanceScan:
    def test_full_scan(self):
        tables = [
            {
                "name": "Users",
                "columns": [
                    {"name": "email", "data_type": "varchar"},
                    {"name": "first_name", "data_type": "varchar"},
                    {"name": "order_count", "data_type": "int"},
                ],
                "measures": [{"name": "TotalOrders"}],
            },
        ]
        report = run_governance_scan(tables)
        assert isinstance(report, GovernanceReport)
        assert report.finding_count > 0
        # Should find PII (email, name)
        assert len(report.pii_columns) >= 2
        # Should find naming issues
        assert "naming" in report.by_category or "pii" in report.by_category

    def test_empty_tables(self):
        report = run_governance_scan([])
        assert report.finding_count == 0

    def test_mode_from_config(self):
        report = run_governance_scan([], config={"mode": "enforce", "naming": {}, "pii_detection": False})
        assert report.mode == "enforce"
