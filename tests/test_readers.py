from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from aoe2_mcminimap.readers import match_from_parsed_scenario, read_map


class TestReaders(TestCase):
    def test_read_map_uses_recorded_game_parser_for_recordings(self):
        mgz_result = object()

        with patch("aoe2_mcminimap.readers.get_mgz", return_value=mgz_result) as mock_get_mgz:
            result = read_map("example.mgz")

        mock_get_mgz.assert_called_once_with("example.mgz")
        self.assertIs(mgz_result, result)

    def test_read_map_uses_shared_parser_for_scenarios(self):
        parsed = object()
        match = object()

        with patch("aoe2_mcminimap.readers.parse_scenario", return_value=parsed) as mock_parse:
            with patch("aoe2_mcminimap.readers.match_from_parsed_scenario", return_value=match) as mock_match:
                result = read_map("example.scx")

        mock_parse.assert_called_once_with("example.scx", suppress_output=True)
        mock_match.assert_called_once_with(parsed)
        self.assertIs(match, result)

    def test_match_from_parsed_scenario_routes_definitive(self):
        parsed = SimpleNamespace(is_definitive_edition=True, scenario="de")
        expected = object()

        with patch("aoe2_mcminimap.readers._match_from_de_scenario", return_value=expected) as mock_de:
            with patch("aoe2_mcminimap.readers._match_from_legacy_scenario") as mock_legacy:
                result = match_from_parsed_scenario(parsed)

        mock_de.assert_called_once_with("de")
        mock_legacy.assert_not_called()
        self.assertIs(expected, result)

    def test_match_from_parsed_scenario_routes_legacy(self):
        parsed = SimpleNamespace(is_definitive_edition=False, scenario="legacy")
        expected = object()

        with patch("aoe2_mcminimap.readers._match_from_legacy_scenario", return_value=expected) as mock_legacy:
            with patch("aoe2_mcminimap.readers._match_from_de_scenario") as mock_de:
                result = match_from_parsed_scenario(parsed)

        mock_legacy.assert_called_once_with("legacy")
        mock_de.assert_not_called()
        self.assertIs(expected, result)
