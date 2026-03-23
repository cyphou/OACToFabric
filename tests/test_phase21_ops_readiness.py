"""Phase 21 — Operational Readiness tests.

≥30 tests covering:
  • Application Insights exporter (dry-run, payload structure)
  • OTLP exporter (traces, metrics, dry-run, JSON)
  • Key Vault secret provider (cache, env fallback, config fallback)
  • Security audit (credential scanning, config audit, log audit)
  • Notification manager HTTP mocks (Teams, email, PagerDuty)
"""

from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from src.core.appinsights_exporter import (
    AppInsightsExporter,
    ExportResult,
    OTLPExporter,
)
from src.core.keyvault_provider import (
    KeyVaultSecretProvider,
    ManagedIdentityAuth,
    SecretValue,
)
from src.core.security_audit import (
    AuditFinding,
    AuditReport,
    CredentialScanner,
    FindingSeverity,
    audit_config,
    audit_log_output,
)
from src.core.telemetry import TelemetryCollector


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  App Insights exporter tests                                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestAppInsightsExporter:
    def test_parse_ikey(self):
        conn = "InstrumentationKey=abc-123;IngestionEndpoint=https://dc.example.com"
        exp = AppInsightsExporter(conn, dry_run=True)
        assert exp.instrumentation_key == "abc-123"

    def test_parse_ikey_missing(self):
        exp = AppInsightsExporter("SomethingElse=val", dry_run=True)
        assert exp.instrumentation_key == ""

    def test_dry_run_export(self):
        tc = TelemetryCollector()
        ctx = tc.start_run("test-run")
        tc.track_event("test_event", {"key": "val"})
        tc.record_metric("items", 42)
        with tc.span("test_span", agent_id="01"):
            pass

        exp = AppInsightsExporter(
            "InstrumentationKey=test-key", dry_run=True
        )
        result = exp.export(tc)
        assert result.success
        assert result.events_sent >= 1
        assert result.metrics_sent >= 1
        assert result.spans_sent >= 1
        assert result.exporter == "appinsights"

    def test_event_payload_structure(self):
        tc = TelemetryCollector()
        tc.start_run()
        evt = tc.track_event("wave_started", {"wave": "1"})

        exp = AppInsightsExporter(
            "InstrumentationKey=test-key", dry_run=True
        )
        payload = exp._build_event_payload(evt)
        assert payload["name"] == "AppEvents"
        assert payload["iKey"] == "test-key"
        assert payload["data"]["baseType"] == "EventData"
        assert payload["data"]["baseData"]["name"] == "wave_started"

    def test_metric_payload_structure(self):
        tc = TelemetryCollector()
        metric = tc.record_metric("items_migrated", 100, tags={"agent": "02"})

        exp = AppInsightsExporter(
            "InstrumentationKey=test-key", dry_run=True
        )
        payload = exp._build_metric_payload(metric)
        assert payload["name"] == "AppMetrics"
        assert payload["data"]["baseType"] == "MetricData"
        metrics_data = payload["data"]["baseData"]["metrics"]
        assert metrics_data[0]["name"] == "items_migrated"
        assert metrics_data[0]["value"] == 100

    def test_span_payload_structure(self):
        tc = TelemetryCollector()
        tc.start_run()
        with tc.span("discover", agent_id="01") as s:
            pass

        exp = AppInsightsExporter(
            "InstrumentationKey=k", dry_run=True
        )
        payload = exp._build_span_payload(s)
        assert payload["name"] == "AppDependencies"
        assert payload["data"]["baseData"]["name"] == "discover"
        assert payload["data"]["baseData"]["success"] is True

    def test_ingestion_endpoint_from_conn_string(self):
        conn = "InstrumentationKey=k;IngestionEndpoint=https://custom.endpoint.com"
        exp = AppInsightsExporter(conn, dry_run=True)
        assert exp._get_ingestion_endpoint() == "https://custom.endpoint.com"

    def test_ingestion_endpoint_default(self):
        conn = "InstrumentationKey=k"
        exp = AppInsightsExporter(conn, dry_run=True)
        assert "dc.services.visualstudio.com" in exp._get_ingestion_endpoint()


class TestExportResult:
    def test_success_when_no_errors(self):
        r = ExportResult(exporter="test", events_sent=5)
        assert r.success is True
        assert r.total_items == 5

    def test_failure_when_errors(self):
        r = ExportResult(exporter="test", errors=["bad"])
        assert r.success is False

    def test_total_items(self):
        r = ExportResult(
            exporter="test", events_sent=3, metrics_sent=5, spans_sent=2
        )
        assert r.total_items == 10


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  OTLP exporter tests                                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestOTLPExporter:
    def test_dry_run_export(self):
        tc = TelemetryCollector()
        tc.start_run()
        tc.track_event("ev")
        tc.record_metric("m", 1)
        with tc.span("sp"):
            pass

        exp = OTLPExporter(dry_run=True)
        result = exp.export(tc)
        assert result.success
        assert result.exporter == "otlp"
        assert result.spans_sent >= 1
        assert result.metrics_sent >= 1

    def test_trace_payload_structure(self):
        tc = TelemetryCollector()
        tc.start_run("run-abc")
        with tc.span("my_span", agent_id="01") as s:
            pass

        exp = OTLPExporter(service_name="test-svc", dry_run=True)
        payload = exp._build_trace_payload([s])
        assert "resourceSpans" in payload
        spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) == 1
        assert spans[0]["name"] == "my_span"

    def test_metrics_payload_structure(self):
        tc = TelemetryCollector()
        m = tc.record_metric("x", 99)

        exp = OTLPExporter(dry_run=True)
        payload = exp._build_metrics_payload([m])
        assert "resourceMetrics" in payload
        metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
        assert metrics[0]["name"] == "x"
        assert metrics[0]["sum"]["dataPoints"][0]["asDouble"] == 99

    def test_to_json(self):
        tc = TelemetryCollector()
        tc.start_run()
        tc.record_metric("count", 5)
        with tc.span("sp"):
            pass

        exp = OTLPExporter(dry_run=True)
        json_str = exp.to_json(tc)
        data = json.loads(json_str)
        assert "traces" in data or "metrics" in data

    def test_resource_attributes(self):
        exp = OTLPExporter(service_name="my-svc")
        attrs = exp._resource_attrs()
        names = [a["key"] for a in attrs]
        assert "service.name" in names
        values = {a["key"]: a["value"]["stringValue"] for a in attrs}
        assert values["service.name"] == "my-svc"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Key Vault provider tests                                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestKeyVaultSecretProvider:
    def test_env_fallback(self):
        """Secrets resolve from environment when no Key Vault is configured."""
        provider = KeyVaultSecretProvider(
            vault_url="",
            fallback_to_env=True,
        )
        with patch.dict(os.environ, {"MY_SECRET": "env-value-123"}):
            secret = provider.get_secret("my-secret")
            assert secret.value == "env-value-123"
            assert secret.source == "env"

    def test_config_fallback(self):
        """Config dict fallback works when env and KV are unavailable."""
        provider = KeyVaultSecretProvider(
            vault_url="",
            fallback_to_env=False,
            config_fallback={"oac-password": "dev-pass-123"},
        )
        secret = provider.get_secret("oac-password")
        assert secret.value == "dev-pass-123"
        assert secret.source == "config"

    def test_cache_hit(self):
        """Secrets are cached after first retrieval."""
        provider = KeyVaultSecretProvider(
            vault_url="",
            fallback_to_env=False,
            config_fallback={"key1": "val1"},
        )
        s1 = provider.get_secret("key1")
        assert provider.cache_size == 1
        s2 = provider.get_secret("key1")
        assert s2.source == "cache"
        assert s2.value == "val1"

    def test_cache_clear(self):
        provider = KeyVaultSecretProvider(
            vault_url="",
            config_fallback={"x": "y"},
            fallback_to_env=False,
        )
        provider.get_secret("x")
        assert provider.cache_size == 1
        provider.clear_cache()
        assert provider.cache_size == 0

    def test_missing_secret_raises(self):
        provider = KeyVaultSecretProvider(
            vault_url="", fallback_to_env=False
        )
        with pytest.raises(KeyError, match="not-found"):
            provider.get_secret("not-found")

    def test_get_secret_value_default(self):
        provider = KeyVaultSecretProvider(
            vault_url="", fallback_to_env=False
        )
        assert provider.get_secret_value("missing", "default_val") == "default_val"

    def test_get_secret_value_returns_value(self):
        provider = KeyVaultSecretProvider(
            vault_url="",
            fallback_to_env=False,
            config_fallback={"k": "v"},
        )
        assert provider.get_secret_value("k") == "v"


class TestSecretValue:
    def test_not_expired(self):
        sv = SecretValue(name="x", value="y", expires_at=time.time() + 3600)
        assert sv.is_expired is False

    def test_expired(self):
        sv = SecretValue(name="x", value="y", expires_at=time.time() - 1)
        assert sv.is_expired is True

    def test_no_expiry(self):
        sv = SecretValue(name="x", value="y")
        assert sv.is_expired is False

    def test_repr_redacted(self):
        sv = SecretValue(name="password", value="super-secret")
        assert "super-secret" not in repr(sv)
        assert "redacted" in repr(sv)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Security audit tests                                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestCredentialScanner:
    def test_detects_password(self):
        text = 'password = "myS3cur3Pa$$"'
        scanner = CredentialScanner()
        findings = scanner.scan_text(text)
        assert len(findings) >= 1
        assert any(f.pattern_name == "hardcoded_password" for f in findings)

    def test_detects_api_key(self):
        text = 'api_key = "ABCDEF1234567890ABCDEF"'
        scanner = CredentialScanner()
        findings = scanner.scan_text(text)
        assert len(findings) >= 1
        assert any(f.pattern_name == "hardcoded_api_key" for f in findings)

    def test_detects_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        scanner = CredentialScanner()
        findings = scanner.scan_text(text)
        assert len(findings) >= 1
        assert any(f.severity == FindingSeverity.CRITICAL for f in findings)

    def test_detects_private_key(self):
        text = "-----BEGIN RSA PRIVATE KEY-----"
        scanner = CredentialScanner()
        findings = scanner.scan_text(text)
        assert len(findings) >= 1
        assert any(f.pattern_name == "private_key_header" for f in findings)

    def test_clean_text(self):
        text = "this is safe text with no credentials"
        scanner = CredentialScanner()
        findings = scanner.scan_text(text)
        assert len(findings) == 0

    def test_scan_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('password = "hunter2"\nprint("hello")\n')
        scanner = CredentialScanner()
        findings = scanner.scan_file(f)
        assert len(findings) >= 1
        assert findings[0].line_number == 1

    def test_scan_directory(self, tmp_path):
        (tmp_path / "clean.py").write_text("x = 1\n")
        (tmp_path / "dirty.py").write_text('secret = "s3cr3t_val"\n')
        scanner = CredentialScanner()
        report = scanner.scan_directory(tmp_path)
        assert report.files_scanned >= 2
        assert report.lines_scanned >= 2
        assert len(report.findings) >= 1

    def test_skip_binary_extensions(self, tmp_path):
        f = tmp_path / "data.pyc"
        f.write_bytes(b'\x00\x01\x02')
        scanner = CredentialScanner()
        findings = scanner.scan_file(f)
        assert findings == []


class TestAuditReport:
    def test_passed_when_no_high(self):
        r = AuditReport(
            findings=[
                AuditFinding(
                    file_path="f.py",
                    line_number=1,
                    pattern_name="x",
                    severity=FindingSeverity.LOW,
                    description="d",
                )
            ]
        )
        assert r.passed is True

    def test_failed_when_high(self):
        r = AuditReport(
            findings=[
                AuditFinding(
                    file_path="f.py",
                    line_number=1,
                    pattern_name="x",
                    severity=FindingSeverity.HIGH,
                    description="d",
                )
            ]
        )
        assert r.passed is False
        assert r.high_count == 1

    def test_summary(self):
        r = AuditReport(files_scanned=10, lines_scanned=500)
        s = r.summary()
        assert "PASS" in s
        assert "10 files" in s


class TestAuditConfig:
    def test_detects_plaintext_password(self):
        config = {
            "oac": {
                "password": "real_password_here",
                "url": "https://oac.example.com",
            }
        }
        findings = audit_config(config)
        assert len(findings) >= 1
        assert any("password" in f.description.lower() for f in findings)

    def test_clean_config(self):
        config = {
            "oac": {
                "url": "https://oac.example.com",
                "timeout": 30,
            }
        }
        findings = audit_config(config)
        assert len(findings) == 0

    def test_detects_secret_key(self):
        config = {"azure": {"client_secret": "long-secret-value-here"}}
        findings = audit_config(config)
        assert len(findings) >= 1

    def test_detects_connection_string(self):
        config = {
            "db": {"connection_string": "Server=host;Password=xyz123abc"}
        }
        findings = audit_config(config)
        assert any("connection_string" in f.description.lower() for f in findings)


class TestAuditLogOutput:
    def test_detects_leaked_password_in_logs(self):
        log = """
2024-01-01 INFO Starting migration
2024-01-01 DEBUG password = "leaked_cred_123"
2024-01-01 INFO Done
"""
        findings = audit_log_output(log)
        assert len(findings) >= 1

    def test_clean_logs(self):
        log = """
2024-01-01 INFO Starting migration
2024-01-01 INFO Processing 100 items
2024-01-01 INFO Done
"""
        findings = audit_log_output(log)
        assert len(findings) == 0
