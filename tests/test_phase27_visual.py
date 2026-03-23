"""Phase 27 — AI-Powered Visual Validation.

Tests cover:
- ViewportSize enum and VIEWPORT_DIMENSIONS mapping
- ScreenshotSpec construction
- Screenshot validity and content_hash
- ScreenshotPair.both_valid
- ScreenshotCapture mock mode (deterministic screenshots)
- VisualDiff scoring, passed threshold, summary
- VisualComparator SSIM comparison
- VisualValidationReport aggregation
- VisualValidationRunner batch validation
"""

from __future__ import annotations

import pytest

from src.validation.visual_validator import (
    VIEWPORT_DIMENSIONS,
    Screenshot,
    ScreenshotCapture,
    ScreenshotPair,
    ScreenshotSpec,
    ViewportSize,
    VisualComparator,
    VisualDiff,
    VisualValidationReport,
    VisualValidationRunner,
)


# ===================================================================
# ViewportSize
# ===================================================================


class TestViewportSize:
    """Tests for viewport size enum."""

    def test_viewport_values(self):
        assert ViewportSize.DESKTOP.value == "desktop"
        assert ViewportSize.TABLET.value == "tablet"
        assert ViewportSize.MOBILE.value == "mobile"

    def test_viewport_dimensions(self):
        assert len(VIEWPORT_DIMENSIONS) == 3
        for vp in ViewportSize:
            dims = VIEWPORT_DIMENSIONS[vp]
            assert dims[0] > 0
            assert dims[1] > 0

    def test_desktop_larger_than_mobile(self):
        d = VIEWPORT_DIMENSIONS[ViewportSize.DESKTOP]
        m = VIEWPORT_DIMENSIONS[ViewportSize.MOBILE]
        assert d[0] > m[0]


# ===================================================================
# ScreenshotSpec
# ===================================================================


class TestScreenshotSpec:
    """Tests for screenshot specification."""

    def test_spec_defaults(self):
        spec = ScreenshotSpec(
            report_id="r1",
            report_name="Sales Report",
            page_index=0,
            viewport=ViewportSize.DESKTOP,
        )
        assert spec.report_id == "r1"
        assert spec.url == ""
        assert spec.wait_seconds == 3

    def test_spec_custom(self):
        spec = ScreenshotSpec(
            report_id="r1",
            report_name="Sales",
            page_index=2,
            viewport=ViewportSize.MOBILE,
            url="http://example.com",
            wait_seconds=10,
        )
        assert spec.viewport == ViewportSize.MOBILE
        assert spec.url == "http://example.com"


# ===================================================================
# Screenshot
# ===================================================================


class TestScreenshot:
    """Tests for screenshot data."""

    def test_valid_screenshot(self):
        spec = ScreenshotSpec("r1", "report", 0, ViewportSize.DESKTOP)
        ss = Screenshot(
            spec=spec,
            image_data=b"fake-image-data",
            width=1920,
            height=1080,
        )
        assert ss.is_valid is True
        assert len(ss.content_hash) == 16  # SHA-256 truncated to 16 chars

    def test_invalid_screenshot(self):
        spec = ScreenshotSpec("r1", "report", 0, ViewportSize.DESKTOP)
        ss = Screenshot(
            spec=spec,
            image_data=b"",
            width=0,
            height=0,
            error="capture failed",
        )
        assert ss.is_valid is False

    def test_content_hash_deterministic(self):
        spec = ScreenshotSpec("r1", "report", 0, ViewportSize.DESKTOP)
        data = b"same-data"
        s1 = Screenshot(spec=spec, image_data=data, width=100, height=100)
        s2 = Screenshot(spec=spec, image_data=data, width=100, height=100)
        assert s1.content_hash == s2.content_hash


# ===================================================================
# ScreenshotPair
# ===================================================================


class TestScreenshotPair:
    """Tests for screenshot pair."""

    def test_both_valid(self):
        spec = ScreenshotSpec("r1", "report", 0, ViewportSize.DESKTOP)
        src = Screenshot(spec=spec, image_data=b"a", width=100, height=100)
        tgt = Screenshot(spec=spec, image_data=b"b", width=100, height=100)
        pair = ScreenshotPair(report_id="r1", report_name="report", source=src, target=tgt)
        assert pair.both_valid is True

    def test_one_invalid(self):
        spec = ScreenshotSpec("r1", "report", 0, ViewportSize.DESKTOP)
        src = Screenshot(spec=spec, image_data=b"a", width=100, height=100)
        tgt = Screenshot(spec=spec, image_data=b"", width=0, height=0, error="fail")
        pair = ScreenshotPair(report_id="r1", report_name="report", source=src, target=tgt)
        assert pair.both_valid is False


# ===================================================================
# ScreenshotCapture (mock mode)
# ===================================================================


class TestScreenshotCapture:
    """Tests for mock screenshot capture."""

    @pytest.mark.asyncio
    async def test_mock_capture(self):
        capture = ScreenshotCapture(mock=True)
        spec = ScreenshotSpec("r1", "Sales", 0, ViewportSize.DESKTOP)
        ss = await capture.capture(spec)
        assert ss.is_valid is True
        assert ss.width > 0
        assert ss.height > 0

    @pytest.mark.asyncio
    async def test_mock_deterministic(self):
        capture = ScreenshotCapture(mock=True)
        spec = ScreenshotSpec("r1", "Sales", 0, ViewportSize.DESKTOP)
        s1 = await capture.capture(spec)
        s2 = await capture.capture(spec)
        assert s1.content_hash == s2.content_hash

    @pytest.mark.asyncio
    async def test_mock_different_reports(self):
        capture = ScreenshotCapture(mock=True)
        s1 = await capture.capture(
            ScreenshotSpec("r1", "Sales", 0, ViewportSize.DESKTOP)
        )
        s2 = await capture.capture(
            ScreenshotSpec("r2", "Finance", 0, ViewportSize.DESKTOP)
        )
        assert s1.content_hash != s2.content_hash


# ===================================================================
# VisualDiff
# ===================================================================


class TestVisualDiff:
    """Tests for visual diff results."""

    def test_high_score_passes(self):
        diff = VisualDiff(
            report_id="r1",
            report_name="report1",
            similarity_score=0.95,
            layout_match=True,
            data_match=True,
            style_match=True,
            differences=[],
            method="ssim",
        )
        assert diff.passed is True

    def test_low_score_fails(self):
        diff = VisualDiff(
            report_id="r1",
            report_name="report1",
            similarity_score=0.50,
            layout_match=False,
            data_match=False,
            style_match=False,
            differences=["layout mismatch"],
            method="ssim",
        )
        assert diff.passed is False

    def test_threshold_boundary(self):
        diff = VisualDiff(
            report_id="r1",
            report_name="report1",
            similarity_score=0.85,
            layout_match=True,
            data_match=True,
            style_match=True,
            differences=[],
            method="ssim",
        )
        assert diff.passed is True

    def test_below_threshold(self):
        diff = VisualDiff(
            report_id="r1",
            report_name="report1",
            similarity_score=0.84,
            layout_match=True,
            data_match=True,
            style_match=True,
            differences=[],
            method="ssim",
        )
        assert diff.passed is False

    def test_summary_format(self):
        diff = VisualDiff(
            report_id="r1",
            report_name="report1",
            similarity_score=0.92,
            layout_match=True,
            data_match=True,
            style_match=True,
            differences=[],
            method="ai",
        )
        s = diff.summary()
        assert "report1" in s
        assert "92" in s or "0.92" in s


# ===================================================================
# VisualComparator
# ===================================================================


class TestVisualComparator:
    """Tests for visual comparator."""

    @pytest.mark.asyncio
    async def test_ssim_identical(self):
        comp = VisualComparator(use_ai=False)
        spec = ScreenshotSpec("r1", "report", 0, ViewportSize.DESKTOP)
        data = b"identical-data"
        src = Screenshot(spec=spec, image_data=data, width=100, height=100)
        tgt = Screenshot(spec=spec, image_data=data, width=100, height=100)
        pair = ScreenshotPair("r1", "report", src, tgt)
        diff = await comp.compare(pair)
        assert diff.similarity_score >= 0.99

    @pytest.mark.asyncio
    async def test_ssim_different(self):
        comp = VisualComparator(use_ai=False)
        spec = ScreenshotSpec("r1", "report", 0, ViewportSize.DESKTOP)
        src = Screenshot(spec=spec, image_data=b"data-a", width=100, height=100)
        tgt = Screenshot(spec=spec, image_data=b"data-b", width=100, height=100)
        pair = ScreenshotPair("r1", "report", src, tgt)
        diff = await comp.compare(pair)
        assert diff.similarity_score < 1.0


# ===================================================================
# VisualValidationReport
# ===================================================================


class TestVisualValidationReport:
    """Tests for validation report."""

    def test_all_passed(self):
        diffs = [
            VisualDiff(report_id="r1", report_name="r1", similarity_score=0.95,
                       layout_match=True, data_match=True, style_match=True, differences=[], method="ssim"),
            VisualDiff(report_id="r2", report_name="r2", similarity_score=0.90,
                       layout_match=True, data_match=True, style_match=True, differences=[], method="ssim"),
        ]
        report = VisualValidationReport(diffs=diffs, total=2, passed=2, failed=0)
        assert report.total == 2
        assert report.passed == 2
        assert report.failed == 0
        assert report.pass_rate == 1.0

    def test_mixed_results(self):
        diffs = [
            VisualDiff(report_id="r1", report_name="r1", similarity_score=0.95,
                       layout_match=True, data_match=True, style_match=True, differences=[], method="ssim"),
            VisualDiff(report_id="r2", report_name="r2", similarity_score=0.40,
                       layout_match=False, data_match=False, style_match=False,
                       differences=["total mismatch"], method="ssim"),
        ]
        report = VisualValidationReport(diffs=diffs, total=2, passed=1, failed=1)
        assert report.passed == 1
        assert report.failed == 1
        assert report.pass_rate == 0.5

    def test_empty_report(self):
        report = VisualValidationReport(diffs=[])
        assert report.total == 0
        assert report.pass_rate == 0.0

    def test_summary(self):
        diffs = [
            VisualDiff(report_id="r1", report_name="r1", similarity_score=0.95,
                       layout_match=True, data_match=True, style_match=True, differences=[], method="ssim"),
        ]
        report = VisualValidationReport(diffs=diffs, total=1, passed=1, failed=0)
        s = report.summary()
        assert "1" in s


# ===================================================================
# VisualValidationRunner
# ===================================================================


class TestVisualValidationRunner:
    """Tests for visual validation runner."""

    @pytest.mark.asyncio
    async def test_validate_report(self):
        runner = VisualValidationRunner()
        diff = await runner.validate_report(
            report_id="r1",
            report_name="Sales",
            source_url="http://oac/sales",
            target_url="http://pbi/sales",
        )
        assert isinstance(diff, VisualDiff)
        assert diff.report_id == "r1"

    @pytest.mark.asyncio
    async def test_validate_batch(self):
        runner = VisualValidationRunner()
        specs = [
            {"report_id": "r1", "report_name": "Sales", "source_url": "http://a", "target_url": "http://b"},
            {"report_id": "r2", "report_name": "Finance", "source_url": "http://c", "target_url": "http://d"},
        ]
        report = await runner.validate_batch(specs)
        assert isinstance(report, VisualValidationReport)
        assert report.total == 2
