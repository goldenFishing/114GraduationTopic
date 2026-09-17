# ================================================================
# tests/test_prompts.py
# config/prompts.py 模組的單元測試
# ================================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.prompts import (
    prompt_deliberate,
    prompt_dialogue,
    prompt_extract_ham,
    prompt_select_ltm,
    prompt_ltm_summary,
    prompt_update_relationship,
    prompt_infer_emotion,
    prompt_generate_schedule,
)
from config.action_list import VALID_ACTIONS, VALID_LOCATIONS
from config.world_config import VALID_EMOTIONS


class TestPromptDeliberate(unittest.TestCase):
    """測試 prompt_deliberate() 函式的輸出內容。"""

    def _build(self, **kwargs):
        defaults = dict(
            character_name="Amy",
            personality="溫和、細心、喜歡照顧人",
            habit="早起，每天七點開店前先整理好一切",
            emotion="平靜",
            relationship_text="Amy 與 Ben 是老朋友",
            stm_narrative="今天早上 Amy 在咖啡店忙了一早上，Ben 來買咖啡時聊了幾句。",
            ltm_narrative="Amy 記得 Ben 喜歡喝黑咖啡不加糖。",
            scene="咖啡店 09:00",
            co_located_text="Ben 在咖啡店內",
            current_event="",
        )
        defaults.update(kwargs)
        return prompt_deliberate(**defaults)

    def test_returns_string(self):
        """prompt_deliberate() 應回傳字串。"""
        result = self._build()
        self.assertIsInstance(result, str)

    def test_contains_character_name(self):
        """輸出應包含角色名稱 Amy。"""
        result = self._build()
        self.assertIn("Amy", result)

    def test_contains_action_list(self):
        """輸出應包含至少一個合法行動（來自 VALID_ACTIONS）。"""
        result = self._build()
        found = any(action in result for action in VALID_ACTIONS)
        self.assertTrue(found, "prompt_deliberate 應包含 VALID_ACTIONS 中的行動")

    def test_contains_location_list(self):
        """輸出應包含至少一個合法地點（來自 VALID_LOCATIONS）。"""
        result = self._build()
        found = any(loc in result for loc in VALID_LOCATIONS)
        self.assertTrue(found, "prompt_deliberate 應包含 VALID_LOCATIONS 中的地點")

    def test_contains_output_format_tags(self):
        """輸出應包含 [ACTION]、[TARGET]、[CONTENT]、[THOUGHT]、[HAM] 格式標籤。"""
        result = self._build()
        for tag in ["[ACTION]", "[TARGET]", "[CONTENT]", "[THOUGHT]", "[HAM]"]:
            self.assertIn(tag, result, f"prompt_deliberate 缺少格式標籤 {tag}")

    def test_co_located_text_included_when_provided(self):
        """提供 co_located_text 時輸出應包含附近的人的資訊。"""
        result = self._build(co_located_text="Claire 在辦公室")
        self.assertIn("Claire", result)

    def test_current_event_included_when_provided(self):
        """提供 current_event 時輸出應包含事件內容。"""
        result = self._build(current_event="Emma 突然衝進咖啡店說發生地震了")
        self.assertIn("Emma", result)

    def test_empty_optional_fields(self):
        """可選欄位為空時不應產生錯誤。"""
        result = self._build(
            relationship_text="",
            co_located_text="",
            current_event="",
            ltm_narrative="",
        )
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestPromptDialogue(unittest.TestCase):
    """測試 prompt_dialogue() 函式的輸出內容。"""

    def _build(self, **kwargs):
        defaults = dict(
            character_name="Ben",
            personality="開朗、話多、對人熱情",
            emotion="開心",
            partner_name="Amy",
            relationship_text="Ben 和 Amy 是常客與老闆的關係，也是好朋友",
            stm_narrative="Ben 今天去買咖啡，遇到 Amy 很開心。",
            ltm_narrative="Amy 記得 Ben 喜歡什麼，Ben 很感激。",
            scene="咖啡店 09:15",
            recent_dialogue="Amy：早安，老樣子嗎？\nBen：對，謝謝！",
            partner_message="今天天氣不錯，有空一起散步嗎？",
        )
        defaults.update(kwargs)
        return prompt_dialogue(**defaults)

    def test_returns_string(self):
        """prompt_dialogue() 應回傳字串。"""
        result = self._build()
        self.assertIsInstance(result, str)

    def test_contains_both_character_names(self):
        """輸出應包含自己（Ben）和對話對象（Amy）的名稱。"""
        result = self._build()
        self.assertIn("Ben", result)
        self.assertIn("Amy", result)

    def test_contains_partner_message(self):
        """輸出應包含對方說的話。"""
        result = self._build()
        self.assertIn("今天天氣不錯", result)

    def test_contains_output_format_tags(self):
        """輸出應包含 [ACTION]、[CONTENT]、[THOUGHT]、[HAM] 格式標籤。"""
        result = self._build()
        for tag in ["[ACTION]", "[CONTENT]", "[THOUGHT]", "[HAM]"]:
            self.assertIn(tag, result)

    def test_empty_optional_fields(self):
        """可選欄位為空時不應產生錯誤。"""
        result = self._build(
            relationship_text="",
            ltm_narrative="",
            recent_dialogue="",
        )
        self.assertIsInstance(result, str)


class TestPromptExtractHam(unittest.TestCase):
    """測試 prompt_extract_ham() 函式的輸出內容。"""

    def _build(self, char="Claire", narrative="今天 Claire 在辦公室與 David 開了一個緊急會議。"):
        return prompt_extract_ham(char, narrative)

    def test_returns_string(self):
        """prompt_extract_ham() 應回傳字串。"""
        self.assertIsInstance(self._build(), str)

    def test_contains_character_name(self):
        """輸出應包含角色名稱。"""
        result = self._build(char="Claire")
        self.assertIn("Claire", result)

    def test_contains_narrative(self):
        """輸出應包含傳入的敘述文字。"""
        result = self._build(narrative="David 問了 Claire 報告進度如何。")
        self.assertIn("David", result)

    def test_contains_ham_format_hint(self):
        """輸出應包含 HAM 5 元組格式提示（管道符 |）。"""
        result = self._build()
        self.assertIn("|", result)

    def test_contains_extraction_rules(self):
        """輸出應包含「最多」或數量限制說明。"""
        result = self._build()
        self.assertIn("最多", result)


class TestPromptSelectLtm(unittest.TestCase):
    """測試 prompt_select_ltm() 函式的輸出內容。"""

    def _build(self):
        return prompt_select_ltm(
            character_name="David",
            today_narrative="David 今天跟 Claire 開會，感覺壓力很大。",
            extracted_props="David | 感到 | 壓力 | 辦公室 | 下午\nClaire | 提出 | 方案 | 辦公室 | 下午",
        )

    def test_returns_string(self):
        """prompt_select_ltm() 應回傳字串。"""
        self.assertIsInstance(self._build(), str)

    def test_contains_character_name(self):
        """輸出應包含角色名稱。"""
        result = self._build()
        self.assertIn("David", result)

    def test_contains_selection_rules(self):
        """輸出應包含篩選規則（保留/刪除等說明）。"""
        result = self._build()
        self.assertTrue("保留" in result or "刪除" in result or "最多" in result)

    def test_contains_extracted_props(self):
        """輸出應包含傳入的命題文字。"""
        result = self._build()
        self.assertIn("Claire", result)


class TestPromptLtmSummary(unittest.TestCase):
    """測試 prompt_ltm_summary() 函式的輸出內容。"""

    def _build(self):
        return prompt_ltm_summary(
            character_name="Emma",
            all_props_text="Emma | 煮飯 | 招牌菜 | 餐廳 | 每天\nEmma | 喜歡 | 美食 | 無 | 無",
        )

    def test_returns_string(self):
        """prompt_ltm_summary() 應回傳字串。"""
        self.assertIsInstance(self._build(), str)

    def test_contains_character_name(self):
        """輸出應包含角色名稱 Emma。"""
        result = self._build()
        self.assertIn("Emma", result)

    def test_contains_summary_instruction(self):
        """輸出應包含摘要指示（1-2 句話）。"""
        result = self._build()
        self.assertIn("1-2", result)


class TestPromptUpdateRelationship(unittest.TestCase):
    """測試 prompt_update_relationship() 函式的輸出內容。"""

    def test_returns_string(self):
        """prompt_update_relationship() 應回傳字串。"""
        result = prompt_update_relationship(
            character_name="Amy",
            target_name="Ben",
            initial="Amy 和 Ben 是認識多年的老朋友",
            old_summary="兩人關係良好，Amy 會記得 Ben 的咖啡喜好",
            today_narrative="Ben 今天幫 Amy 搬了一箱重東西，Amy 很感激。",
        )
        self.assertIsInstance(result, str)

    def test_contains_both_names(self):
        """輸出應包含雙方角色名稱。"""
        result = prompt_update_relationship("Amy", "Ben", "老朋友", "感情好", "無特殊互動")
        self.assertIn("Amy", result)
        self.assertIn("Ben", result)

    def test_no_old_summary_handled(self):
        """old_summary 為空時應正常運作。"""
        result = prompt_update_relationship("Claire", "David", "同事", "", "Claire 和 David 今天共同完成了報告。")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_contains_initial_relationship(self):
        """輸出應包含初始關係資訊。"""
        result = prompt_update_relationship("Emma", "Amy", "餐廳常客", "互動親切", "今天互相打招呼")
        self.assertIn("餐廳常客", result)


class TestPromptInferEmotion(unittest.TestCase):
    """測試 prompt_infer_emotion() 函式的輸出內容。"""

    def _build(self):
        return prompt_infer_emotion(
            character_name="David",
            today_narrative="David 今天被老闆批評了報告，感到很沮喪。",
            previous_emotion="平靜",
        )

    def test_returns_string(self):
        """prompt_infer_emotion() 應回傳字串。"""
        self.assertIsInstance(self._build(), str)

    def test_contains_valid_emotions(self):
        """輸出應包含至少一個合法情緒選項（來自 VALID_EMOTIONS）。"""
        result = self._build()
        found = any(e in result for e in VALID_EMOTIONS)
        self.assertTrue(found, "prompt_infer_emotion 應包含 VALID_EMOTIONS 中的情緒")

    def test_contains_previous_emotion(self):
        """輸出應包含昨天的情緒（平靜）。"""
        result = self._build()
        self.assertIn("平靜", result)

    def test_contains_character_name(self):
        """輸出應包含角色名稱 David。"""
        result = self._build()
        self.assertIn("David", result)


class TestPromptGenerateSchedule(unittest.TestCase):
    """測試 prompt_generate_schedule() 函式的輸出內容。"""

    def _build(self, **kwargs):
        defaults = dict(
            character_name="Amy",
            personality_short="溫和、熱愛咖啡",
            habit="早起，固定七點開店",
            role="咖啡師",
            day=2,
            ltm_summary="Amy 與 Ben 是好友，記得他喜歡黑咖啡。",
            today_important_events="Ben 今天幫了 Amy 一個忙",
            yesterday_schedule_text="06:00 起床\n07:30 開店",
            template_text="06:00 起床\n07:00 前往咖啡店\n22:30 睡覺",
        )
        defaults.update(kwargs)
        return prompt_generate_schedule(**defaults)

    def test_returns_string(self):
        """prompt_generate_schedule() 應回傳字串。"""
        result = self._build()
        self.assertIsInstance(result, str)

    def test_contains_character_name_and_role(self):
        """輸出應包含角色名稱和職業。"""
        result = self._build()
        self.assertIn("Amy", result)
        self.assertIn("咖啡師", result)

    def test_contains_json_format_hint(self):
        """輸出應包含 JSON 格式提示（含 time/action/location 欄位）。"""
        result = self._build()
        self.assertIn("time", result)
        self.assertIn("action", result)
        self.assertIn("location", result)

    def test_contains_day_number(self):
        """輸出應包含天數資訊。"""
        result = self._build(day=3)
        self.assertIn("3", result)

    def test_contains_action_list(self):
        """輸出應包含至少一個合法行動。"""
        result = self._build()
        found = any(action in result for action in VALID_ACTIONS)
        self.assertTrue(found, "prompt_generate_schedule 應包含 VALID_ACTIONS 中的行動")

    def test_no_ltm_summary_handled(self):
        """ltm_summary 為空時應正常運作並用替代文字。"""
        result = self._build(ltm_summary="")
        self.assertIsInstance(result, str)
        self.assertIn("尚無", result)

    def test_no_important_events_handled(self):
        """today_important_events 為空時應正常運作並用替代文字。"""
        result = self._build(today_important_events="")
        self.assertIsInstance(result, str)
        self.assertIn("無特殊", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
