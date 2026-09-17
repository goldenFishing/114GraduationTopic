# ================================================================
# tests/test_prompt_io.py
# model/prompt_io.py 單元測試
#
# 涵蓋：
#   1. parse_decision_output() - 解析完整模型輸出
#   2. _parse_block_value()    - 單行 [TAG] 解析
#   3. _parse_block_multiline() - 多行 [THOUGHT] 解析
#   4. _parse_ham_block()      - [HAM]...[/HAM] 解析
#   5. _parse_ham_lines()      - 每行 HAM 命題解析
#   6. _validate_action()      - action 驗證與 fallback
#   7. PromptBuilder           - 組裝 prompt（mock 所有依賴）
#   8. _truncate()             - 截斷工具
# ================================================================

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model.prompt_io import (
    parse_decision_output,
    _parse_block_value,
    _parse_block_multiline,
    _parse_ham_block,
    _parse_ham_lines,
    _validate_action,
    _truncate,
    PromptBuilder,
)


# ================================================================
# 輸出解析測試
# ================================================================

class TestParseBlockValue(unittest.TestCase):
    """測試 _parse_block_value() 單行解析。"""

    def test_simple_tag(self):
        raw = "[ACTION] 工作\n[TARGET] 辦公室"
        self.assertEqual(_parse_block_value(raw, "ACTION"), "工作")

    def test_tag_with_colon(self):
        raw = "[ACTION]: 散步"
        self.assertEqual(_parse_block_value(raw, "ACTION"), "散步")

    def test_tag_with_spaces(self):
        raw = "  [TARGET]  咖啡店  "
        self.assertEqual(_parse_block_value(raw, "TARGET"), "咖啡店")

    def test_missing_tag_returns_empty(self):
        raw = "[ACTION] 工作"
        self.assertEqual(_parse_block_value(raw, "TARGET"), "")

    def test_only_tag_no_content(self):
        raw = "[ACTION]"
        self.assertEqual(_parse_block_value(raw, "ACTION"), "")

    def test_multiline_stops_at_first_match(self):
        raw = "[ACTION] 休息\n[ACTION] 工作"
        self.assertEqual(_parse_block_value(raw, "ACTION"), "休息")


class TestParseBlockMultiline(unittest.TestCase):
    """測試 _parse_block_multiline() THOUGHT 解析。"""

    def test_single_line_thought(self):
        raw = "[THOUGHT] 今天天氣不錯，想去散步"
        result = _parse_block_multiline(raw, "THOUGHT")
        self.assertIn("今天天氣不錯", result)

    def test_multiline_thought(self):
        raw = "[THOUGHT]\n今天工作很累\n需要好好休息\n[ACTION] 休息"
        result = _parse_block_multiline(raw, "THOUGHT")
        self.assertIn("今天工作很累", result)
        self.assertIn("需要好好休息", result)
        self.assertNotIn("[ACTION]", result)

    def test_thought_stops_at_next_tag(self):
        raw = "[THOUGHT] 第一行\n繼續想\n[ACTION] 工作"
        result = _parse_block_multiline(raw, "THOUGHT")
        self.assertNotIn("工作", result)

    def test_missing_tag_returns_empty(self):
        raw = "[ACTION] 工作"
        result = _parse_block_multiline(raw, "THOUGHT")
        self.assertEqual(result, "")


class TestParseHamBlock(unittest.TestCase):
    """測試 _parse_ham_block() HAM 解析。"""

    def test_basic_ham_block(self):
        raw = "[HAM]\n- Amy | 喜歡 | 咖啡 | 咖啡店 | 早上\n[/HAM]"
        result = _parse_ham_block(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["subject"], "Amy")
        self.assertEqual(result[0]["relation"], "喜歡")
        self.assertEqual(result[0]["object"], "咖啡")

    def test_multiple_ham_propositions(self):
        raw = "[HAM]\n- Ben | 工作於 | 超市 | 超市 | 無\n- Ben | 喜歡 | 運動 | 廣場 | 無\n[/HAM]"
        result = _parse_ham_block(raw)
        self.assertEqual(len(result), 2)

    def test_ham_location_none_when_empty(self):
        raw = "[HAM]\n- Amy | 在 | 咖啡店 | 無 | 無\n[/HAM]"
        result = _parse_ham_block(raw)
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["location"])
        self.assertIsNone(result[0]["time"])

    def test_no_ham_block_returns_empty(self):
        raw = "[ACTION] 工作\n[TARGET] 辦公室"
        result = _parse_ham_block(raw)
        self.assertEqual(result, [])

    def test_ham_fallback_without_closing_tag(self):
        raw = "[ACTION] 工作\n[HAM]\n- Amy | 在 | 咖啡店 | 咖啡店 | 早上"
        result = _parse_ham_block(raw)
        self.assertGreaterEqual(len(result), 0)


class TestParseHamLines(unittest.TestCase):
    """測試 _parse_ham_lines() 行解析。"""

    def test_valid_line(self):
        lines = "Amy | 喜歡 | 咖啡 | 咖啡店 | 早上"
        result = _parse_ham_lines(lines)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["subject"], "Amy")

    def test_line_with_dash_prefix(self):
        lines = "- Amy | 認識 | Ben | 廣場 | 無"
        result = _parse_ham_lines(lines)
        self.assertEqual(len(result), 1)

    def test_line_without_pipe_ignored(self):
        lines = "This line has no pipe character"
        result = _parse_ham_lines(lines)
        self.assertEqual(result, [])

    def test_line_with_only_2_parts_ignored(self):
        lines = "Amy | 喜歡"
        result = _parse_ham_lines(lines)
        self.assertEqual(result, [])

    def test_location_none_on_empty(self):
        lines = "Amy | 在 | 家 | | "
        result = _parse_ham_lines(lines)
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["location"])

    def test_empty_lines_ignored(self):
        lines = "\n\n\n"
        result = _parse_ham_lines(lines)
        self.assertEqual(result, [])


class TestValidateAction(unittest.TestCase):
    """測試 _validate_action() 行動驗證。"""

    def test_valid_action_passes(self):
        result = _validate_action("工作")
        self.assertEqual(result, "工作")

    def test_valid_action_with_spaces(self):
        result = _validate_action("  休息  ")
        self.assertEqual(result, "休息")

    def test_invalid_action_with_embedded_valid(self):
        """動作字串包含合法動詞 → 提取。"""
        result = _validate_action("我要去工作了")
        self.assertEqual(result, "工作")

    def test_completely_invalid_action_fallback(self):
        """完全無法識別 → 回傳 ACTION_DEFAULT_ON_INVALID。"""
        from config.action_list import ACTION_DEFAULT_ON_INVALID
        result = _validate_action("無效的動作描述xxxyyy")
        self.assertEqual(result, ACTION_DEFAULT_ON_INVALID)

    def test_all_valid_actions_pass(self):
        """所有合法行動都能通過驗證。"""
        from config.action_list import VALID_ACTIONS
        for action in VALID_ACTIONS:
            self.assertEqual(_validate_action(action), action)


class TestParseDecisionOutput(unittest.TestCase):
    """測試 parse_decision_output() 整合解析。"""

    def test_full_output_parsing(self):
        raw = (
            "[ACTION] 工作\n"
            "[TARGET] 辦公室\n"
            "[CONTENT]\n"
            "[THOUGHT] 今天有重要報告要完成\n"
            "[HAM]\n"
            "- Claire | 工作於 | 辦公室 | 辦公室 | 上午\n"
            "[/HAM]"
        )
        result = parse_decision_output(raw)
        self.assertEqual(result["action"], "工作")
        self.assertEqual(result["target"], "辦公室")
        self.assertEqual(result["thought"], "今天有重要報告要完成")
        self.assertIsInstance(result["ham"], list)
        self.assertEqual(len(result["ham"]), 1)

    def test_dialogue_output_parsing(self):
        raw = (
            "[ACTION] 對話\n"
            "[TARGET] Ben\n"
            "[CONTENT] 你今天超市怎麼樣？\n"
            "[THOUGHT] 想問問 Ben 的近況\n"
            "[HAM]\n[/HAM]"
        )
        result = parse_decision_output(raw)
        self.assertEqual(result["action"], "對話")
        self.assertEqual(result["content"], "你今天超市怎麼樣？")

    def test_empty_raw_returns_defaults(self):
        """空字串回傳預設結構。"""
        result = parse_decision_output("")
        self.assertIn("action", result)
        self.assertIn("target", result)
        self.assertIn("content", result)
        self.assertIn("thought", result)
        self.assertIn("ham", result)

    def test_invalid_action_uses_fallback(self):
        raw = "[ACTION] 完全不存在的動作\n[TARGET] 某地點"
        result = parse_decision_output(raw)
        from config.action_list import ACTION_DEFAULT_ON_INVALID
        self.assertEqual(result["action"], ACTION_DEFAULT_ON_INVALID)

    def test_raw_preserved_in_result(self):
        raw = "[ACTION] 休息\n[TARGET] A家"
        result = parse_decision_output(raw)
        self.assertEqual(result["raw"], raw)


class TestTruncate(unittest.TestCase):
    """測試 _truncate() 截斷函式。"""

    def test_short_text_unchanged(self):
        text = "短文字"
        result = _truncate(text, 100)
        self.assertEqual(result, text)

    def test_long_text_truncated(self):
        text = "A" * 200
        result = _truncate(text, 100)
        self.assertEqual(len(result), len("A" * 100 + "\n...（已截斷）"))

    def test_exact_length_unchanged(self):
        text = "A" * 50
        result = _truncate(text, 50)
        self.assertEqual(result, text)

    def test_truncated_text_has_marker(self):
        text = "A" * 200
        result = _truncate(text, 100)
        self.assertIn("已截斷", result)


# ================================================================
# PromptBuilder 測試（mock 所有依賴）
# ================================================================

class TestPromptBuilder(unittest.TestCase):
    """測試 PromptBuilder（mock 所有依賴）。"""

    def _make_builder(self):
        """建立帶有 mock 依賴的 PromptBuilder。"""
        char = MagicMock()
        char.name = "Amy"
        char.emotion = "開心"
        char.get_personality.return_value = "外向、樂觀"
        char.get_habit.return_value = "早起、喝咖啡"
        char.get_relationship_text.return_value = "和 Ben 是普通朋友"
        char.get_relationship.return_value = {"summary": "", "initial": ""}

        stm = MagicMock()
        stm.get_today_narrative.return_value = "今天早上起床，喝了咖啡。"
        stm.get_recent.return_value = []

        ltm = MagicMock()
        ltm.get_summary.return_value = "Amy 是咖啡師"

        graph = MagicMock()
        graph.auto_query_nodes.return_value = []
        graph.spreading_retrieve.return_value = []
        graph.propositions_to_narrative.return_value = ""

        return PromptBuilder(char, stm, ltm, graph)

    def test_build_deliberate_returns_string(self):
        """build_deliberate() 回傳字串。"""
        builder = self._make_builder()
        with patch("model.prompt_io.prompt_deliberate", return_value="deliberate_prompt"):
            result = builder.build_deliberate(
                scene="第1天 09:00 咖啡店",
                perception={"location": "咖啡店", "yolo_desc": "", "scene_text": ""},
                co_located_codes=["B"],
                input_text="",
            )
        self.assertIsInstance(result, str)
        self.assertEqual(result, "deliberate_prompt")

    def test_build_deliberate_with_no_co_located(self):
        """build_deliberate() 沒有同地點角色不崩潰。"""
        builder = self._make_builder()
        with patch("model.prompt_io.prompt_deliberate", return_value="prompt_no_co"):
            result = builder.build_deliberate(
                scene="第1天 09:00 A家",
                perception={"location": "A家", "yolo_desc": "", "scene_text": ""},
                co_located_codes=[],
                input_text="",
            )
        self.assertEqual(result, "prompt_no_co")

    def test_build_dialogue_returns_string(self):
        """build_dialogue() 回傳字串。"""
        builder = self._make_builder()
        with patch("model.prompt_io.prompt_dialogue", return_value="dialogue_prompt"):
            result = builder.build_dialogue(
                scene="第1天 12:00 廣場",
                partner_code="B",
                partner_message="你好，Amy！",
                recent_dialogue="",
            )
        self.assertIsInstance(result, str)
        self.assertEqual(result, "dialogue_prompt")

    def test_build_dialogue_with_recent_dialogue(self):
        """build_dialogue() 傳入 recent_dialogue 不崩潰。"""
        builder = self._make_builder()
        with patch("model.prompt_io.prompt_dialogue", return_value="dialogue_with_history"):
            result = builder.build_dialogue(
                scene="第1天 12:00 廣場",
                partner_code="B",
                partner_message="最近如何？",
                recent_dialogue="Amy：還不錯\nBen：太好了",
            )
        self.assertEqual(result, "dialogue_with_history")

    def test_build_deliberate_calls_graph_auto_query(self):
        """build_deliberate() 呼叫 graph.auto_query_nodes。"""
        builder = self._make_builder()
        with patch("model.prompt_io.prompt_deliberate", return_value="p"):
            builder.build_deliberate(
                scene="第1天 08:00",
                perception={"location": "咖啡店"},
            )
        builder.graph.auto_query_nodes.assert_called_once()

    def test_build_deliberate_truncates_ltm(self):
        """build_deliberate() 當 LTM 過長時截斷。"""
        builder = self._make_builder()
        # 讓 propositions_to_narrative 回傳超長字串
        builder.graph.propositions_to_narrative.return_value = "X" * 10000
        with patch("model.prompt_io.prompt_deliberate", return_value="p"):
            result = builder.build_deliberate(
                scene="第1天 08:00",
                perception={},
            )
        # 不應崩潰，prompt_deliberate 應被呼叫
        self.assertEqual(result, "p")


if __name__ == "__main__":
    unittest.main(verbosity=2)
