# ================================================================
# tests/test_memory_stm.py
# 短期記憶（STM）單元測試
# ================================================================

import sys
import os
import unittest

# 確保 project root 在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory_stm import STM, make_turn_id, _is_summary_turn


def _make_char_data():
    """建立最小可用的 character_data dict。"""
    return {"stm": {"turns": []}}


def _sample_turn_parts():
    return (
        {"location": "咖啡店", "yolo_desc": ["A", "B"], "scene_text": "早上"},
        {"input_text": "早安", "action": "對話", "target": "Ben", "content": "今天想喝什麼"},
        {"thought": "Ben看起來心情不錯", "emotion": "平靜"},
    )


class TestSTMAddTurn(unittest.TestCase):
    """測試 add_turn 寫入功能"""

    def setUp(self):
        self.data = _make_char_data()
        self.stm = STM(self.data)

    def test_add_turn_increases_count(self):
        """add_turn 後筆數應增加 1"""
        perc, evt, inn = _sample_turn_parts()
        self.stm.add_turn("D001_T001", "08:00", perc, evt, inn)
        self.assertEqual(self.stm.count(), 1)

    def test_add_turn_returns_dict(self):
        """add_turn 應回傳包含 turn_id 的 dict"""
        perc, evt, inn = _sample_turn_parts()
        result = self.stm.add_turn("D001_T002", "08:00", perc, evt, inn)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["turn_id"], "D001_T002")

    def test_add_turn_normalizes_perception(self):
        """add_turn 應確保 perception 三欄位存在"""
        self.stm.add_turn("D001_T003", "09:00", {}, {}, {})
        turn = self.stm.get_all()[0]
        self.assertIn("location", turn["perception"])
        self.assertIn("yolo_desc", turn["perception"])
        self.assertIn("scene_text", turn["perception"])

    def test_add_multiple_turns(self):
        """多次 add_turn 累積筆數正確"""
        perc, evt, inn = _sample_turn_parts()
        for i in range(5):
            self.stm.add_turn(f"D001_T{i+1:03d}", "08:00", perc, evt, inn)
        self.assertEqual(self.stm.count(), 5)

    def test_add_turn_stores_in_character_data(self):
        """add_turn 直接修改 character_data dict（引用語意）"""
        perc, evt, inn = _sample_turn_parts()
        self.stm.add_turn("D001_T004", "10:00", perc, evt, inn)
        # 驗證 data dict 本身也更新了
        self.assertEqual(len(self.data["stm"]["turns"]), 1)


class TestSTMGetRecent(unittest.TestCase):
    """測試 get_recent 讀取功能"""

    def setUp(self):
        self.data = _make_char_data()
        self.stm = STM(self.data)
        perc, evt, inn = _sample_turn_parts()
        for i in range(8):
            self.stm.add_turn(f"D001_T{i+1:03d}", "08:00", perc, evt, inn)

    def test_get_recent_returns_correct_count(self):
        """get_recent(3) 應回傳 3 筆"""
        result = self.stm.get_recent(3)
        self.assertEqual(len(result), 3)

    def test_get_recent_returns_latest(self):
        """get_recent 應回傳最新的幾筆"""
        result = self.stm.get_recent(2)
        self.assertEqual(result[1]["turn_id"], "D001_T008")

    def test_get_recent_excludes_summary_turns(self):
        """get_recent 不應包含摘要 turn（T000）"""
        self.stm.add_summary_turn(2, "昨日一切平靜")
        recent = self.stm.get_recent(5)
        for t in recent:
            self.assertFalse(_is_summary_turn(t))

    def test_get_recent_all_when_n_exceeds_count(self):
        """n 超過總筆數時應回傳全部非摘要 turn"""
        result = self.stm.get_recent(100)
        self.assertEqual(len(result), 8)


class TestSTMShrinkToSummary(unittest.TestCase):
    """測試 shrink_to_summary 濃縮後縮減"""

    def setUp(self):
        self.data = _make_char_data()
        self.stm = STM(self.data)
        perc, evt, inn = _sample_turn_parts()
        for i in range(10):
            self.stm.add_turn(f"D001_T{i+1:03d}", "08:00", perc, evt, inn)

    def test_shrink_keeps_summary_turn(self):
        """shrink 後第一筆應為摘要 turn"""
        self.stm.shrink_to_summary("Amy 昨天在咖啡店工作。", new_day=2, keep_recent=3)
        all_turns = self.stm.get_all()
        self.assertTrue(_is_summary_turn(all_turns[0]))

    def test_shrink_keeps_recent_count(self):
        """shrink 後保留 keep_recent 筆（加上摘要 turn）"""
        self.stm.shrink_to_summary("昨日摘要", new_day=2, keep_recent=3)
        non_summary = self.stm.get_recent(100)
        self.assertEqual(len(non_summary), 3)

    def test_shrink_summary_text_stored(self):
        """shrink 後摘要文字應正確儲存在摘要 turn 中"""
        summary_text = "Amy 昨天工作很努力，晚上回家後休息。"
        self.stm.shrink_to_summary(summary_text, new_day=2, keep_recent=2)
        all_turns = self.stm.get_all()
        self.assertIn(summary_text, all_turns[0]["inner"]["thought"])


class TestSTMTickId(unittest.TestCase):
    """測試 tick_id 功能與 get_latest_if_this_tick 方法。"""

    def setUp(self):
        self.data = {"stm": {"turns": []}}
        self.stm = STM(self.data)

    def test_add_turn_with_tick_id(self):
        """add_turn 傳入 tick_id 後，turn 中應存有 tick_id 欄位。"""
        perc = {"location": "咖啡店", "yolo_desc": ["A"], "scene_text": ""}
        evt  = {"action": "賣咖啡", "target": "", "content": ""}
        inn  = {"thought": "忙碌中", "emotion": "平靜"}
        self.stm.add_turn("D001_T001", "08:00", perc, evt, inn, tick_id="D001_T001")
        turn = self.stm.get_all()[0]
        self.assertEqual(turn.get("tick_id"), "D001_T001")

    def test_get_latest_if_this_tick_matches(self):
        """get_latest_if_this_tick 應在最新 turn 的 tick_id 符合時回傳非空字串。"""
        perc = {"location": "咖啡店", "yolo_desc": ["A"], "scene_text": ""}
        evt  = {"action": "賣咖啡", "target": "", "content": "今天好忙"}
        inn  = {"thought": "忙", "emotion": "平靜"}
        self.stm.add_turn("D001_T001", "08:00", perc, evt, inn, tick_id="D001_T001")
        result = self.stm.get_latest_if_this_tick("D001_T001")
        self.assertIsInstance(result, str)
        # 應回傳 content 或 action，不應為空（因為有內容）
        self.assertGreater(len(result), 0)

    def test_get_latest_if_this_tick_no_match(self):
        """get_latest_if_this_tick tick_id 不符時應回傳空字串。"""
        perc = {"location": "咖啡店", "yolo_desc": [], "scene_text": ""}
        evt  = {"action": "賣咖啡", "target": "", "content": ""}
        inn  = {"thought": "", "emotion": "平靜"}
        self.stm.add_turn("D001_T001", "08:00", perc, evt, inn, tick_id="D001_T001")
        result = self.stm.get_latest_if_this_tick("D001_T002")  # 不同 tick_id
        self.assertEqual(result, "")

    def test_get_latest_if_this_tick_empty_stm(self):
        """空 STM 時 get_latest_if_this_tick 應回傳空字串。"""
        result = self.stm.get_latest_if_this_tick("D001_T001")
        self.assertEqual(result, "")


class TestSTMSafety(unittest.TestCase):
    """測試安全閥與工具函式"""

    def test_is_over_safety_limit_false_when_empty(self):
        """空 STM 不應觸發安全閥"""
        stm = STM(_make_char_data())
        self.assertFalse(stm.is_over_safety_limit())

    def test_make_turn_id_format(self):
        """make_turn_id 應產生正確格式"""
        tid = make_turn_id(3, 7)
        self.assertEqual(tid, "D003_T007")

    def test_clear_empties_stm(self):
        """clear() 後 count 應為 0"""
        stm = STM(_make_char_data())
        perc, evt, inn = _sample_turn_parts()
        stm.add_turn("D001_T001", "08:00", perc, evt, inn)
        stm.clear()
        self.assertEqual(stm.count(), 0)

    def test_next_turn_number_increments(self):
        """next_turn_number 應在現有 turn 最大編號上加 1"""
        stm = STM(_make_char_data())
        perc, evt, inn = _sample_turn_parts()
        stm.add_turn("D001_T001", "08:00", perc, evt, inn)
        stm.add_turn("D001_T002", "09:00", perc, evt, inn)
        self.assertEqual(stm.next_turn_number(1), 3)

    def test_get_today_narrative_returns_string(self):
        """get_today_narrative 應回傳非空字串"""
        stm = STM(_make_char_data())
        perc, evt, inn = _sample_turn_parts()
        stm.add_turn("D001_T001", "08:00", perc, evt, inn)
        narrative = stm.get_today_narrative()
        self.assertIsInstance(narrative, str)
        self.assertTrue(len(narrative) > 0)

    def test_get_recent_actions_returns_list(self):
        """get_recent_actions 應回傳行動動詞列表"""
        stm = STM(_make_char_data())
        perc, evt, inn = _sample_turn_parts()
        stm.add_turn("D001_T001", "08:00", perc, evt, inn)
        actions = stm.get_recent_actions(3)
        self.assertIsInstance(actions, list)


class TestSTMSerialization(unittest.TestCase):
    """測試序列化相關行為（透過 character_data 引用）"""

    def test_stm_data_reflects_in_character_dict(self):
        """STM 對 turns 的修改應直接反映在原始 character_data 中"""
        char_data = {"name": "Amy", "stm": {"turns": []}}
        stm = STM(char_data)
        perc, evt, inn = _sample_turn_parts()
        stm.add_turn("D001_T001", "08:00", perc, evt, inn)
        # 確認 character_data["stm"]["turns"] 同步更新
        self.assertEqual(len(char_data["stm"]["turns"]), 1)
        self.assertEqual(char_data["stm"]["turns"][0]["turn_id"], "D001_T001")

    def test_init_creates_stm_structure_if_missing(self):
        """若 character_data 缺少 stm 結構，__init__ 應自動建立"""
        char_data = {}
        stm = STM(char_data)
        self.assertIn("stm", char_data)
        self.assertIn("turns", char_data["stm"])


class TestSTMIntegrationGaps(unittest.TestCase):
    """測試與暴露 yolo_desc 串列型別保存與 narrative 格式化之漏洞。"""

    def setUp(self):
        self.data = {"stm": {"turns": []}}
        self.stm = STM(self.data)

    def test_yolo_desc_remains_list(self):
        """yolo_desc 在 add_turn 後應維持串列型別，而不是被強制轉成字串。"""
        perc = {"location": "咖啡店", "yolo_desc": ["A", "B"], "scene_text": ""}
        self.stm.add_turn("D001_T001", "08:00", perc, {}, {})
        
        # 取得最新的一筆 turn
        turn = self.stm.get_all()[0]
        # 驗證 yolo_desc 的型別應該是 list，而不是 str
        self.assertIsInstance(turn["perception"]["yolo_desc"], list)
        
        # 驗證 get_prev_yolo() 應回傳原始串列
        prev_yolo = self.stm.get_prev_yolo()
        self.assertEqual(prev_yolo, ["A", "B"])

    def test_narrative_formats_yolo_list_correctly(self):
        """get_today_narrative 應將串列型別的 yolo_desc 格式化為人名（如 Amy、Ben）。"""
        perc = {"location": "咖啡店", "yolo_desc": ["A", "B"], "scene_text": ""}
        self.stm.add_turn("D001_T001", "08:00", perc, {}, {})
        narrative = self.stm.get_today_narrative()
        
        # 預期輸出包含 "Amy、Ben" 而不是包含 "['A', 'B']"
        self.assertIn("Amy、Ben", narrative)
        self.assertNotIn("['A', 'B']", narrative)


if __name__ == "__main__":
    unittest.main(verbosity=2)

