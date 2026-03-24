"""Cognos → Semantic Model bridge.

Converts parsed Cognos report specifications (``ParsedReportSpec``)
into ``SemanticModelIR`` for TMDL generation.

Mapping strategy
~~~~~~~~~~~~~~~~
- Each **Cognos package** maps to one ``SemanticModelIR``.
- Each **query subject** becomes a ``LogicalTable``.
- Each **data item** becomes a ``LogicalColumn`` (measure if aggregated).
- **Dimensions** become dimension tables with hierarchies.
- **Prompts** are converted to slicer/parameter definitions.
- **Detail filters** are converted to RLS role definitions.
- **Namespaces** map to display folders.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.agents.semantic.rpd_model_parser import (
    ColumnKind,
    Hierarchy,
    HierarchyLevel,
    JoinCardinality,
    LogicalColumn,
    LogicalJoin,
    LogicalTable,
    SemanticModelIR,
    SubjectArea,
)
from src.connectors.cognos_connector import (
    COGNOS_TO_FABRIC_TYPE,
    COGNOS_TO_TMDL_MAPPING,
    CalcTranslationResult,
    CognosDataItem,
    CognosExpressionTranslator,
    CognosPackage,
    CognosPrompt,
    CognosQuery,
    CognosReport,
    ParsedReportSpec,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CognosSlicerDefinition:
    """A slicer/parameter derived from a Cognos prompt."""

    name: str
    prompt_type: str
    parameter_name: str
    caption: str
    required: bool = False
    multi_select: bool = False
    pbi_type: str = "slicer"


@dataclass
class CognosRlsRole:
    """An RLS role derived from a Cognos detail filter."""

    name: str
    filter_expression: str
    tables: list[str] = field(default_factory=list)


@dataclass
class CognosConversionResult:
    """Result of converting Cognos specs to SemanticModelIR."""

    ir: SemanticModelIR
    slicers: list[CognosSlicerDefinition] = field(default_factory=list)
    rls_roles: list[CognosRlsRole] = field(default_factory=list)
    calc_translations: list[CalcTranslationResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    review_items: list[str] = field(default_factory=list)

    @property
    def table_count(self) -> int:
        return len(self.ir.tables)

    @property
    def measure_count(self) -> int:
        return sum(len(t.measures) for t in self.ir.tables)

    @property
    def relationship_count(self) -> int:
        return len(self.ir.joins)


# ---------------------------------------------------------------------------
# Core converter
# ---------------------------------------------------------------------------

_AGGREGATE_FUNCTIONS = {"total", "count", "average", "minimum", "maximum",
                        "aggregate", "median", "standard-deviation", "variance"}


class CognosToSemanticModelConverter:
    """Convert Cognos report specifications → SemanticModelIR."""

    def __init__(self) -> None:
        self._translator = CognosExpressionTranslator()

    def convert(
        self,
        spec: ParsedReportSpec,
        *,
        model_name: str | None = None,
    ) -> CognosConversionResult:
        """Convert a parsed Cognos report spec to SemanticModelIR."""
        warnings: list[str] = []
        review_items: list[str] = []
        calc_translations: list[CalcTranslationResult] = []

        name = model_name or (spec.reports[0].name if spec.reports else "CognosModel")

        tables: list[LogicalTable] = []
        joins: list[LogicalJoin] = []
        slicers: list[CognosSlicerDefinition] = []
        rls_roles: list[CognosRlsRole] = []

        # Build tables from queries
        for report in spec.reports:
            for query in report.queries:
                table, measures, translations = self._query_to_table(query)
                tables.append(table)
                calc_translations.extend(translations)

            # Convert prompts → slicers
            for prompt in report.prompts:
                slicer = self._prompt_to_slicer(prompt)
                slicers.append(slicer)

            # Convert detail filters → RLS
            for query in report.queries:
                for flt_expr in query.detail_filters:
                    role = self._filter_to_rls(query.name, flt_expr)
                    rls_roles.append(role)

        # Build joins between tables sharing common column names
        for i, t1 in enumerate(tables):
            for t2 in tables[i + 1:]:
                join = self._infer_join(t1, t2)
                if join:
                    joins.append(join)

        # Subject area
        sa = SubjectArea(
            name=name,
            tables=[t.name for t in tables],
            columns={t.name: [c.name for c in t.columns] for t in tables},
            description=f"Converted from Cognos reports: {', '.join(spec.report_names)}",
        )

        ir = SemanticModelIR(
            tables=tables,
            joins=joins,
            subject_areas=[sa],
            model_name=name,
            description=f"Migrated from IBM Cognos Analytics",
        )

        return CognosConversionResult(
            ir=ir,
            slicers=slicers,
            rls_roles=rls_roles,
            calc_translations=calc_translations,
            warnings=warnings,
            review_items=review_items,
        )

    def _query_to_table(
        self, query: CognosQuery
    ) -> tuple[LogicalTable, list[LogicalColumn], list[CalcTranslationResult]]:
        """Convert a Cognos query to a LogicalTable."""
        columns: list[LogicalColumn] = []
        measures: list[LogicalColumn] = []
        translations: list[CalcTranslationResult] = []

        for item in query.data_items:
            is_measure = (
                item.aggregate in _AGGREGATE_FUNCTIONS
                or item.usage == "fact"
                and item.expression
                and any(agg in item.expression.lower() for agg in _AGGREGATE_FUNCTIONS)
            )

            if item.expression:
                result = self._translator.translate(item)
                translations.append(result)
                dax_expr = result.dax_expression
            else:
                dax_expr = ""

            col = LogicalColumn(
                name=item.name,
                data_type=COGNOS_TO_FABRIC_TYPE.get(item.data_type, "string"),
                expression=dax_expr if is_measure else "",
                kind=ColumnKind.MEASURE if is_measure else ColumnKind.DIRECT,
                display_folder=query.name,
                description=f"From Cognos data item: {item.label or item.name}",
                aggregation=item.aggregate if is_measure else "",
            )
            columns.append(col)

        # Add a key column
        key = LogicalColumn(
            name=f"{query.name}Key",
            data_type="int64",
            kind=ColumnKind.KEY,
            description=f"Primary key for {query.name}",
        )
        columns.insert(0, key)

        table = LogicalTable(
            name=query.name,
            columns=columns,
            physical_sources=[f"cognos.{query.name}"],
            description=f"From Cognos query: {query.name}",
            metadata={"cognos_package_ref": query.package_ref},
        )

        return table, measures, translations

    def _prompt_to_slicer(self, prompt: CognosPrompt) -> CognosSlicerDefinition:
        """Convert a Cognos prompt to a slicer definition."""
        from src.connectors.cognos_connector import COGNOS_PROMPT_TO_PBI
        pbi_type = COGNOS_PROMPT_TO_PBI.get(prompt.prompt_type, "slicer")
        return CognosSlicerDefinition(
            name=prompt.name,
            prompt_type=prompt.prompt_type,
            parameter_name=prompt.parameter_name,
            caption=prompt.caption,
            required=prompt.required,
            multi_select=prompt.multi_select,
            pbi_type=pbi_type,
        )

    def _filter_to_rls(self, query_name: str, filter_expr: str) -> CognosRlsRole:
        """Convert a Cognos detail filter to an RLS role."""
        result = self._translator.translate_expression(filter_expr, source_name=query_name)
        return CognosRlsRole(
            name=f"RLS_{query_name}",
            filter_expression=result.dax_expression,
            tables=[query_name],
        )

    def _infer_join(self, t1: LogicalTable, t2: LogicalTable) -> LogicalJoin | None:
        """Infer a join between two tables based on matching key column names."""
        t1_cols = {c.name for c in t1.columns}
        t2_cols = {c.name for c in t2.columns}

        shared_keys = [
            c.name for c in t1.columns
            if c.kind == ColumnKind.KEY and c.name in t2_cols
        ]
        if not shared_keys:
            # Look for FK pattern: t2.name + "Key" in t1
            fk_name = f"{t2.name}Key"
            if fk_name in t1_cols and any(c.name == fk_name for c in t2.columns):
                return LogicalJoin(
                    from_table=t1.name,
                    to_table=t2.name,
                    from_column=fk_name,
                    to_column=fk_name,
                    join_type="left",
                    cardinality=JoinCardinality.MANY_TO_ONE,
                    is_active=True,
                )
            return None

        col = shared_keys[0]
        return LogicalJoin(
            from_table=t1.name,
            to_table=t2.name,
            from_column=col,
            to_column=col,
            join_type="inner",
            cardinality=JoinCardinality.MANY_TO_ONE,
            is_active=True,
        )
