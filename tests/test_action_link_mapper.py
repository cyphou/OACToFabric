"""Tests for action_link_mapper — OAC actions → PBI drillthrough/bookmarks."""

from __future__ import annotations

import unittest

from src.agents.report.action_link_mapper import (
    ActionMappingResult,
    PBIBookmarkAction,
    PBIDrillthrough,
    PBIPageNavigationAction,
    PBIURLAction,
    map_all_action_links,
    map_oac_action_link,
)


class TestMapOACActionLink(unittest.TestCase):

    def test_navigate_to_drillthrough(self):
        result = map_oac_action_link("navigate", "/reports/detail", source_column="Region")
        self.assertIsInstance(result, PBIDrillthrough)
        self.assertIn("Region", result.filter_columns)

    def test_cross_report_detected(self):
        result = map_oac_action_link("navigate", "other/report/page")
        self.assertIsInstance(result, PBIDrillthrough)
        self.assertTrue(result.cross_report)

    def test_drilldown_to_drillthrough(self):
        result = map_oac_action_link("drillDown", "DetailPage")
        self.assertIsInstance(result, PBIDrillthrough)

    def test_url_action(self):
        result = map_oac_action_link("url", "https://example.com", parameters={"label": "Click"})
        self.assertIsInstance(result, PBIURLAction)
        self.assertEqual(result.url, "https://example.com")
        self.assertEqual(result.display_text, "Click")

    def test_bookmark_action(self):
        result = map_oac_action_link("bookmark", "MyBookmark")
        self.assertIsInstance(result, PBIBookmarkAction)
        self.assertEqual(result.bookmark_name, "MyBookmark")

    def test_page_navigation(self):
        result = map_oac_action_link("pageNavigation", "Page2")
        self.assertIsInstance(result, PBIPageNavigationAction)
        self.assertEqual(result.target_page, "Page2")

    def test_unknown_returns_none(self):
        result = map_oac_action_link("unknownAction", "target")
        self.assertIsNone(result)

    def test_visual_json_drillthrough(self):
        result = map_oac_action_link("navigate", "page1")
        self.assertIsInstance(result, PBIDrillthrough)
        j = result.to_visual_json()
        self.assertIn("drillthrough", j)

    def test_visual_json_url(self):
        result = map_oac_action_link("url", "https://x.com")
        j = result.to_visual_json()
        self.assertIn("action", j)
        self.assertEqual(j["action"]["type"], "WebUrl")


class TestMapAllActionLinks(unittest.TestCase):

    def test_mixed_actions(self):
        actions = [
            {"action_type": "navigate", "target": "p1", "source_column": "Region"},
            {"action_type": "url", "target": "https://x.com"},
            {"action_type": "bookmark", "target": "BM1"},
            {"action_type": "INVALID", "target": "x"},
        ]
        result = map_all_action_links(actions)
        self.assertEqual(len(result.drillthroughs), 1)
        self.assertEqual(len(result.url_actions), 1)
        self.assertEqual(len(result.bookmarks), 1)
        self.assertEqual(len(result.warnings), 1)

    def test_empty(self):
        result = map_all_action_links([])
        self.assertEqual(len(result.drillthroughs), 0)


if __name__ == "__main__":
    unittest.main()
