"""DAX translation catalog — expanded function mappings & coverage reporting.

Provides:
- ``FunctionCategory`` — categories of OAC/OBIEE functions.
- ``TranslationEntry`` — a single OAC→DAX function mapping.
- ``TranslationCatalog`` — registry of all mappings with lookup.
- ``CoverageReport`` — measure translation coverage.
- ``ConfidenceCalibrator`` — compare LLM confidence vs human review outcomes.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Function categories
# ---------------------------------------------------------------------------


class FunctionCategory(str, Enum):
    AGGREGATE = "aggregate"
    TIME_INTELLIGENCE = "time_intelligence"
    STRING = "string"
    MATH = "math"
    DATE = "date"
    LOGICAL = "logical"
    FILTER = "filter"
    TABLE = "table"
    STATISTICAL = "statistical"
    INFORMATION = "information"
    LEVEL_BASED = "level_based"
    OTHER = "other"


class TranslationDifficulty(str, Enum):
    DIRECT = "direct"          # 1:1 mapping
    PARAMETRIC = "parametric"  # needs parameter rewriting
    COMPLEX = "complex"        # requires multi-expression DAX pattern
    UNSUPPORTED = "unsupported"


# ---------------------------------------------------------------------------
# Translation entry
# ---------------------------------------------------------------------------


@dataclass
class TranslationEntry:
    """A single OAC→DAX function mapping."""
    oac_function: str
    dax_function: str
    category: FunctionCategory
    difficulty: TranslationDifficulty = TranslationDifficulty.DIRECT
    description: str = ""
    oac_syntax: str = ""
    dax_syntax: str = ""
    example_oac: str = ""
    example_dax: str = ""
    notes: str = ""

    @property
    def is_supported(self) -> bool:
        return self.difficulty != TranslationDifficulty.UNSUPPORTED


# ---------------------------------------------------------------------------
# Translation catalog
# ---------------------------------------------------------------------------


class TranslationCatalog:
    """Registry of all OAC→DAX function mappings.

    Contains 80+ mappings organized by category.
    """

    def __init__(self) -> None:
        self._entries: dict[str, TranslationEntry] = {}
        self._load_builtins()

    def _load_builtins(self) -> None:
        """Load all built-in translation entries."""
        entries = [
            # --- Aggregates ---
            TranslationEntry("SUM", "SUM", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT,
                             example_oac="SUM(Sales.Amount)", example_dax="SUM('Sales'[Amount])"),
            TranslationEntry("COUNT", "COUNT", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT,
                             example_oac="COUNT(Orders.ID)", example_dax="COUNT('Orders'[ID])"),
            TranslationEntry("COUNTDISTINCT", "DISTINCTCOUNT", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT,
                             example_oac="COUNTDISTINCT(Customers.ID)", example_dax="DISTINCTCOUNT('Customers'[ID])"),
            TranslationEntry("AVG", "AVERAGE", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT),
            TranslationEntry("MIN", "MIN", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT),
            TranslationEntry("MAX", "MAX", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT),
            TranslationEntry("MEDIAN", "MEDIAN", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT),
            TranslationEntry("STDDEV", "STDEV.S", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT),
            TranslationEntry("VARIANCE", "VAR.S", FunctionCategory.AGGREGATE, TranslationDifficulty.DIRECT),
            TranslationEntry("COUNT_STAR", "COUNTROWS", FunctionCategory.AGGREGATE, TranslationDifficulty.PARAMETRIC,
                             notes="COUNT(*) becomes COUNTROWS(table)"),

            # --- Time Intelligence ---
            TranslationEntry("AGO", "DATEADD", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.PARAMETRIC,
                             example_oac="AGO(Sales.Amount, Time, 1, YEAR)",
                             example_dax="CALCULATE([Amount], DATEADD('Date'[Date], -1, YEAR))",
                             notes="AGO with period offset maps to DATEADD with negative offset"),
            TranslationEntry("TODATE", "DATESYTD", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.PARAMETRIC,
                             example_oac="TODATE(Sales.Amount, Time, YEAR)",
                             example_dax="CALCULATE([Amount], DATESYTD('Date'[Date]))"),
            TranslationEntry("PERIODROLLING", "DATESINPERIOD", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.COMPLEX,
                             notes="Rolling period requires DATESINPERIOD + CALCULATE"),
            TranslationEntry("PERIODTODATE", "TOTALYTD", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("SAMEPERIODLASTYEAR", "SAMEPERIODLASTYEAR", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("PARALLELPERIOD", "PARALLELPERIOD", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("DATESYTD", "DATESYTD", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("DATESMTD", "DATESMTD", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("DATESQTD", "DATESQTD", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("FIRSTDATE", "FIRSTDATE", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("LASTDATE", "LASTDATE", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("OPENINGBALANCEYEAR", "OPENINGBALANCEYEAR", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("CLOSINGBALANCEYEAR", "CLOSINGBALANCEYEAR", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("PREVIOUSYEAR", "PREVIOUSYEAR", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("NEXTYEAR", "NEXTYEAR", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("PREVIOUSMONTH", "PREVIOUSMONTH", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("NEXTMONTH", "NEXTMONTH", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("PREVIOUSQUARTER", "PREVIOUSQUARTER", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),
            TranslationEntry("NEXTQUARTER", "NEXTQUARTER", FunctionCategory.TIME_INTELLIGENCE, TranslationDifficulty.DIRECT),

            # --- String Functions ---
            TranslationEntry("UPPER", "UPPER", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("LOWER", "LOWER", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("TRIM", "TRIM", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("LENGTH", "LEN", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("SUBSTRING", "MID", FunctionCategory.STRING, TranslationDifficulty.PARAMETRIC,
                             notes="SUBSTRING(str, start, len) → MID(str, start, len)"),
            TranslationEntry("REPLACE", "SUBSTITUTE", FunctionCategory.STRING, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("CONCAT", "CONCATENATE", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("INSTR", "FIND", FunctionCategory.STRING, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("LPAD", "REPT", FunctionCategory.STRING, TranslationDifficulty.COMPLEX,
                             notes="LPAD requires REPT + RIGHT pattern"),
            TranslationEntry("RPAD", "REPT", FunctionCategory.STRING, TranslationDifficulty.COMPLEX),
            TranslationEntry("LEFT", "LEFT", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("RIGHT", "RIGHT", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("INITCAP", "PROPER", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("REGEXP", "CONTAINSSTRING", FunctionCategory.STRING, TranslationDifficulty.COMPLEX,
                             notes="OAC REGEXP maps roughly to CONTAINSSTRING for simple patterns"),
            TranslationEntry("UNICODE_CHAR", "UNICHAR", FunctionCategory.STRING, TranslationDifficulty.DIRECT),
            TranslationEntry("UNICODE_CODE", "UNICODE", FunctionCategory.STRING, TranslationDifficulty.DIRECT),

            # --- Math Functions ---
            TranslationEntry("ABS", "ABS", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("CEILING", "CEILING", FunctionCategory.MATH, TranslationDifficulty.PARAMETRIC,
                             notes="DAX CEILING takes significance parameter"),
            TranslationEntry("FLOOR", "FLOOR", FunctionCategory.MATH, TranslationDifficulty.PARAMETRIC,
                             notes="DAX FLOOR takes significance parameter"),
            TranslationEntry("ROUND", "ROUND", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("MOD", "MOD", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("POWER", "POWER", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("LOG", "LOG", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("LOG10", "LOG10", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("EXP", "EXP", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("SQRT", "SQRT", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("SIGN", "SIGN", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("TRUNCATE", "TRUNC", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("PI", "PI", FunctionCategory.MATH, TranslationDifficulty.DIRECT),
            TranslationEntry("RAND", "RAND", FunctionCategory.MATH, TranslationDifficulty.DIRECT),

            # --- Date Functions ---
            TranslationEntry("CURRENT_DATE", "TODAY", FunctionCategory.DATE, TranslationDifficulty.DIRECT),
            TranslationEntry("CURRENT_TIMESTAMP", "NOW", FunctionCategory.DATE, TranslationDifficulty.DIRECT),
            TranslationEntry("EXTRACT_YEAR", "YEAR", FunctionCategory.DATE, TranslationDifficulty.DIRECT),
            TranslationEntry("EXTRACT_MONTH", "MONTH", FunctionCategory.DATE, TranslationDifficulty.DIRECT),
            TranslationEntry("EXTRACT_DAY", "DAY", FunctionCategory.DATE, TranslationDifficulty.DIRECT),
            TranslationEntry("EXTRACT_HOUR", "HOUR", FunctionCategory.DATE, TranslationDifficulty.DIRECT),
            TranslationEntry("EXTRACT_MINUTE", "MINUTE", FunctionCategory.DATE, TranslationDifficulty.DIRECT),
            TranslationEntry("EXTRACT_SECOND", "SECOND", FunctionCategory.DATE, TranslationDifficulty.DIRECT),
            TranslationEntry("ADD_MONTHS", "EDATE", FunctionCategory.DATE, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("TIMESTAMPADD", "DATEADD", FunctionCategory.DATE, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("TIMESTAMPDIFF", "DATEDIFF", FunctionCategory.DATE, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("MONTHNAME", "FORMAT", FunctionCategory.DATE, TranslationDifficulty.PARAMETRIC,
                             notes="FORMAT(date, \"MMMM\")"),
            TranslationEntry("DAYNAME", "FORMAT", FunctionCategory.DATE, TranslationDifficulty.PARAMETRIC,
                             notes="FORMAT(date, \"dddd\")"),
            TranslationEntry("EOMONTH", "EOMONTH", FunctionCategory.DATE, TranslationDifficulty.DIRECT),

            # --- Logical Functions ---
            TranslationEntry("CASE", "SWITCH", FunctionCategory.LOGICAL, TranslationDifficulty.PARAMETRIC,
                             notes="CASE WHEN → SWITCH(TRUE, ...)"),
            TranslationEntry("IIF", "IF", FunctionCategory.LOGICAL, TranslationDifficulty.DIRECT),
            TranslationEntry("IFNULL", "COALESCE", FunctionCategory.LOGICAL, TranslationDifficulty.DIRECT),
            TranslationEntry("NVL", "COALESCE", FunctionCategory.LOGICAL, TranslationDifficulty.DIRECT),
            TranslationEntry("NULLIF", "IF", FunctionCategory.LOGICAL, TranslationDifficulty.PARAMETRIC,
                             notes="NULLIF(a, b) → IF(a = b, BLANK(), a)"),
            TranslationEntry("COALESCE", "COALESCE", FunctionCategory.LOGICAL, TranslationDifficulty.DIRECT),
            TranslationEntry("ISBLANK", "ISBLANK", FunctionCategory.LOGICAL, TranslationDifficulty.DIRECT),
            TranslationEntry("ISNULL", "ISBLANK", FunctionCategory.LOGICAL, TranslationDifficulty.DIRECT),

            # --- Filter / Table Functions ---
            TranslationEntry("FILTER", "FILTER", FunctionCategory.FILTER, TranslationDifficulty.DIRECT),
            TranslationEntry("EVALUATE_PREDICATE", "CALCULATETABLE", FunctionCategory.FILTER, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("ALL", "ALL", FunctionCategory.FILTER, TranslationDifficulty.DIRECT),
            TranslationEntry("ALLEXCEPT", "ALLEXCEPT", FunctionCategory.FILTER, TranslationDifficulty.DIRECT),
            TranslationEntry("RELATED", "RELATED", FunctionCategory.TABLE, TranslationDifficulty.DIRECT),
            TranslationEntry("RELATEDTABLE", "RELATEDTABLE", FunctionCategory.TABLE, TranslationDifficulty.DIRECT),
            TranslationEntry("VALUES", "VALUES", FunctionCategory.TABLE, TranslationDifficulty.DIRECT),
            TranslationEntry("DISTINCT", "DISTINCT", FunctionCategory.TABLE, TranslationDifficulty.DIRECT),

            # --- Statistical ---
            TranslationEntry("PERCENTILE", "PERCENTILEX.INC", FunctionCategory.STATISTICAL, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("RANK", "RANKX", FunctionCategory.STATISTICAL, TranslationDifficulty.COMPLEX,
                             notes="Requires RANKX(ALL(Table), [Measure])"),
            TranslationEntry("NTILE", "RANKX", FunctionCategory.STATISTICAL, TranslationDifficulty.COMPLEX),
            TranslationEntry("TOPN", "TOPN", FunctionCategory.STATISTICAL, TranslationDifficulty.DIRECT),

            # --- Level-based measures ---
            TranslationEntry("AGGREGATE_AT_LEVEL", "CALCULATE", FunctionCategory.LEVEL_BASED, TranslationDifficulty.COMPLEX,
                             notes="Uses CALCULATE + ALLEXCEPT to pin aggregation level"),
            TranslationEntry("SHARE", "DIVIDE", FunctionCategory.LEVEL_BASED, TranslationDifficulty.COMPLEX,
                             notes="Share of parent = DIVIDE([Measure], CALCULATE([Measure], ALL(dim)))"),

            # --- Information ---
            TranslationEntry("CAST", "CONVERT", FunctionCategory.INFORMATION, TranslationDifficulty.PARAMETRIC),
            TranslationEntry("TYPEOF", "ISTEXT", FunctionCategory.INFORMATION, TranslationDifficulty.COMPLEX,
                             notes="No direct equivalent; use IS* functions"),
        ]

        for entry in entries:
            self._entries[entry.oac_function.upper()] = entry

    def lookup(self, oac_function: str) -> TranslationEntry | None:
        """Look up a translation for an OAC function."""
        return self._entries.get(oac_function.upper())

    def translate(self, oac_function: str) -> str | None:
        """Get the DAX equivalent of an OAC function."""
        entry = self.lookup(oac_function)
        return entry.dax_function if entry else None

    def add(self, entry: TranslationEntry) -> None:
        """Register a custom translation entry."""
        self._entries[entry.oac_function.upper()] = entry

    def remove(self, oac_function: str) -> bool:
        """Remove a translation entry."""
        key = oac_function.upper()
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def by_category(self, category: FunctionCategory) -> list[TranslationEntry]:
        """Get all entries for a category."""
        return [e for e in self._entries.values() if e.category == category]

    def by_difficulty(self, difficulty: TranslationDifficulty) -> list[TranslationEntry]:
        """Get all entries for a difficulty level."""
        return [e for e in self._entries.values() if e.difficulty == difficulty]

    @property
    def total_count(self) -> int:
        return len(self._entries)

    @property
    def supported_count(self) -> int:
        return sum(1 for e in self._entries.values() if e.is_supported)

    def all_entries(self) -> list[TranslationEntry]:
        return sorted(self._entries.values(), key=lambda e: (e.category.value, e.oac_function))

    def search(self, pattern: str) -> list[TranslationEntry]:
        """Search entries by function name pattern."""
        regex = re.compile(pattern, re.IGNORECASE)
        return [e for e in self._entries.values() if regex.search(e.oac_function)]


# ---------------------------------------------------------------------------
# Coverage report
# ---------------------------------------------------------------------------


@dataclass
class CoverageResult:
    """Result of a translation coverage analysis."""
    total_source_functions: int = 0
    mapped_functions: int = 0
    unmapped_functions: list[str] = field(default_factory=list)
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)
    by_difficulty: dict[str, int] = field(default_factory=dict)

    @property
    def coverage_pct(self) -> float:
        if self.total_source_functions == 0:
            return 100.0
        return (self.mapped_functions / self.total_source_functions) * 100.0

    def summary(self) -> str:
        return (
            f"Translation Coverage: {self.mapped_functions}/{self.total_source_functions} "
            f"({self.coverage_pct:.1f}%), "
            f"{len(self.unmapped_functions)} unmapped"
        )


class CoverageReport:
    """Measure DAX translation coverage against a set of source functions."""

    def __init__(self, catalog: TranslationCatalog) -> None:
        self._catalog = catalog

    def analyze(self, source_functions: list[str]) -> CoverageResult:
        """Analyze coverage for a set of source functions."""
        result = CoverageResult(total_source_functions=len(source_functions))

        for func in source_functions:
            entry = self._catalog.lookup(func)
            if entry and entry.is_supported:
                result.mapped_functions += 1
                cat = entry.category.value
                if cat not in result.by_category:
                    result.by_category[cat] = {"mapped": 0, "total": 0}
                result.by_category[cat]["mapped"] += 1
                result.by_category[cat]["total"] += 1

                diff = entry.difficulty.value
                result.by_difficulty[diff] = result.by_difficulty.get(diff, 0) + 1
            else:
                result.unmapped_functions.append(func)
                # Still count in category totals
                cat = "unknown"
                if cat not in result.by_category:
                    result.by_category[cat] = {"mapped": 0, "total": 0}
                result.by_category[cat]["total"] += 1

        return result

    def catalog_summary(self) -> dict[str, Any]:
        """Summarize the catalog itself."""
        by_cat: dict[str, int] = {}
        by_diff: dict[str, int] = {}
        for entry in self._catalog.all_entries():
            cat = entry.category.value
            by_cat[cat] = by_cat.get(cat, 0) + 1
            diff = entry.difficulty.value
            by_diff[diff] = by_diff.get(diff, 0) + 1
        return {
            "total": self._catalog.total_count,
            "supported": self._catalog.supported_count,
            "by_category": by_cat,
            "by_difficulty": by_diff,
        }


# ---------------------------------------------------------------------------
# Confidence calibrator
# ---------------------------------------------------------------------------


@dataclass
class CalibrationSample:
    """A single calibration sample: LLM prediction vs human review."""
    expression: str
    llm_confidence: float  # 0.0 to 1.0
    human_correct: bool  # did human confirm the translation was correct?
    llm_translation: str = ""
    human_translation: str = ""


@dataclass
class CalibrationResult:
    """Result of confidence calibration."""
    total_samples: int = 0
    correct_count: int = 0
    calibration_error: float = 0.0  # mean |confidence - accuracy| across bins
    bins: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.correct_count / self.total_samples

    def summary(self) -> str:
        return (
            f"Calibration: {self.correct_count}/{self.total_samples} correct "
            f"({self.accuracy:.1%}), calibration error={self.calibration_error:.3f}"
        )


class ConfidenceCalibrator:
    """Compare LLM confidence scores vs human review outcomes.

    Groups samples into confidence bins and measures calibration error.
    """

    def __init__(self, num_bins: int = 5) -> None:
        self.num_bins = num_bins
        self._samples: list[CalibrationSample] = []

    def add_sample(self, sample: CalibrationSample) -> None:
        self._samples.append(sample)

    def add_samples(self, samples: list[CalibrationSample]) -> None:
        self._samples.extend(samples)

    def calibrate(self) -> CalibrationResult:
        """Run calibration analysis on collected samples."""
        if not self._samples:
            return CalibrationResult()

        result = CalibrationResult(
            total_samples=len(self._samples),
            correct_count=sum(1 for s in self._samples if s.human_correct),
        )

        # Create bins
        bin_size = 1.0 / self.num_bins
        total_error = 0.0

        for i in range(self.num_bins):
            low = i * bin_size
            high = (i + 1) * bin_size

            bin_samples = [
                s for s in self._samples
                if low <= s.llm_confidence < high or (i == self.num_bins - 1 and s.llm_confidence == high)
            ]

            if bin_samples:
                avg_confidence = sum(s.llm_confidence for s in bin_samples) / len(bin_samples)
                avg_accuracy = sum(1 for s in bin_samples if s.human_correct) / len(bin_samples)
                bin_error = abs(avg_confidence - avg_accuracy)
                total_error += bin_error * len(bin_samples)

                result.bins.append({
                    "range": f"{low:.1f}-{high:.1f}",
                    "count": len(bin_samples),
                    "avg_confidence": round(avg_confidence, 3),
                    "avg_accuracy": round(avg_accuracy, 3),
                    "error": round(bin_error, 3),
                })

        result.calibration_error = total_error / len(self._samples) if self._samples else 0.0
        return result

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()
