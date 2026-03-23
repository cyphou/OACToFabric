"""Tests for Phase 36 — UAT Workflow & Sign-Off."""

from __future__ import annotations

import pytest

from src.core.uat_workflow import (
    ComparisonOutcome,
    ComparisonResult,
    ComparisonSpec,
    ComparisonType,
    Defect,
    DefectLog,
    DefectSeverity,
    DefectStatus,
    SignOffRecord,
    SignOffStatus,
    SignOffTracker,
    UATReport,
    UATSession,
    UATStatus,
    UATWorkflow,
)


# ===================================================================
# UATSession
# ===================================================================


class TestUATSession:
    def test_create_default(self):
        s = UATSession(name="Wave 1 UAT")
        assert s.session_id
        assert s.status == UATStatus.DRAFT
        assert s.created_at

    def test_transition_valid(self):
        s = UATSession()
        s.transition(UATStatus.IN_PROGRESS)
        assert s.status == UATStatus.IN_PROGRESS

    def test_transition_chain(self):
        s = UATSession()
        s.transition(UATStatus.IN_PROGRESS)
        s.transition(UATStatus.COMPLETED)
        s.transition(UATStatus.SIGNED_OFF)
        assert s.status == UATStatus.SIGNED_OFF

    def test_transition_invalid(self):
        s = UATSession()
        with pytest.raises(ValueError):
            s.transition(UATStatus.COMPLETED)  # can't skip IN_PROGRESS

    def test_transition_from_signed_off(self):
        s = UATSession()
        s.transition(UATStatus.IN_PROGRESS)
        s.transition(UATStatus.COMPLETED)
        s.transition(UATStatus.SIGNED_OFF)
        with pytest.raises(ValueError):
            s.transition(UATStatus.IN_PROGRESS)

    def test_transition_blocked(self):
        s = UATSession()
        s.transition(UATStatus.IN_PROGRESS)
        s.transition(UATStatus.BLOCKED)
        assert s.status == UATStatus.BLOCKED
        s.transition(UATStatus.IN_PROGRESS)
        assert s.status == UATStatus.IN_PROGRESS

    def test_updates_timestamp(self):
        s = UATSession()
        old = s.updated_at
        s.transition(UATStatus.IN_PROGRESS)
        assert s.updated_at >= old

    def test_scope_and_tags(self):
        s = UATSession(scope=["report_1", "dashboard_1"], tags={"priority": "high"})
        assert len(s.scope) == 2
        assert s.tags["priority"] == "high"


# ===================================================================
# ComparisonSpec & ComparisonResult
# ===================================================================


class TestComparisonSpec:
    def test_create(self):
        spec = ComparisonSpec(name="Revenue Match", comparison_type=ComparisonType.METRIC_MATCH,
                               source_ref="OAC::Revenue", target_ref="PBI::Revenue")
        assert spec.spec_id
        assert spec.comparison_type == ComparisonType.METRIC_MATCH

    def test_with_tolerance(self):
        spec = ComparisonSpec(name="Approx", tolerance=0.01)
        assert spec.tolerance == 0.01

    def test_with_filters(self):
        spec = ComparisonSpec(filters={"region": "EMEA", "year": "2024"})
        assert spec.filters["region"] == "EMEA"


class TestComparisonResult:
    def test_match(self):
        r = ComparisonResult(spec_id="abc", outcome=ComparisonOutcome.MATCH,
                              source_value=100, target_value=100)
        assert r.outcome == ComparisonOutcome.MATCH

    def test_mismatch(self):
        r = ComparisonResult(spec_id="abc", outcome=ComparisonOutcome.MISMATCH,
                              source_value=100, target_value=95, difference=5.0)
        assert r.difference == 5.0

    def test_error(self):
        r = ComparisonResult(outcome=ComparisonOutcome.ERROR, error_message="timeout")
        assert r.error_message == "timeout"

    def test_timestamp_auto(self):
        r = ComparisonResult()
        assert r.executed_at


# ===================================================================
# DefectLog
# ===================================================================


class TestDefectLog:
    def test_create_defect(self):
        log = DefectLog()
        d = log.create(title="Missing column", severity=DefectSeverity.MAJOR)
        assert d.defect_id.startswith("DEF-")
        assert log.total_count == 1

    def test_add_defect(self):
        log = DefectLog()
        d = Defect(title="Wrong value")
        log.add(d)
        assert log.total_count == 1

    def test_by_severity(self):
        log = DefectLog()
        log.create(title="A", severity=DefectSeverity.MINOR)
        log.create(title="B", severity=DefectSeverity.CRITICAL)
        log.create(title="C", severity=DefectSeverity.MINOR)
        assert len(log.by_severity(DefectSeverity.MINOR)) == 2
        assert len(log.by_severity(DefectSeverity.CRITICAL)) == 1

    def test_by_status(self):
        log = DefectLog()
        d = log.create(title="A")
        assert log.open_count == 1
        d.resolve()
        assert d.status == DefectStatus.FIXED
        assert log.open_count == 0

    def test_by_session(self):
        log = DefectLog()
        log.create(title="A", session_id="s1")
        log.create(title="B", session_id="s2")
        log.create(title="C", session_id="s1")
        assert len(log.by_session("s1")) == 2

    def test_blocker_count(self):
        log = DefectLog()
        log.create(title="A", severity=DefectSeverity.BLOCKER)
        log.create(title="B", severity=DefectSeverity.CRITICAL)
        log.create(title="C", severity=DefectSeverity.MINOR)
        assert log.blocker_count == 2

    def test_summary(self):
        log = DefectLog()
        log.create(severity=DefectSeverity.MINOR)
        log.create(severity=DefectSeverity.MINOR)
        log.create(severity=DefectSeverity.MAJOR)
        s = log.summary()
        assert s["minor"] == 2
        assert s["major"] == 1

    def test_resolve_defect(self):
        d = Defect(title="Bug")
        d.resolve(DefectStatus.WONT_FIX)
        assert d.status == DefectStatus.WONT_FIX
        assert d.resolved_at


# ===================================================================
# SignOffTracker
# ===================================================================


class TestSignOffTracker:
    def test_create_record(self):
        tracker = SignOffTracker()
        r = tracker.create(session_id="s1", approver="alice")
        assert r.status == SignOffStatus.PENDING
        assert tracker.pending_count == 1

    def test_approve(self):
        r = SignOffRecord(approver="bob")
        r.approve("Looks good")
        assert r.status == SignOffStatus.APPROVED
        assert r.signed_at

    def test_reject(self):
        r = SignOffRecord(approver="carol")
        r.reject("Data mismatch in Q4")
        assert r.status == SignOffStatus.REJECTED

    def test_conditional_approve(self):
        r = SignOffRecord(approver="dave")
        r.approve_conditional(["Fix defect DEF-001", "Retest dashboard"])
        assert r.status == SignOffStatus.CONDITIONAL
        assert len(r.conditions) == 2

    def test_fully_approved(self):
        tracker = SignOffTracker()
        r1 = tracker.create(session_id="s1", approver="alice")
        r2 = tracker.create(session_id="s1", approver="bob")
        assert not tracker.is_fully_approved("s1")
        r1.approve()
        r2.approve()
        assert tracker.is_fully_approved("s1")

    def test_has_rejection(self):
        tracker = SignOffTracker()
        r1 = tracker.create(session_id="s1", approver="alice")
        r1.reject()
        assert tracker.has_rejection("s1")

    def test_empty_session_not_approved(self):
        tracker = SignOffTracker()
        assert not tracker.is_fully_approved("nonexistent")


# ===================================================================
# UATWorkflow
# ===================================================================


class TestUATWorkflow:
    def test_create_session(self):
        wf = UATWorkflow()
        s = wf.create_session(name="Wave 1")
        assert s.session_id in [sess.session_id for sess in wf.all_sessions]

    def test_get_session(self):
        wf = UATWorkflow()
        s = wf.create_session(name="Wave 1")
        found = wf.get_session(s.session_id)
        assert found is s

    def test_add_comparison(self):
        wf = UATWorkflow()
        s = wf.create_session(name="Test")
        spec = ComparisonSpec(name="Revenue")
        wf.add_comparison(s.session_id, spec)
        assert len(wf.get_comparisons(s.session_id)) == 1

    def test_add_comparison_invalid_session(self):
        wf = UATWorkflow()
        with pytest.raises(ValueError):
            wf.add_comparison("nonexistent", ComparisonSpec())

    def test_record_result(self):
        wf = UATWorkflow()
        s = wf.create_session()
        spec = ComparisonSpec(name="KPI")
        wf.add_comparison(s.session_id, spec)
        wf.record_result(s.session_id, ComparisonResult(
            spec_id=spec.spec_id, outcome=ComparisonOutcome.MATCH,
        ))
        assert len(wf.get_results(s.session_id)) == 1

    def test_session_progress(self):
        wf = UATWorkflow()
        s = wf.create_session()
        spec1 = ComparisonSpec(name="A")
        spec2 = ComparisonSpec(name="B")
        wf.add_comparison(s.session_id, spec1)
        wf.add_comparison(s.session_id, spec2)
        wf.record_result(s.session_id, ComparisonResult(
            spec_id=spec1.spec_id, outcome=ComparisonOutcome.MATCH,
        ))
        progress = wf.session_progress(s.session_id)
        assert progress["total_specs"] == 2
        assert progress["completed_specs"] == 1
        assert progress["progress_pct"] == pytest.approx(50.0)

    def test_start_and_complete(self):
        wf = UATWorkflow()
        s = wf.create_session()
        wf.start_session(s.session_id)
        assert s.status == UATStatus.IN_PROGRESS
        wf.complete_session(s.session_id)
        assert s.status == UATStatus.COMPLETED

    def test_sign_off_session(self):
        wf = UATWorkflow()
        s = wf.create_session()
        wf.start_session(s.session_id)
        wf.complete_session(s.session_id)
        record = wf.sign_off_session(s.session_id, "alice", "Approved")
        assert record.status == SignOffStatus.APPROVED
        assert s.status == UATStatus.SIGNED_OFF

    def test_defect_integration(self):
        wf = UATWorkflow()
        s = wf.create_session()
        wf.defect_log.create(title="Bug 1", session_id=s.session_id, severity=DefectSeverity.MAJOR)
        progress = wf.session_progress(s.session_id)
        assert progress["defects"] == 1


# ===================================================================
# UATReport
# ===================================================================


class TestUATReport:
    def test_session_report(self):
        wf = UATWorkflow()
        s = wf.create_session(name="Wave 1 UAT", wave="W1")
        spec = ComparisonSpec(name="Revenue")
        wf.add_comparison(s.session_id, spec)
        wf.start_session(s.session_id)
        wf.record_result(s.session_id, ComparisonResult(
            spec_id=spec.spec_id, outcome=ComparisonOutcome.MATCH,
        ))
        report = UATReport(wf)
        md = report.generate_session_report(s.session_id)
        assert "Wave 1 UAT" in md
        assert "Progress" in md

    def test_session_report_not_found(self):
        wf = UATWorkflow()
        report = UATReport(wf)
        md = report.generate_session_report("nonexistent")
        assert "not found" in md

    def test_session_report_with_defects(self):
        wf = UATWorkflow()
        s = wf.create_session(name="Test")
        wf.defect_log.create(title="Bug", session_id=s.session_id, severity=DefectSeverity.CRITICAL)
        report = UATReport(wf)
        md = report.generate_session_report(s.session_id)
        assert "Defects" in md

    def test_session_report_with_signoffs(self):
        wf = UATWorkflow()
        s = wf.create_session(name="Test")
        wf.start_session(s.session_id)
        wf.complete_session(s.session_id)
        wf.sign_off_session(s.session_id, "alice")
        report = UATReport(wf)
        md = report.generate_session_report(s.session_id)
        assert "Sign-offs" in md

    def test_summary_report(self):
        wf = UATWorkflow()
        wf.create_session(name="S1")
        wf.create_session(name="S2")
        wf.defect_log.create(title="Bug")
        report = UATReport(wf)
        md = report.generate_summary()
        assert "Total sessions" in md
        assert "2" in md


# ===================================================================
# Enums
# ===================================================================


class TestUATEnums:
    def test_uat_status_values(self):
        assert UATStatus.DRAFT.value == "draft"
        assert UATStatus.SIGNED_OFF.value == "signed_off"

    def test_comparison_type_values(self):
        assert ComparisonType.DATA_MATCH.value == "data_match"
        assert ComparisonType.VISUAL_MATCH.value == "visual_match"

    def test_defect_severity_values(self):
        assert DefectSeverity.BLOCKER.value == "blocker"
        assert DefectSeverity.COSMETIC.value == "cosmetic"

    def test_signoff_status_values(self):
        assert SignOffStatus.PENDING.value == "pending"
        assert SignOffStatus.CONDITIONAL.value == "conditional"
