"""Tests for Phase 34 — DAX Translation Catalog."""

from __future__ import annotations

import pytest

from src.core.translation_catalog import (
    CalibrationResult,
    CalibrationSample,
    ConfidenceCalibrator,
    CoverageReport,
    CoverageResult,
    FunctionCategory,
    TranslationCatalog,
    TranslationDifficulty,
    TranslationEntry,
)


# ===================================================================
# TranslationEntry
# ===================================================================


class TestTranslationEntry:
    def test_basic_creation(self):
        e = TranslationEntry("SUM", "SUM", FunctionCategory.AGGREGATE)
        assert e.oac_function == "SUM"
        assert e.dax_function == "SUM"
        assert e.category == FunctionCategory.AGGREGATE

    def test_is_supported_direct(self):
        e = TranslationEntry("SUM", "SUM", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT)
        assert e.is_supported is True

    def test_is_supported_complex(self):
        e = TranslationEntry("RANK", "RANKX", FunctionCategory.STATISTICAL, TranslationDifficulty.COMPLEX)
        assert e.is_supported is True

    def test_not_supported(self):
        e = TranslationEntry("FANCY", "", FunctionCategory.OTHER, TranslationDifficulty.UNSUPPORTED)
        assert e.is_supported is False

    def test_with_examples(self):
        e = TranslationEntry(
            "AGO", "DATEADD", FunctionCategory.TIME_INTELLIGENCE,
            TranslationDifficulty.PARAMETRIC,
            example_oac="AGO(Sales.Amount, Time, 1, YEAR)",
            example_dax="CALCULATE([Amount], DATEADD('Date'[Date], -1, YEAR))",
        )
        assert "AGO" in e.example_oac
        assert "DATEADD" in e.example_dax


# ===================================================================
# TranslationCatalog
# ===================================================================


class TestTranslationCatalog:
    def test_catalog_loads_builtins(self):
        cat = TranslationCatalog()
        assert cat.total_count >= 80

    def test_all_builtins_supported(self):
        cat = TranslationCatalog()
        assert cat.supported_count == cat.total_count  # no UNSUPPORTED in builtins

    def test_lookup_exact(self):
        cat = TranslationCatalog()
        e = cat.lookup("SUM")
        assert e is not None
        assert e.dax_function == "SUM"

    def test_lookup_case_insensitive(self):
        cat = TranslationCatalog()
        e1 = cat.lookup("sum")
        e2 = cat.lookup("SUM")
        assert e1 is not None
        assert e1 == e2

    def test_lookup_missing(self):
        cat = TranslationCatalog()
        assert cat.lookup("NONEXISTENT_FUNC") is None

    def test_translate_returns_dax(self):
        cat = TranslationCatalog()
        assert cat.translate("COUNTDISTINCT") == "DISTINCTCOUNT"

    def test_translate_returns_none_for_missing(self):
        cat = TranslationCatalog()
        assert cat.translate("XYZ") is None

    def test_add_custom_entry(self):
        cat = TranslationCatalog()
        initial = cat.total_count
        cat.add(TranslationEntry("MY_FUNC", "MY_DAX", FunctionCategory.OTHER))
        assert cat.total_count == initial + 1
        assert cat.lookup("MY_FUNC") is not None

    def test_remove_entry(self):
        cat = TranslationCatalog()
        initial = cat.total_count
        assert cat.remove("SUM") is True
        assert cat.total_count == initial - 1
        assert cat.lookup("SUM") is None

    def test_remove_missing(self):
        cat = TranslationCatalog()
        assert cat.remove("NONEXISTENT") is False

    def test_by_category_aggregate(self):
        cat = TranslationCatalog()
        aggs = cat.by_category(FunctionCategory.AGGREGATE)
        assert len(aggs) >= 8
        assert all(e.category == FunctionCategory.AGGREGATE for e in aggs)

    def test_by_category_time_intelligence(self):
        cat = TranslationCatalog()
        ti = cat.by_category(FunctionCategory.TIME_INTELLIGENCE)
        assert len(ti) >= 10

    def test_by_difficulty_direct(self):
        cat = TranslationCatalog()
        directs = cat.by_difficulty(TranslationDifficulty.DIRECT)
        assert len(directs) >= 30

    def test_by_difficulty_complex(self):
        cat = TranslationCatalog()
        cplx = cat.by_difficulty(TranslationDifficulty.COMPLEX)
        assert len(cplx) >= 5

    def test_all_entries_sorted(self):
        cat = TranslationCatalog()
        entries = cat.all_entries()
        keys = [(e.category.value, e.oac_function) for e in entries]
        assert keys == sorted(keys)

    def test_search_by_pattern(self):
        cat = TranslationCatalog()
        results = cat.search("DATE")
        assert len(results) >= 5
        assert all("DATE" in e.oac_function.upper() for e in results)

    def test_search_regex(self):
        cat = TranslationCatalog()
        results = cat.search("^SUM$")
        assert len(results) == 1
        assert results[0].oac_function == "SUM"

    def test_has_key_functions(self):
        """Verify specific important functions are in the catalog."""
        cat = TranslationCatalog()
        must_have = ["SUM", "AVG", "COUNT", "AGO", "TODATE", "CASE", "IIF", "FILTER", "RANK"]
        for func in must_have:
            assert cat.lookup(func) is not None, f"{func} missing from catalog"

    def test_categories_cover_all_expected(self):
        cat = TranslationCatalog()
        categories_with_entries = {e.category for e in cat.all_entries()}
        expected = {
            FunctionCategory.AGGREGATE, FunctionCategory.TIME_INTELLIGENCE,
            FunctionCategory.STRING, FunctionCategory.MATH,
            FunctionCategory.DATE, FunctionCategory.LOGICAL,
            FunctionCategory.FILTER, FunctionCategory.TABLE,
            FunctionCategory.STATISTICAL, FunctionCategory.LEVEL_BASED,
            FunctionCategory.INFORMATION,
        }
        assert expected.issubset(categories_with_entries)


# ===================================================================
# CoverageReport
# ===================================================================


class TestCoverageReport:
    def test_full_coverage(self):
        cat = TranslationCatalog()
        report = CoverageReport(cat)
        result = report.analyze(["SUM", "AVG", "COUNT"])
        assert result.coverage_pct == 100.0
        assert result.mapped_functions == 3
        assert len(result.unmapped_functions) == 0

    def test_partial_coverage(self):
        cat = TranslationCatalog()
        report = CoverageReport(cat)
        result = report.analyze(["SUM", "UNKNOWN_FUNC"])
        assert result.coverage_pct == 50.0
        assert result.mapped_functions == 1
        assert "UNKNOWN_FUNC" in result.unmapped_functions

    def test_zero_coverage(self):
        cat = TranslationCatalog()
        report = CoverageReport(cat)
        result = report.analyze(["FOO", "BAR"])
        assert result.coverage_pct == 0.0

    def test_empty_source(self):
        cat = TranslationCatalog()
        report = CoverageReport(cat)
        result = report.analyze([])
        assert result.coverage_pct == 100.0  # nothing to map = 100%

    def test_by_category_populated(self):
        cat = TranslationCatalog()
        report = CoverageReport(cat)
        result = report.analyze(["SUM", "AVG", "AGO"])
        assert "aggregate" in result.by_category
        assert "time_intelligence" in result.by_category

    def test_by_difficulty_populated(self):
        cat = TranslationCatalog()
        report = CoverageReport(cat)
        result = report.analyze(["SUM", "AGO"])
        assert "direct" in result.by_difficulty
        assert "parametric" in result.by_difficulty

    def test_summary_string(self):
        result = CoverageResult(total_source_functions=10, mapped_functions=8, unmapped_functions=["A", "B"])
        s = result.summary()
        assert "8/10" in s
        assert "80.0%" in s

    def test_catalog_summary(self):
        cat = TranslationCatalog()
        report = CoverageReport(cat)
        summary = report.catalog_summary()
        assert summary["total"] >= 80
        assert "by_category" in summary
        assert "by_difficulty" in summary


# ===================================================================
# ConfidenceCalibrator
# ===================================================================


class TestConfidenceCalibrator:
    def _make_samples(self) -> list[CalibrationSample]:
        return [
            CalibrationSample("SUM(x)", 0.95, True),
            CalibrationSample("AVG(x)", 0.90, True),
            CalibrationSample("AGO(x)", 0.70, True),
            CalibrationSample("RANK(x)", 0.60, False),
            CalibrationSample("LPAD(x)", 0.40, False),
            CalibrationSample("CUSTOM(x)", 0.20, False),
        ]

    def test_add_sample(self):
        cal = ConfidenceCalibrator()
        cal.add_sample(CalibrationSample("SUM", 0.9, True))
        assert cal.sample_count == 1

    def test_add_samples_batch(self):
        cal = ConfidenceCalibrator()
        cal.add_samples(self._make_samples())
        assert cal.sample_count == 6

    def test_calibrate_empty(self):
        cal = ConfidenceCalibrator()
        result = cal.calibrate()
        assert result.total_samples == 0
        assert result.accuracy == 0.0

    def test_calibrate_basic(self):
        cal = ConfidenceCalibrator(num_bins=5)
        cal.add_samples(self._make_samples())
        result = cal.calibrate()
        assert result.total_samples == 6
        assert result.correct_count == 3
        assert result.accuracy == 0.5

    def test_calibrate_bins_exist(self):
        cal = ConfidenceCalibrator(num_bins=5)
        cal.add_samples(self._make_samples())
        result = cal.calibrate()
        assert len(result.bins) > 0
        for b in result.bins:
            assert "range" in b
            assert "count" in b
            assert "avg_confidence" in b
            assert "avg_accuracy" in b

    def test_calibration_error_bounded(self):
        cal = ConfidenceCalibrator(num_bins=5)
        cal.add_samples(self._make_samples())
        result = cal.calibrate()
        assert 0.0 <= result.calibration_error <= 1.0

    def test_perfect_calibration(self):
        """When confidence matches accuracy exactly."""
        cal = ConfidenceCalibrator(num_bins=2)
        # All high-confidence correct, all low-confidence wrong
        samples = [
            CalibrationSample("a", 0.9, True),
            CalibrationSample("b", 0.8, True),
            CalibrationSample("c", 0.1, False),
            CalibrationSample("d", 0.2, False),
        ]
        cal.add_samples(samples)
        result = cal.calibrate()
        # Should have low calibration error
        assert result.calibration_error < 0.3

    def test_summary_string(self):
        result = CalibrationResult(total_samples=10, correct_count=8, calibration_error=0.05)
        s = result.summary()
        assert "8/10" in s
        assert "80.0%" in s

    def test_clear(self):
        cal = ConfidenceCalibrator()
        cal.add_samples(self._make_samples())
        cal.clear()
        assert cal.sample_count == 0

    def test_custom_bin_count(self):
        cal = ConfidenceCalibrator(num_bins=10)
        cal.add_samples(self._make_samples())
        result = cal.calibrate()
        # Should have at most 10 bins, but only bins with data
        assert len(result.bins) <= 10


# ===================================================================
# Enum tests
# ===================================================================


class TestEnums:
    def test_function_category_values(self):
        assert FunctionCategory.AGGREGATE.value == "aggregate"
        assert FunctionCategory.TIME_INTELLIGENCE.value == "time_intelligence"

    def test_difficulty_values(self):
        assert TranslationDifficulty.DIRECT.value == "direct"
        assert TranslationDifficulty.UNSUPPORTED.value == "unsupported"

    def test_all_categories_string(self):
        for cat in FunctionCategory:
            assert isinstance(cat.value, str)

    def test_all_difficulties_string(self):
        for diff in TranslationDifficulty:
            assert isinstance(diff.value, str)
