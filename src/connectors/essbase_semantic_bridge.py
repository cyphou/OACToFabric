"""Essbase → Semantic Model bridge.

Converts a parsed Essbase outline (``ParsedOutline``) into the
``SemanticModelIR`` understood by the TMDL generator, allowing
end-to-end migration from Essbase cubes to Power BI semantic models.

Mapping strategy
~~~~~~~~~~~~~~~~
- Each **Essbase cube** becomes one ``SemanticModelIR`` (one Power BI semantic model).
- Each **sparse dimension** becomes a separate ``LogicalTable`` (dimension table).
- Each **dense dimension** becomes columns in the fact table (star schema).
- The **fact table** is synthesised from the cube's dense dimensions + measure keys.
- **Dynamic calc members** become DAX measures in the fact table.
- **Stored members** at level-0 become rows; upper-level members become hierarchy levels.
- **Essbase hierarchies** (generations) map to ``Hierarchy`` with ``HierarchyLevel`` per generation.
- **Accounts dimension** is special: each member becomes a measure or calculated column.
- **Time dimension** is marked as ``is_date_table=True`` with auto-generated date hierarchy.
- **Filters** (security) are converted to RLS role definitions.
- **Substitution variables** become DAX variables / what-if parameters.
- **Calc scripts** are translated to DAX measures via ``EssbaseCalcTranslator``.
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
from src.connectors.essbase_connector import (
    ESSBASE_TO_TMDL_MAPPING,
    CalcTranslationResult,
    EssbaseCalcScript,
    EssbaseCalcTranslator,
    EssbaseDimension,
    EssbaseFilter,
    EssbaseMember,
    EssbaseMdxTranslator,
    EssbaseSubstitutionVar,
    ParsedOutline,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Essbase → Fabric data type mapping
# ---------------------------------------------------------------------------

ESSBASE_DATA_TYPE_MAP: dict[str, str] = {
    "numeric": "double",
    "text": "string",
    "date": "dateTime",
    "boolean": "boolean",
    "smartlist": "string",
    "non-numeric": "string",
}


# ---------------------------------------------------------------------------
# RLS role definition
# ---------------------------------------------------------------------------


@dataclass
class RlsRoleDefinition:
    """An RLS role generated from an Essbase filter."""

    name: str
    filter_expression: str  # DAX filter expression
    tables: list[str] = field(default_factory=list)
    source_filter: str = ""  # Original Essbase filter name


@dataclass
class WhatsIfParameter:
    """A What-if parameter generated from an Essbase substitution variable."""

    name: str
    current_value: str
    description: str = ""
    dax_variable: str = ""


# ---------------------------------------------------------------------------
# Conversion result
# ---------------------------------------------------------------------------


@dataclass
class EssbaseConversionResult:
    """Result of converting an Essbase outline to SemanticModelIR."""

    ir: SemanticModelIR
    rls_roles: list[RlsRoleDefinition] = field(default_factory=list)
    whatif_parameters: list[WhatsIfParameter] = field(default_factory=list)
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


class EssbaseToSemanticModelConverter:
    """Convert Essbase outline → SemanticModelIR for TMDL generation.

    Usage::

        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(parsed_outline)
        # result.ir → SemanticModelIR ready for generate_tmdl()
        # result.rls_roles → RLS definitions for Agent 06
        # result.calc_translations → translated calc scripts/measures
    """

    def __init__(self) -> None:
        self._calc_translator = EssbaseCalcTranslator()
        self._mdx_translator = EssbaseMdxTranslator()

    def convert(
        self,
        outline: ParsedOutline,
        *,
        model_name: str | None = None,
        calc_scripts: list[EssbaseCalcScript] | None = None,
        filters: list[EssbaseFilter] | None = None,
        substitution_vars: list[EssbaseSubstitutionVar] | None = None,
    ) -> EssbaseConversionResult:
        """Convert a full Essbase outline to a SemanticModelIR.

        Parameters
        ----------
        outline:
            Parsed Essbase outline with dimensions, members, hierarchies.
        model_name:
            Override semantic model name (defaults to ``{app}_{db}``).
        calc_scripts:
            Calc scripts to translate to DAX measures.
        filters:
            Essbase security filters to convert to RLS roles.
        substitution_vars:
            Substitution variables to convert to What-if parameters.
        """
        warnings: list[str] = []
        review_items: list[str] = []

        name = model_name or f"{outline.application}_{outline.database}" or "EssbaseModel"

        # 1. Build tables from dimensions
        tables: list[LogicalTable] = []
        fact_columns: list[LogicalColumn] = []
        joins: list[LogicalJoin] = []
        measures: list[LogicalColumn] = []

        accounts_dims: list[EssbaseDimension] = []
        time_dims: list[EssbaseDimension] = []
        regular_dims: list[EssbaseDimension] = []

        for dim in outline.dimensions:
            if dim.dimension_type == "accounts":
                accounts_dims.append(dim)
            elif dim.dimension_type == "time":
                time_dims.append(dim)
            else:
                regular_dims.append(dim)

        # Process accounts dimensions → measures
        for dim in accounts_dims:
            acct_measures, acct_warnings = self._accounts_to_measures(dim)
            measures.extend(acct_measures)
            warnings.extend(acct_warnings)

        # Process time dimensions → date tables
        for dim in time_dims:
            table = self._dimension_to_table(dim, is_date=True)
            tables.append(table)

        # Process regular dimensions → dimension tables (sparse) or fact columns (dense)
        for dim in regular_dims:
            if dim.storage_type == "sparse":
                table = self._dimension_to_table(dim)
                tables.append(table)
            else:
                # Dense dimension → columns in fact table
                cols = self._dense_dimension_to_columns(dim)
                fact_columns.extend(cols)

        # Process attribute dimensions → extra columns on parent
        for dim in outline.dimensions:
            if dim.dimension_type == "attribute":
                self._attribute_dimension(dim, tables, warnings)

        # 2. Build fact table
        fact_table = self._build_fact_table(
            name, fact_columns, measures, outline.dimensions
        )
        tables.insert(0, fact_table)

        # 3. Build star-schema joins (dim tables → fact table)
        for table in tables:
            if table.name != fact_table.name and not table.is_date_table:
                join = self._build_dimension_join(fact_table, table)
                if join:
                    joins.append(join)

        # Date table joins
        for table in tables:
            if table.is_date_table:
                join = self._build_date_join(fact_table, table)
                if join:
                    joins.append(join)

        # 4. Translate calc scripts → additional DAX measures
        calc_translations: list[CalcTranslationResult] = []
        if calc_scripts:
            for script in calc_scripts:
                result = self._calc_translator.translate(script)
                calc_translations.append(result)
                if result.confidence >= 0.5:
                    measure = LogicalColumn(
                        name=script.name,
                        data_type="double",
                        expression=result.dax_expression,
                        kind=ColumnKind.MEASURE,
                        display_folder="Calc Scripts",
                        description=f"From Essbase calc script: {script.name}",
                    )
                    fact_table.columns.append(measure)
                else:
                    review_items.append(
                        f"Low confidence ({result.confidence:.0%}) for calc script '{script.name}': {result.warnings}"
                    )

        # 5. Convert filters → RLS roles
        rls_roles: list[RlsRoleDefinition] = []
        if filters:
            for flt in filters:
                role = self._filter_to_rls(flt, tables)
                if role:
                    rls_roles.append(role)

        # 6. Convert substitution variables → What-if parameters
        whatif_params: list[WhatsIfParameter] = []
        if substitution_vars:
            for var in substitution_vars:
                param = WhatsIfParameter(
                    name=var.name,
                    current_value=var.value,
                    description=f"Essbase substitution variable ({var.scope})",
                    dax_variable=f'VAR __{var.name} = "{var.value}"',
                )
                whatif_params.append(param)

        # 7. Build subject area (one perspective per cube)
        subject_area = SubjectArea(
            name=name,
            tables=[t.name for t in tables],
            columns={t.name: [c.name for c in t.columns] for t in tables},
            description=f"Essbase cube: {outline.application}/{outline.database}",
        )

        ir = SemanticModelIR(
            tables=tables,
            joins=joins,
            subject_areas=[subject_area],
            model_name=name,
            description=f"Migrated from Essbase {outline.application}/{outline.database}",
        )

        return EssbaseConversionResult(
            ir=ir,
            rls_roles=rls_roles,
            whatif_parameters=whatif_params,
            calc_translations=calc_translations,
            warnings=warnings,
            review_items=review_items,
        )

    # ------------------------------------------------------------------
    # Dimension → LogicalTable
    # ------------------------------------------------------------------

    def _dimension_to_table(
        self, dim: EssbaseDimension, *, is_date: bool = False
    ) -> LogicalTable:
        """Convert an Essbase dimension to a LogicalTable."""
        columns: list[LogicalColumn] = []

        # Key column
        columns.append(LogicalColumn(
            name=f"{dim.name}Key",
            data_type="string",
            kind=ColumnKind.KEY,
            description=f"Primary key for {dim.name} dimension",
        ))

        # Name column
        columns.append(LogicalColumn(
            name=dim.name,
            data_type="string",
            kind=ColumnKind.DIRECT,
            description=f"{dim.name} member name",
        ))

        # Parent column (for parent-child hierarchies)
        columns.append(LogicalColumn(
            name=f"{dim.name}Parent",
            data_type="string",
            kind=ColumnKind.DIRECT,
            description=f"Parent member for {dim.name}",
        ))

        # Level column
        columns.append(LogicalColumn(
            name=f"{dim.name}Level",
            data_type="int64",
            kind=ColumnKind.DIRECT,
            description=f"Level number in {dim.name} hierarchy",
        ))

        # Generation columns for each generation detected
        if dim.generation_count > 0:
            for gen in range(1, dim.generation_count + 1):
                columns.append(LogicalColumn(
                    name=f"Gen{gen}_{dim.name}",
                    data_type="string",
                    kind=ColumnKind.DIRECT,
                    description=f"Generation {gen} of {dim.name}",
                ))

        # UDA columns from member_details
        udas = set()
        for mbr in dim.member_details:
            for uda in mbr.uda_list:
                udas.add(uda)
        for uda in sorted(udas):
            columns.append(LogicalColumn(
                name=f"UDA_{uda}",
                data_type="boolean",
                kind=ColumnKind.DIRECT,
                description=f"UDA flag: {uda}",
            ))

        # Alias column
        if dim.alias_table:
            columns.append(LogicalColumn(
                name=f"{dim.name}Alias",
                data_type="string",
                kind=ColumnKind.DIRECT,
                description=f"Alias from table '{dim.alias_table}'",
            ))

        # Build hierarchy from generations
        hierarchy = self._build_hierarchy(dim)

        table = LogicalTable(
            name=dim.name,
            columns=columns,
            hierarchies=[hierarchy] if hierarchy else [],
            physical_sources=[f"essbase.{dim.name}"],
            description=f"Dimension: {dim.name} ({dim.dimension_type}, {dim.storage_type})",
            is_date_table=is_date,
            metadata={
                "essbase_dimension_type": dim.dimension_type,
                "essbase_storage_type": dim.storage_type,
                "member_count": len(dim.members),
            },
        )

        return table

    # ------------------------------------------------------------------
    # Accounts dimension → measures
    # ------------------------------------------------------------------

    def _accounts_to_measures(
        self, dim: EssbaseDimension
    ) -> tuple[list[LogicalColumn], list[str]]:
        """Convert accounts dimension members to DAX measures."""
        measures: list[LogicalColumn] = []
        warnings: list[str] = []

        for mbr in dim.member_details:
            if mbr.storage_type == "dynamic_calc" and mbr.formula:
                # Translate formula to DAX
                result = self._calc_translator.translate_formula(
                    mbr.formula, source_name=mbr.name
                )
                measure = LogicalColumn(
                    name=mbr.name,
                    data_type="double",
                    expression=result.dax_expression,
                    kind=ColumnKind.MEASURE,
                    display_folder="Accounts",
                    description=f"Dynamic calc: {mbr.formula}",
                    aggregation="CALCULATE",
                )
                measures.append(measure)
                if result.confidence < 0.7:
                    warnings.append(
                        f"Low confidence ({result.confidence:.0%}) translating "
                        f"'{mbr.name}': {mbr.formula}"
                    )
            elif mbr.storage_type == "dynamic_calc":
                # Dynamic calc without formula → SUM measure
                measure = LogicalColumn(
                    name=mbr.name,
                    data_type="double",
                    expression=f"SUM('Fact'[{mbr.name}])",
                    kind=ColumnKind.MEASURE,
                    display_folder="Accounts",
                    aggregation="SUM",
                )
                measures.append(measure)
            elif mbr.storage_type == "store":
                # Stored member → simple SUM measure
                measure = LogicalColumn(
                    name=mbr.name,
                    data_type="double",
                    expression=f"SUM('Fact'[{mbr.name}])",
                    kind=ColumnKind.MEASURE,
                    display_folder="Accounts",
                    aggregation="SUM",
                )
                measures.append(measure)
            elif mbr.storage_type == "label_only":
                # Label-only → display folder, no measure
                pass
            else:
                warnings.append(
                    f"Skipped accounts member '{mbr.name}' "
                    f"(storage_type={mbr.storage_type})"
                )

        # If no member_details, create measures from member names
        if not dim.member_details and dim.members:
            for name in dim.members:
                measure = LogicalColumn(
                    name=name,
                    data_type="double",
                    expression=f"SUM('Fact'[{name}])",
                    kind=ColumnKind.MEASURE,
                    display_folder="Accounts",
                    aggregation="SUM",
                )
                measures.append(measure)

        return measures, warnings

    # ------------------------------------------------------------------
    # Dense dimension → fact table columns
    # ------------------------------------------------------------------

    def _dense_dimension_to_columns(
        self, dim: EssbaseDimension
    ) -> list[LogicalColumn]:
        """Dense dimension → fact table columns."""
        columns: list[LogicalColumn] = []

        # Key column referencing the dimension
        columns.append(LogicalColumn(
            name=f"{dim.name}Key",
            data_type="string",
            kind=ColumnKind.DIRECT,
            description=f"Dense dimension key: {dim.name}",
        ))

        return columns

    # ------------------------------------------------------------------
    # Attribute dimension → extra columns on parent table
    # ------------------------------------------------------------------

    def _attribute_dimension(
        self,
        dim: EssbaseDimension,
        tables: list[LogicalTable],
        warnings: list[str],
    ) -> None:
        """Add attribute dimension as columns on the parent table."""
        # Attribute dimensions attach to regular dimensions
        # In absence of explicit parent info, add as a standalone column set
        # on the first regular table
        for table in tables:
            if not table.is_date_table and table.name != "Fact":
                table.columns.append(LogicalColumn(
                    name=dim.name,
                    data_type="string",
                    kind=ColumnKind.DIRECT,
                    description=f"Attribute dimension: {dim.name}",
                ))
                return

        warnings.append(f"No parent table found for attribute dimension '{dim.name}'")

    # ------------------------------------------------------------------
    # Fact table construction
    # ------------------------------------------------------------------

    def _build_fact_table(
        self,
        model_name: str,
        dense_columns: list[LogicalColumn],
        measures: list[LogicalColumn],
        dimensions: list[EssbaseDimension],
    ) -> LogicalTable:
        """Build the central fact table."""
        columns: list[LogicalColumn] = []

        # Foreign key columns for each sparse dimension
        for dim in dimensions:
            if dim.storage_type == "sparse" and dim.dimension_type not in ("accounts", "attribute"):
                columns.append(LogicalColumn(
                    name=f"{dim.name}Key",
                    data_type="string",
                    kind=ColumnKind.KEY,
                    description=f"FK to {dim.name} dimension",
                ))

        # Date key for time dimensions
        for dim in dimensions:
            if dim.dimension_type == "time":
                columns.append(LogicalColumn(
                    name=f"{dim.name}Key",
                    data_type="string",
                    kind=ColumnKind.KEY,
                    description=f"FK to {dim.name} date table",
                ))

        # Dense dimension columns
        columns.extend(dense_columns)

        # Value column (the base measure for stored data)
        columns.append(LogicalColumn(
            name="Value",
            data_type="double",
            kind=ColumnKind.DIRECT,
            description="Essbase data cell value",
        ))

        # Measures from accounts dimension
        columns.extend(measures)

        fact_name = f"Fact_{model_name}" if model_name else "Fact"

        return LogicalTable(
            name=fact_name,
            columns=columns,
            physical_sources=["essbase.data_export"],
            description="Fact table synthesised from Essbase cube data cells",
            metadata={"essbase_source": "data_export"},
        )

    # ------------------------------------------------------------------
    # Hierarchy construction
    # ------------------------------------------------------------------

    def _build_hierarchy(self, dim: EssbaseDimension) -> Hierarchy | None:
        """Build a hierarchy from dimension generations."""
        if dim.generation_count <= 1:
            return None

        levels: list[HierarchyLevel] = []
        for gen in range(1, dim.generation_count + 1):
            levels.append(HierarchyLevel(
                name=f"Gen{gen}",
                column_name=f"Gen{gen}_{dim.name}",
                ordinal=gen,
            ))

        return Hierarchy(
            name=f"{dim.name} Hierarchy",
            table_name=dim.name,
            levels=levels,
            description=f"Auto-generated from Essbase {dim.name} generations",
        )

    # ------------------------------------------------------------------
    # Star-schema joins
    # ------------------------------------------------------------------

    def _build_dimension_join(
        self, fact_table: LogicalTable, dim_table: LogicalTable
    ) -> LogicalJoin | None:
        """Build a join between fact and dimension table."""
        fk_name = f"{dim_table.name}Key"

        # Check fact table has the FK column
        fact_has_fk = any(c.name == fk_name for c in fact_table.columns)
        dim_has_pk = any(c.name == fk_name for c in dim_table.columns)

        if fact_has_fk and dim_has_pk:
            return LogicalJoin(
                from_table=fact_table.name,
                to_table=dim_table.name,
                from_column=fk_name,
                to_column=fk_name,
                join_type="left",
                cardinality=JoinCardinality.MANY_TO_ONE,
                is_active=True,
            )
        return None

    def _build_date_join(
        self, fact_table: LogicalTable, date_table: LogicalTable
    ) -> LogicalJoin | None:
        """Build a join between fact and date table."""
        fk_name = f"{date_table.name}Key"

        fact_has_fk = any(c.name == fk_name for c in fact_table.columns)
        date_has_pk = any(c.name == fk_name for c in date_table.columns)

        if fact_has_fk and date_has_pk:
            return LogicalJoin(
                from_table=fact_table.name,
                to_table=date_table.name,
                from_column=fk_name,
                to_column=fk_name,
                join_type="left",
                cardinality=JoinCardinality.MANY_TO_ONE,
                is_active=True,
            )
        return None

    # ------------------------------------------------------------------
    # Security filters → RLS
    # ------------------------------------------------------------------

    def _filter_to_rls(
        self, flt: EssbaseFilter, tables: list[LogicalTable]
    ) -> RlsRoleDefinition | None:
        """Convert an Essbase filter to an RLS role definition."""
        if not flt.rows:
            return None

        dax_filters: list[str] = []
        affected_tables: list[str] = []

        for row in flt.rows:
            member = row.get("member", "")
            access = row.get("access", "read")

            if access == "none":
                # Deny access → filter out
                dax_filters.append(f"NOT(CONTAINSSTRING({{table}}[member], \"{member}\"))")
            elif access in ("read", "write"):
                # Allow access → include
                dax_filters.append(f"CONTAINSSTRING({{table}}[member], \"{member}\")")

            # Try to find which table this member belongs to
            for table in tables:
                if any(member in c.name for c in table.columns):
                    if table.name not in affected_tables:
                        affected_tables.append(table.name)

        if not dax_filters:
            return None

        combined = " && ".join(dax_filters)

        return RlsRoleDefinition(
            name=flt.name,
            filter_expression=combined,
            tables=affected_tables,
            source_filter=flt.name,
        )
