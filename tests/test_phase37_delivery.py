"""Tests for Phase 37 — Customer Delivery Package."""

from __future__ import annotations

import pytest

from src.core.delivery_package import (
    AssetCatalog,
    ChangeDocGenerator,
    ChangeEntry,
    ChecklistItem,
    ChecklistItemStatus,
    DeliveryAsset,
    DeliveryAssetType,
    DeliveryPackage,
    DeliveryStatus,
    HandoverChecklist,
    KnownIssue,
    KnownIssueTracker,
    TrainingContentGen,
    TrainingModule,
)


# ===================================================================
# AssetCatalog
# ===================================================================


class TestAssetCatalog:
    def test_create_asset(self):
        cat = AssetCatalog()
        a = cat.create(name="Revenue Report", asset_type=DeliveryAssetType.REPORT)
        assert a.asset_id
        assert cat.total_count == 1

    def test_add_and_get(self):
        cat = AssetCatalog()
        a = DeliveryAsset(name="Model A", asset_type=DeliveryAssetType.SEMANTIC_MODEL)
        cat.add(a)
        found = cat.get(a.asset_id)
        assert found is a

    def test_remove(self):
        cat = AssetCatalog()
        a = cat.create(name="X")
        assert cat.remove(a.asset_id) is True
        assert cat.total_count == 0

    def test_remove_missing(self):
        cat = AssetCatalog()
        assert cat.remove("nonexistent") is False

    def test_by_type(self):
        cat = AssetCatalog()
        cat.create(name="R1", asset_type=DeliveryAssetType.REPORT)
        cat.create(name="R2", asset_type=DeliveryAssetType.REPORT)
        cat.create(name="M1", asset_type=DeliveryAssetType.SEMANTIC_MODEL)
        assert len(cat.by_type(DeliveryAssetType.REPORT)) == 2

    def test_by_status(self):
        cat = AssetCatalog()
        a = cat.create(name="A", status=DeliveryStatus.DELIVERED)
        cat.create(name="B", status=DeliveryStatus.PENDING)
        assert cat.delivered_count == 1
        assert cat.pending_count == 1

    def test_summary(self):
        cat = AssetCatalog()
        cat.create(name="R1", asset_type=DeliveryAssetType.REPORT, status=DeliveryStatus.DELIVERED)
        cat.create(name="P1", asset_type=DeliveryAssetType.PIPELINE, status=DeliveryStatus.MIGRATED)
        s = cat.summary()
        assert s["total"] == 2
        assert "report" in s["by_type"]

    def test_search(self):
        cat = AssetCatalog()
        cat.create(name="Revenue Dashboard")
        cat.create(name="Cost Report")
        cat.create(name="Revenue KPIs")
        results = cat.search("revenue")
        assert len(results) == 2


# ===================================================================
# ChangeDocGenerator
# ===================================================================


class TestChangeDocGenerator:
    def test_add_entry(self):
        gen = ChangeDocGenerator()
        gen.add(ChangeEntry(source_name="OAC::Sales", target_name="PBI::Sales", change_type="created"))
        assert gen.total_changes == 1

    def test_add_from_mapping(self):
        gen = ChangeDocGenerator()
        e = gen.add_from_mapping("OAC::Rev", "PBI::Rev", category="reports")
        assert e.source_name == "OAC::Rev"
        assert gen.total_changes == 1

    def test_by_category(self):
        gen = ChangeDocGenerator()
        gen.add_from_mapping("A", "B", category="schema")
        gen.add_from_mapping("C", "D", category="reports")
        gen.add_from_mapping("E", "F", category="schema")
        assert len(gen.by_category("schema")) == 2

    def test_by_impact(self):
        gen = ChangeDocGenerator()
        gen.add_from_mapping("A", "B", impact="high")
        gen.add_from_mapping("C", "D", impact="low")
        assert len(gen.by_impact("high")) == 1

    def test_generate_markdown(self):
        gen = ChangeDocGenerator()
        gen.add_from_mapping("OAC::Sales", "PBI::Sales", change_type="created",
                              category="reports", impact="low", description="Migrated report")
        md = gen.generate_markdown()
        assert "Migration Change Document" in md
        assert "OAC::Sales" in md
        assert "PBI::Sales" in md

    def test_generate_empty(self):
        gen = ChangeDocGenerator()
        md = gen.generate_markdown()
        assert "Total changes" in md


# ===================================================================
# TrainingContentGen
# ===================================================================


class TestTrainingContentGen:
    def _make_catalog(self, *types: DeliveryAssetType) -> AssetCatalog:
        cat = AssetCatalog()
        for i, t in enumerate(types):
            cat.create(name=f"asset_{i}", asset_type=t)
        return cat

    def test_generate_report_module(self):
        gen = TrainingContentGen()
        catalog = self._make_catalog(DeliveryAssetType.REPORT)
        modules = gen.generate_from_catalog(catalog)
        assert any("Report" in m.title for m in modules)

    def test_generate_semantic_model_module(self):
        gen = TrainingContentGen()
        catalog = self._make_catalog(DeliveryAssetType.SEMANTIC_MODEL)
        modules = gen.generate_from_catalog(catalog)
        assert any("Semantic" in m.title for m in modules)

    def test_generate_rls_module(self):
        gen = TrainingContentGen()
        catalog = self._make_catalog(DeliveryAssetType.RLS_ROLE)
        modules = gen.generate_from_catalog(catalog)
        assert any("Security" in m.title for m in modules)

    def test_generate_pipeline_module(self):
        gen = TrainingContentGen()
        catalog = self._make_catalog(DeliveryAssetType.PIPELINE)
        modules = gen.generate_from_catalog(catalog)
        assert any("Pipeline" in m.title for m in modules)

    def test_generate_lakehouse_module(self):
        gen = TrainingContentGen()
        catalog = self._make_catalog(DeliveryAssetType.LAKEHOUSE_TABLE)
        modules = gen.generate_from_catalog(catalog)
        assert any("Lakehouse" in m.title for m in modules)

    def test_generate_all_types(self):
        gen = TrainingContentGen()
        catalog = self._make_catalog(
            DeliveryAssetType.REPORT, DeliveryAssetType.SEMANTIC_MODEL,
            DeliveryAssetType.RLS_ROLE, DeliveryAssetType.PIPELINE,
            DeliveryAssetType.LAKEHOUSE_TABLE,
        )
        modules = gen.generate_from_catalog(catalog)
        assert len(modules) >= 5

    def test_outline_markdown(self):
        gen = TrainingContentGen()
        catalog = self._make_catalog(DeliveryAssetType.REPORT, DeliveryAssetType.SEMANTIC_MODEL)
        gen.generate_from_catalog(catalog)
        md = gen.generate_outline_markdown()
        assert "Training Plan" in md
        assert "Module 1" in md

    def test_empty_catalog(self):
        gen = TrainingContentGen()
        catalog = AssetCatalog()
        modules = gen.generate_from_catalog(catalog)
        assert len(modules) == 0

    def test_module_fields(self):
        m = TrainingModule(title="Test", duration_minutes=60, audience="admin")
        assert m.module_id
        assert m.duration_minutes == 60


# ===================================================================
# KnownIssueTracker
# ===================================================================


class TestKnownIssueTracker:
    def test_create_issue(self):
        tracker = KnownIssueTracker()
        ki = tracker.create(title="Filter mismatch", severity="medium",
                             workaround="Use direct query instead")
        assert ki.issue_id.startswith("KI-")
        assert tracker.total_count == 1

    def test_by_severity(self):
        tracker = KnownIssueTracker()
        tracker.create(title="A", severity="high")
        tracker.create(title="B", severity="low")
        tracker.create(title="C", severity="high")
        assert len(tracker.by_severity("high")) == 2

    def test_for_asset(self):
        tracker = KnownIssueTracker()
        tracker.create(title="A", affected_assets=["report_1", "dashboard_1"])
        tracker.create(title="B", affected_assets=["report_2"])
        assert len(tracker.for_asset("report_1")) == 1

    def test_generate_markdown(self):
        tracker = KnownIssueTracker()
        tracker.create(title="Bug X", description="Desc", severity="medium",
                        workaround="Do Y", affected_assets=["asset_1"])
        md = tracker.generate_markdown()
        assert "Known Issues" in md
        assert "Bug X" in md
        assert "Do Y" in md

    def test_empty_markdown(self):
        tracker = KnownIssueTracker()
        md = tracker.generate_markdown()
        assert "No known issues" in md


# ===================================================================
# HandoverChecklist
# ===================================================================


class TestHandoverChecklist:
    def test_standard_items(self):
        cl = HandoverChecklist(include_standard=True)
        assert cl.total_count == 20

    def test_no_standard(self):
        cl = HandoverChecklist(include_standard=False)
        assert cl.total_count == 0

    def test_add_custom(self):
        cl = HandoverChecklist(include_standard=False)
        cl.create(category="Custom", description="Custom check")
        assert cl.total_count == 1

    def test_complete_item(self):
        cl = HandoverChecklist(include_standard=False)
        item = cl.create(category="Test", description="Test item")
        item.complete("Done")
        assert item.status == ChecklistItemStatus.DONE
        assert item.notes == "Done"

    def test_skip_item(self):
        item = ChecklistItem(description="Optional")
        item.skip("Not applicable")
        assert item.status == ChecklistItemStatus.NA

    def test_progress(self):
        cl = HandoverChecklist(include_standard=False)
        i1 = cl.create(description="A")
        i2 = cl.create(description="B")
        i1.complete()
        assert cl.progress_pct == pytest.approx(50.0)

    def test_is_complete(self):
        cl = HandoverChecklist(include_standard=False)
        i1 = cl.create(description="A")
        i2 = cl.create(description="B")
        assert not cl.is_complete
        i1.complete()
        i2.skip()
        assert cl.is_complete

    def test_by_category(self):
        cl = HandoverChecklist(include_standard=True)
        data_items = cl.by_category("Data")
        assert len(data_items) >= 2

    def test_generate_markdown(self):
        cl = HandoverChecklist(include_standard=False)
        i1 = cl.create(category="Data", description="Check A")
        i2 = cl.create(category="Data", description="Check B")
        i1.complete()
        md = cl.generate_markdown()
        assert "Handover Checklist" in md
        assert "[x]" in md
        assert "[ ]" in md

    def test_remaining_count(self):
        cl = HandoverChecklist(include_standard=False)
        cl.create(description="A")
        cl.create(description="B")
        assert cl.remaining_count == 2


# ===================================================================
# DeliveryPackage
# ===================================================================


class TestDeliveryPackage:
    def test_create_default(self):
        pkg = DeliveryPackage(customer_name="Acme Corp", project_name="OAC Migration")
        assert pkg.package_id
        assert pkg.created_at

    def test_index_markdown(self):
        pkg = DeliveryPackage(customer_name="Acme", project_name="Migration")
        pkg.catalog.create(name="R1", asset_type=DeliveryAssetType.REPORT)
        md = pkg.generate_index_markdown()
        assert "Acme" in md
        assert "Asset Summary" in md

    def test_not_ready_empty(self):
        pkg = DeliveryPackage()
        assert not pkg.is_ready

    def test_not_ready_pending_assets(self):
        pkg = DeliveryPackage()
        pkg.catalog.create(name="A", status=DeliveryStatus.PENDING)
        assert not pkg.is_ready

    def test_ready_when_complete(self):
        pkg = DeliveryPackage(customer_name="X", project_name="Y")
        pkg.catalog.create(name="A", status=DeliveryStatus.DELIVERED)
        # Complete all checklist items
        for item in pkg.checklist.all_items:
            item.complete()
        assert pkg.is_ready

    def test_subcomponents_independent(self):
        pkg = DeliveryPackage()
        pkg.change_doc.add_from_mapping("A", "B")
        pkg.known_issues.create(title="Bug")
        assert pkg.change_doc.total_changes == 1
        assert pkg.known_issues.total_count == 1


# ===================================================================
# Enums
# ===================================================================


class TestDeliveryEnums:
    def test_asset_type_values(self):
        assert DeliveryAssetType.SEMANTIC_MODEL.value == "semantic_model"
        assert DeliveryAssetType.REPORT.value == "report"

    def test_delivery_status_values(self):
        assert DeliveryStatus.PENDING.value == "pending"
        assert DeliveryStatus.DELIVERED.value == "delivered"

    def test_checklist_status_values(self):
        assert ChecklistItemStatus.TODO.value == "todo"
        assert ChecklistItemStatus.DONE.value == "done"
