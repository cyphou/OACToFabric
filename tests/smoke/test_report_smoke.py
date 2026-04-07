"""Smoke tests — Semantic Model Agent end-to-end."""

from __future__ import annotations

import unittest


class TestSemanticSmoke(unittest.TestCase):
    """Verify Semantic Model Agent can produce TMDL for a tiny model."""

    def test_tmdl_generator_import(self) -> None:
        from src.agents.semantic import tmdl_generator  # noqa: F401

    def test_expression_translator_import(self) -> None:
        from src.agents.semantic import expression_translator  # noqa: F401

    def test_hierarchy_mapper_import(self) -> None:
        from src.agents.semantic import hierarchy_mapper  # noqa: F401

    def test_dax_optimizer_import(self) -> None:
        from src.agents.semantic import dax_optimizer  # noqa: F401

    def test_tmdl_generates_table(self) -> None:
        """TMDL generator produces table TMDL for a simple IR."""
        from src.agents.semantic.tmdl_generator import generate_table_tmdl
        from src.agents.semantic.rpd_model_parser import LogicalTable, LogicalColumn

        table = LogicalTable(
            name="SmokeTable",
            columns=[
                LogicalColumn(name="ID", data_type="Int64"),
                LogicalColumn(name="Amount", data_type="Double"),
            ],
        )
        tmdl = generate_table_tmdl(table, hierarchies=[], translations={})
        self.assertIn("SmokeTable", tmdl)

    def test_expression_translator_basic(self) -> None:
        """A simple OAC expression translates to DAX."""
        from src.agents.semantic.expression_translator import translate_expression

        result = translate_expression("SUM(Revenue)")
        self.assertIsNotNone(result)
        self.assertTrue(len(result.dax_expression) > 0)


if __name__ == "__main__":
    unittest.main()
