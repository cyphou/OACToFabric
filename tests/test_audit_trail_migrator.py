"""Tests for audit_trail_migrator — OAC audit logs → Fabric audit integration."""

from __future__ import annotations

import unittest

from src.agents.security.audit_trail_migrator import (
    AuditMigrationResult,
    AuditTableSchema,
    OACAuditEvent,
    generate_audit_migration,
    map_audit_event,
)


class TestAuditTableSchema(unittest.TestCase):

    def test_default_ddl(self):
        schema = AuditTableSchema()
        ddl = schema.to_ddl()
        self.assertIn("CREATE TABLE", ddl)
        self.assertIn("migration_audit_trail", ddl)
        self.assertIn("event_type", ddl)
        self.assertIn("USING DELTA", ddl)
        self.assertIn("PARTITIONED BY", ddl)

    def test_custom_table_name(self):
        schema = AuditTableSchema(table_name="custom_audit")
        ddl = schema.to_ddl()
        self.assertIn("custom_audit", ddl)


class TestMapAuditEvent(unittest.TestCase):

    def test_login_event(self):
        event = OACAuditEvent(event_type="login", user="user@corp.com", timestamp="2025-01-01T00:00:00Z")
        mapped = map_audit_event(event)
        self.assertEqual(mapped["event_type"], "UserLogin")
        self.assertEqual(mapped["user_principal"], "user@corp.com")
        self.assertEqual(mapped["source_system"], "OAC")

    def test_query_event(self):
        event = OACAuditEvent(event_type="query", user="analyst@corp.com")
        mapped = map_audit_event(event)
        self.assertEqual(mapped["event_type"], "QueryExecution")

    def test_export_event(self):
        event = OACAuditEvent(event_type="export")
        mapped = map_audit_event(event)
        self.assertEqual(mapped["event_type"], "DataExport")

    def test_unknown_event_passthrough(self):
        event = OACAuditEvent(event_type="custom_event")
        mapped = map_audit_event(event)
        self.assertEqual(mapped["event_type"], "custom_event")

    def test_all_fields_present(self):
        event = OACAuditEvent(
            event_type="view_report",
            timestamp="2025-01-01",
            user="u@c.com",
            resource_path="/reports/sales",
            action="view",
            details="Viewed report",
            ip_address="1.2.3.4",
            session_id="sess-1",
        )
        mapped = map_audit_event(event)
        self.assertEqual(mapped["event_type"], "ReportView")
        self.assertEqual(mapped["ip_address"], "1.2.3.4")
        self.assertEqual(mapped["session_id"], "sess-1")


class TestGenerateAuditMigration(unittest.TestCase):

    def test_basic_generation(self):
        result = generate_audit_migration()
        self.assertIn("CREATE TABLE", result.table_ddl)
        self.assertIn("migration_audit_trail", result.table_ddl)
        self.assertIn("Audit Trail Ingestion", result.pyspark_ingestion)
        self.assertEqual(result.pipeline_json["name"], "IngestAuditTrail")
        self.assertEqual(result.retention_policy.retention_days, 365)

    def test_custom_retention(self):
        result = generate_audit_migration(retention_days=90)
        self.assertEqual(result.retention_policy.retention_days, 90)

    def test_custom_table_name(self):
        result = generate_audit_migration(table_name="my_audit")
        self.assertIn("my_audit", result.table_ddl)
        self.assertIn("my_audit", result.pyspark_ingestion)

    def test_pipeline_json_structure(self):
        result = generate_audit_migration()
        pj = result.pipeline_json
        self.assertEqual(pj["type"], "TridentNotebook")
        self.assertIn("parameters", pj["typeProperties"])


if __name__ == "__main__":
    unittest.main()
