"""Generate anonymized RPD XML fixtures for CI testing.

Creates realistic RPD XML files with randomized names while preserving
the structural patterns found in real OAC RPD exports. Useful for:
- CI test suites that need RPD fixtures without confidential data.
- Load testing the streaming parser with variable-size files.
- Regression testing parser changes against realistic structures.

Usage::

    from src.testing.rpd_fixture_gen import generate_rpd_fixture

    # Small fixture (10 tables, 50 columns)
    generate_rpd_fixture("tests/fixtures/small_rpd.xml", num_tables=10)

    # Large fixture (500 tables, 5000 columns)
    generate_rpd_fixture("tests/fixtures/large_rpd.xml", num_tables=500)
"""

from __future__ import annotations

import random
import string
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent


# ---------------------------------------------------------------------------
# Name generators (anonymized but realistic)
# ---------------------------------------------------------------------------

_ADJECTIVES = [
    "Global", "Regional", "Annual", "Monthly", "Daily", "Weekly",
    "Summary", "Detail", "Historical", "Current", "Projected",
    "Core", "Extended", "Consolidated", "Primary", "Secondary",
]

_NOUNS = [
    "Sales", "Revenue", "Orders", "Customers", "Products", "Inventory",
    "Shipments", "Returns", "Payments", "Invoices", "Accounts",
    "Employees", "Departments", "Regions", "Categories", "Suppliers",
]

_COL_PREFIXES = [
    "DIM", "FACT", "MTR", "ATTR", "KEY", "FK", "SRC", "TGT",
]

_DATA_TYPES = [
    ("VARCHAR2", "255"), ("NUMBER", "10,2"), ("DATE", ""),
    ("TIMESTAMP", ""), ("INTEGER", ""), ("CLOB", ""),
    ("NUMBER", "12,0"), ("VARCHAR2", "50"), ("NUMBER", "18,4"),
]


def _rand_name(prefix: str = "") -> str:
    adj = random.choice(_ADJECTIVES)
    noun = random.choice(_NOUNS)
    suffix = "".join(random.choices(string.digits, k=3))
    parts = [p for p in [prefix, adj, noun, suffix] if p]
    return "_".join(parts)


def _rand_col_name() -> str:
    prefix = random.choice(_COL_PREFIXES)
    noun = random.choice(_NOUNS).upper()
    suffix = "".join(random.choices(string.ascii_uppercase, k=2))
    return f"{prefix}_{noun}_{suffix}"


def _uuid() -> str:
    """Generate a fake mdsid (UUID-like)."""
    parts = [
        "".join(random.choices("0123456789abcdef", k=n))
        for n in [8, 4, 4, 4, 12]
    ]
    return "-".join(parts)


# ---------------------------------------------------------------------------
# XML generators
# ---------------------------------------------------------------------------


def _add_physical_layer(
    root: Element,
    num_tables: int,
    cols_per_table: int,
) -> list[dict]:
    """Add PhysicalLayer with tables and columns. Returns table metadata."""
    phys = SubElement(root, "PhysicalLayer")
    db = SubElement(phys, "Database", name="OracleDB_Prod", mdsid=_uuid())
    schema = SubElement(db, "Schema", name="OACS", mdsid=_uuid())

    tables_meta = []
    for i in range(num_tables):
        tname = _rand_name("TBL")
        table = SubElement(schema, "PhysicalTable", name=tname, mdsid=_uuid())
        SubElement(table, "Description").text = f"Physical table {i+1}"

        columns = []
        # Always add a PK column
        pk_name = f"PK_{tname}_ID"
        pk = SubElement(table, "PhysicalColumn", name=pk_name, mdsid=_uuid())
        SubElement(pk, "DataType").text = "NUMBER"
        SubElement(pk, "Length").text = "12"
        SubElement(pk, "Nullable").text = "false"
        columns.append({"name": pk_name, "type": "NUMBER"})

        for j in range(cols_per_table - 1):
            cname = _rand_col_name()
            dtype, length = random.choice(_DATA_TYPES)
            col = SubElement(table, "PhysicalColumn", name=cname, mdsid=_uuid())
            SubElement(col, "DataType").text = dtype
            if length:
                SubElement(col, "Length").text = length
            SubElement(col, "Nullable").text = random.choice(["true", "false"])
            columns.append({"name": cname, "type": dtype})

        tables_meta.append({
            "name": tname,
            "columns": columns,
            "pk": pk_name,
        })

    return tables_meta


def _add_logical_layer(
    root: Element,
    tables_meta: list[dict],
) -> list[dict]:
    """Add BusinessModel (logical layer) with logical tables and sources."""
    bm = SubElement(root, "BusinessModel", name="Analytics_Model", mdsid=_uuid())

    logical_tables = []
    for tm in tables_meta:
        lt_name = tm["name"].replace("TBL_", "")
        lt = SubElement(bm, "LogicalTable", name=lt_name, mdsid=_uuid())

        # Logical table source
        lts = SubElement(lt, "LogicalTableSource", name=f"LTS_{lt_name}", mdsid=_uuid())
        SubElement(lts, "PhysicalTableRef").text = tm["name"]

        # Logical columns
        for col in tm["columns"]:
            lc = SubElement(lt, "LogicalColumn", name=col["name"], mdsid=_uuid())
            # Add expression for some columns (calculated)
            if random.random() < 0.2:
                expr = f"SUM({col['name']})"
                SubElement(lc, "Expression").text = expr

        logical_tables.append({"name": lt_name, "physical": tm["name"]})

    # Add some joins between tables
    if len(logical_tables) > 1:
        for i in range(min(len(logical_tables) - 1, 10)):
            join = SubElement(bm, "LogicalJoin", mdsid=_uuid())
            SubElement(join, "Table1").text = logical_tables[i]["name"]
            SubElement(join, "Table2").text = logical_tables[i + 1]["name"]
            SubElement(join, "Cardinality").text = random.choice([
                "ONE_TO_MANY", "MANY_TO_ONE", "ONE_TO_ONE",
            ])

    return logical_tables


def _add_presentation_layer(
    root: Element,
    logical_tables: list[dict],
) -> None:
    """Add PresentationLayer with catalogs and tables."""
    pres = SubElement(root, "PresentationLayer")

    # Create 1-3 subject areas
    num_sa = min(3, max(1, len(logical_tables) // 5))
    tables_per_sa = len(logical_tables) // num_sa

    for sa_idx in range(num_sa):
        sa_name = f"SA_{_rand_name()}"
        catalog = SubElement(pres, "PresentationCatalog", name=sa_name, mdsid=_uuid())

        start = sa_idx * tables_per_sa
        end = start + tables_per_sa if sa_idx < num_sa - 1 else len(logical_tables)

        for lt in logical_tables[start:end]:
            pt = SubElement(catalog, "PresentationTable", name=lt["name"], mdsid=_uuid())
            SubElement(pt, "LogicalTableRef").text = lt["name"]

            # Add 3-5 presentation columns
            for _ in range(random.randint(3, 5)):
                pc_name = _rand_col_name()
                SubElement(pt, "PresentationColumn", name=pc_name, mdsid=_uuid())


def _add_security_layer(root: Element, num_roles: int = 3) -> None:
    """Add SecurityLayer with roles and RLS filters."""
    sec = SubElement(root, "SecurityLayer")

    role_names = [
        "BIAdministrator", "BIConsumer", "BIAuthor",
        "SalesAnalyst", "FinanceViewer", "HRAdmin",
    ]

    for i in range(min(num_roles, len(role_names))):
        role = SubElement(sec, "ApplicationRole", name=role_names[i], mdsid=_uuid())
        SubElement(role, "Description").text = f"Role for {role_names[i]}"

        # Add RLS filter for some roles
        if random.random() < 0.5:
            rls = SubElement(role, "RowLevelSecurityFilter", mdsid=_uuid())
            SubElement(rls, "Expression").text = (
                f'"Analytics_Model"."Dim_Region"."REGION_CODE" = '
                f'VALUEOF(NQ_SESSION.REGION)'
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_rpd_fixture(
    output_path: str | Path,
    *,
    num_tables: int = 10,
    cols_per_table: int = 8,
    num_roles: int = 3,
    seed: int | None = 42,
) -> Path:
    """Generate an anonymized RPD XML fixture.

    Parameters
    ----------
    output_path:
        Where to write the XML file.
    num_tables:
        Number of physical tables to generate.
    cols_per_table:
        Average columns per table.
    num_roles:
        Number of security roles.
    seed:
        Random seed for reproducibility.

    Returns
    -------
    Path to the generated file.
    """
    if seed is not None:
        random.seed(seed)

    root = Element("Repository", name="AnonymizedRPD", version="12.2.5.0")

    # Build layers
    tables_meta = _add_physical_layer(root, num_tables, cols_per_table)
    logical_tables = _add_logical_layer(root, tables_meta)
    _add_presentation_layer(root, logical_tables)
    _add_security_layer(root, num_roles)

    # Write
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    tree = ElementTree(root)
    indent(tree, space="  ")
    tree.write(str(out), encoding="unicode", xml_declaration=True)

    return out
