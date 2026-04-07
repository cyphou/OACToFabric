"""Smoke tests — Report Migration Agent end-to-end."""

from __future__ import annotations

import unittest


class TestReportSmoke(unittest.TestCase):
    """Verify Report Agent can produce PBIR visuals for a minimal analysis."""

    def test_visual_mapper_import(self) -> None:
        from src.agents.report import visual_mapper  # noqa: F401

    def test_pbir_generator_import(self) -> None:
        from src.agents.report import pbir_generator  # noqa: F401

    def test_layout_engine_import(self) -> None:
        from src.agents.report import layout_engine  # noqa: F401

    def test_prompt_converter_import(self) -> None:
        from src.agents.report import prompt_converter  # noqa: F401

    def test_visual_mapper_basic(self) -> None:
        """A bar chart type maps to a Power BI visual type."""
        from src.agents.report.visual_mapper import map_visual_type

        pbi_type, warnings = map_visual_type("bar")
        self.assertIsNotNone(pbi_type)

    def test_pbir_generator_creates_page(self) -> None:
        """PBIR generator can emit a minimal report page JSON."""
        from src.agents.report.pbir_generator import generate_page_json
        from src.agents.report.layout_engine import PBIPage

        page = PBIPage(name="SmokePage", display_name="Smoke Page")
        result = generate_page_json(page)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "SmokePage")


if __name__ == "__main__":
    unittest.main()
