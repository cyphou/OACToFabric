"""Qlik → Semantic Model bridge.

Converts a ``QlikApp`` into ``SemanticModelIR`` for TMDL generation.

Mapping strategy
~~~~~~~~~~~~~~~~
- Each **Qlik table** → ``LogicalTable``.
- Each **Qlik field** → ``LogicalColumn``.
- **Master measures** → DAX measures (translated via ``QlikExpressionTranslator``).
- **Master dimensions** → dimension columns; drill-down dims → ``Hierarchy``.
- **Variables** → DAX variables / What-if parameters.
- **Section Access** rules → RLS role definitions.
- **Key fields** linking tables → ``LogicalJoin``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

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
from src.connectors.qlik_connector import (
    QLIK_TO_FABRIC_TYPE,
    CalcTranslationResult,
    QlikApp,
    QlikDimension,
    QlikExpressionTranslator,
    QlikField,
    QlikMeasure,
    QlikTable,
    QlikVariable,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class QlikRlsRole:
    """An RLS role derived from Qlik Section Access."""

    name: str
    filter_expression: str
    tables: list[str] = field(default_factory=list)


@dataclass
class QlikWhatsIfParameter:
    """A What-if parameter from a Qlik variable."""

    name: str
    definition: str
    dax_variable: str = ""


@dataclass
class QlikConversionResult:
    """Result of converting a Qlik app to SemanticModelIR."""

    ir: SemanticModelIR
    rls_roles: list[QlikRlsRole] = field(default_factory=list)
    whatif_parameters: list[QlikWhatsIfParameter] = field(default_factory=list)
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


class QlikToSemanticModelConverter:
    """Convert a Qlik app → SemanticModelIR for TMDL generation."""

    def __init__(self) -> None:
        self._translator = QlikExpressionTranslator()

    def convert(
        self,
        app: QlikApp,
        *,
        model_name: str | None = None,
    ) -> QlikConversionResult:
        """Convert a full Qlik app to a SemanticModelIR."""
        warnings: list[str] = []
        review_items: list[str] = []
        calc_translations: list[CalcTranslationResult] = []

        name = model_name or app.name or "QlikModel"

        # 1. Convert tables
        tables: list[LogicalTable] = []
        for qt in app.tables:
            table = self._table_to_logical(qt)
            tables.append(table)

        # 2. Add master measures to first table (or create a measures table)
        measures_table = tables[0] if tables else LogicalTable(
            name="Measures",
            columns=[LogicalColumn(name="MeasuresKey", data_type="int64", kind=ColumnKind.KEY)],
        )
        if not tables:
            tables.append(measures_table)

        for measure in app.measures:
            result = self._translator.translate(measure)
            calc_translations.append(result)
            col = LogicalColumn(
                name=measure.name,
                data_type="double",
                expression=result.dax_expression,
                kind=ColumnKind.MEASURE,
                display_folder="Measures",
                description=measure.description or f"From Qlik: {measure.expression}",
                format_string=measure.number_format,
            )
            measures_table.columns.append(col)
            if result.confidence < 0.5:
                review_items.append(
                    f"Low confidence ({result.confidence:.0%}) translating '{measure.name}': {result.warnings}"
                )

        # 3. Add master dimensions as hierarchies
        for dim in app.dimensions:
            self._add_dimension(dim, tables, warnings)

        # 4. Infer joins from key fields
        joins = self._infer_joins(tables)

        # 5. Convert variables → What-if parameters
        whatif: list[QlikWhatsIfParameter] = []
        for var in app.variables:
            result = self._translator.translate_expression(var.definition, source_name=var.name)
            calc_translations.append(result)
            whatif.append(QlikWhatsIfParameter(
                name=var.name,
                definition=var.definition,
                dax_variable=f'VAR __{var.name} = {result.dax_expression}',
            ))

        # 6. Subject area
        sa = SubjectArea(
            name=name,
            tables=[t.name for t in tables],
            columns={t.name: [c.name for c in t.columns] for t in tables},
            description=f"Converted from Qlik app: {app.name}",
        )

        ir = SemanticModelIR(
            tables=tables,
            joins=joins,
            subject_areas=[sa],
            model_name=name,
            description=f"Migrated from Qlik: {app.name}",
        )

        return QlikConversionResult(
            ir=ir,
            rls_roles=[],
            whatif_parameters=whatif,
            calc_translations=calc_translations,
            warnings=warnings,
            review_items=review_items,
        )

    def _table_to_logical(self, qt: QlikTable) -> LogicalTable:
        """Convert a Qlik table to a LogicalTable."""
        columns: list[LogicalColumn] = []

        # Key column
        columns.append(LogicalColumn(
            name=f"{qt.name}Key",
            data_type="int64",
            kind=ColumnKind.KEY,
            description=f"Primary key for {qt.name}",
        ))

        for qf in qt.fields:
            col = LogicalColumn(
                name=qf.name,
                data_type=QLIK_TO_FABRIC_TYPE.get(qf.data_type, "string"),
                expression=qf.expression,
                kind=ColumnKind.KEY if qf.is_key else ColumnKind.DIRECT,
                description=qf.comment or "",
            )
            columns.append(col)

        return LogicalTable(
            name=qt.name,
            columns=columns,
            physical_sources=[f"qlik.{qt.source_connection or qt.name}"],
            description=qt.comment or f"From Qlik {qt.source_type} load",
            metadata={
                "qlik_source_type": qt.source_type,
                "qlik_row_count": qt.row_count,
            },
        )

    def _add_dimension(
        self, dim: QlikDimension, tables: list[LogicalTable], warnings: list[str]
    ) -> None:
        """Add a master dimension to the appropriate table."""
        if dim.is_drill_down and dim.drill_down_fields:
            # Create a hierarchy
            levels = []
            for i, f in enumerate(dim.drill_down_fields, start=1):
                levels.append(HierarchyLevel(
                    name=f,
                    column_name=f,
                    ordinal=i,
                ))

            hierarchy = Hierarchy(
                name=dim.name,
                table_name=tables[0].name if tables else "",
                levels=levels,
                description=dim.description or f"Drill-down: {' → '.join(dim.drill_down_fields)}",
            )

            # Add to the table containing these fields
            for table in tables:
                col_names = {c.name for c in table.columns}
                if dim.drill_down_fields[0] in col_names:
                    table.hierarchies.append(hierarchy)
                    hierarchy.table_name = table.name
                    return

            # If no table found, add to first table
            if tables:
                tables[0].hierarchies.append(hierarchy)
        else:
            # Single-field dimension — just mark the field
            target_field = dim.field_name or dim.name
            for table in tables:
                for col in table.columns:
                    if col.name == target_field:
                        col.display_folder = "Dimensions"
                        return
            warnings.append(f"Dimension '{dim.name}' field '{target_field}' not found in any table")

    def _infer_joins(self, tables: list[LogicalTable]) -> list[LogicalJoin]:
        """Infer joins based on shared field names (Qlik associative model)."""
        joins: list[LogicalJoin] = []
        seen: set[tuple[str, str]] = set()

        for i, t1 in enumerate(tables):
            t1_fields = {c.name for c in t1.columns if c.kind != ColumnKind.KEY or not c.name.endswith("Key")}
            for t2 in tables[i + 1:]:
                t2_fields = {c.name for c in t2.columns if c.kind != ColumnKind.KEY or not c.name.endswith("Key")}
                shared = t1_fields & t2_fields
                if shared:
                    col = sorted(shared)[0]
                    pair = tuple(sorted([t1.name, t2.name]))
                    if pair not in seen:
                        seen.add(pair)
                        joins.append(LogicalJoin(
                            from_table=t1.name,
                            to_table=t2.name,
                            from_column=col,
                            to_column=col,
                            join_type="inner",
                            cardinality=JoinCardinality.MANY_TO_ONE,
                            is_active=True,
                        ))

        return joins
