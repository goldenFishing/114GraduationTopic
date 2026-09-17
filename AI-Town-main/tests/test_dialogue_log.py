"""
tests/test_dialogue_log.py

Tests for observe/dialogue_log.py — dialogue history formatting utilities.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from observe.dialogue_log import (
    format_dialogue_history,
    filter_by_character,
    filter_by_day,
)
from config.world_config import CHARACTER_NAMES


# ── Fixtures ──────────────────────────────────────────────────────

def _make_raw_entry(initiator="A", responder="B", accepted=True, turns=None):
    if turns is None:
        turns = [
            {"speaker": initiator, "msg": "你好！"},
            {"speaker": responder, "msg": "你好呀！"},
        ]
    return {
        "initiator": initiator,
        "responder": responder,
        "accepted":  accepted,
        "turns":     turns,
    }


# ── format_dialogue_history ───────────────────────────────────────

class TestFormatDialogueHistory(unittest.TestCase):

    def test_empty_history_returns_empty_list(self):
        self.assertEqual(format_dialogue_history([]), [])

    def test_single_entry_keys(self):
        """Formatted entry contains all expected keys."""
        result = format_dialogue_history([_make_raw_entry()])
        self.assertEqual(len(result), 1)
        entry = result[0]
        for key in ("initiator_code", "initiator_name",
                    "responder_code", "responder_name",
                    "accepted", "rounds", "turns"):
            self.assertIn(key, entry)

    def test_code_to_name_mapping(self):
        """Character codes are translated to full names via CHARACTER_NAMES."""
        result = format_dialogue_history([_make_raw_entry("A", "B")])
        entry = result[0]
        self.assertEqual(entry["initiator_code"], "A")
        self.assertEqual(entry["initiator_name"], CHARACTER_NAMES["A"])
        self.assertEqual(entry["responder_code"], "B")
        self.assertEqual(entry["responder_name"], CHARACTER_NAMES["B"])

    def test_unknown_code_falls_back_to_code(self):
        """Unknown codes are kept as-is in both _code and _name fields."""
        result = format_dialogue_history([_make_raw_entry("X", "Y")])
        entry = result[0]
        self.assertEqual(entry["initiator_name"], "X")
        self.assertEqual(entry["responder_name"], "Y")

    def test_accepted_flag_preserved(self):
        accepted_entry  = format_dialogue_history([_make_raw_entry(accepted=True)])[0]
        rejected_entry  = format_dialogue_history([_make_raw_entry(accepted=False)])[0]
        self.assertTrue(accepted_entry["accepted"])
        self.assertFalse(rejected_entry["accepted"])

    def test_rounds_calculation(self):
        """Rounds = len(turns) // 2."""
        turns = [
            {"speaker": "A", "msg": "1"},
            {"speaker": "B", "msg": "2"},
            {"speaker": "A", "msg": "3"},
            {"speaker": "B", "msg": "4"},
        ]
        result = format_dialogue_history([_make_raw_entry(turns=turns)])
        self.assertEqual(result[0]["rounds"], 2)

    def test_turns_contain_speaker_name(self):
        """Each turn inside formatted entry has a speaker_name field."""
        result = format_dialogue_history([_make_raw_entry("A", "B")])
        for turn in result[0]["turns"]:
            self.assertIn("speaker_name", turn)
            self.assertIn("msg", turn)

    def test_multiple_entries(self):
        """Multiple raw entries produce equal number of formatted entries."""
        raw = [_make_raw_entry("A", "B"), _make_raw_entry("C", "D")]
        result = format_dialogue_history(raw)
        self.assertEqual(len(result), 2)

    def test_no_turns_gives_rounds_zero(self):
        """An entry with an empty turns list yields rounds=0."""
        entry = _make_raw_entry(turns=[])
        result = format_dialogue_history([entry])
        self.assertEqual(result[0]["rounds"], 0)


# ── filter_by_character ───────────────────────────────────────────

class TestFilterByCharacter(unittest.TestCase):

    def _formatted_pair(self, init, resp):
        return {
            "initiator_code": init,
            "responder_code": resp,
            "accepted": True,
            "turns": [],
        }

    def test_filter_keeps_initiator_match(self):
        history = [self._formatted_pair("A", "B"), self._formatted_pair("C", "D")]
        result  = filter_by_character(history, "A")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["initiator_code"], "A")

    def test_filter_keeps_responder_match(self):
        history = [self._formatted_pair("A", "B"), self._formatted_pair("C", "D")]
        result  = filter_by_character(history, "B")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["responder_code"], "B")

    def test_filter_returns_empty_when_no_match(self):
        history = [self._formatted_pair("A", "B")]
        result  = filter_by_character(history, "Z")
        self.assertEqual(result, [])

    def test_filter_empty_history(self):
        self.assertEqual(filter_by_character([], "A"), [])


# ── filter_by_day ─────────────────────────────────────────────────

class TestFilterByDay(unittest.TestCase):

    def _make_sim_data(self, days_ticks):
        """Build a minimal simulation_data dict.
        days_ticks: list of lists, each inner list is tick dialogue lists.
        """
        days = []
        for day_idx, ticks in enumerate(days_ticks, start=1):
            tick_list = []
            for dialogues in ticks:
                tick_list.append({"dialogues": dialogues})
            days.append({"day": day_idx, "ticks": tick_list})
        return {"days": days}

    def test_day_1_returns_correct_dialogues(self):
        dlg1 = {"initiator": "A", "responder": "B", "accepted": True, "turns": []}
        dlg2 = {"initiator": "C", "responder": "D", "accepted": False, "turns": []}
        sim  = self._make_sim_data([[[dlg1]], [[dlg2]]])  # day1→tick→[dlg1], day2…
        # Actually need to build properly: days_ticks[0] = [[dlg1]] means day1 has 1 tick with [dlg1]
        sim  = self._make_sim_data([[[dlg1]], [[dlg2]]])
        result = filter_by_day(sim, 1)
        self.assertEqual(result, [dlg1])

    def test_day_out_of_range_returns_empty(self):
        sim = self._make_sim_data([[[]]])  # 1 day
        self.assertEqual(filter_by_day(sim, 0), [])
        self.assertEqual(filter_by_day(sim, 5), [])

    def test_multiple_ticks_aggregated(self):
        dlg1 = {"initiator": "A", "responder": "B", "accepted": True,  "turns": []}
        dlg2 = {"initiator": "C", "responder": "D", "accepted": False, "turns": []}
        sim  = self._make_sim_data([[[dlg1], [dlg2]]])  # day1 has 2 ticks
        result = filter_by_day(sim, 1)
        self.assertEqual(len(result), 2)

    def test_empty_sim_data(self):
        self.assertEqual(filter_by_day({}, 1), [])


if __name__ == "__main__":
    unittest.main()
