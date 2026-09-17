# ================================================================
# tests/test_action_list.py
# action_list 模組的單元測試
#
# 涵蓋規格 docs/modules/action_list.md 中的 6 個測試情境：
#   1. action_id_resolver 位置精確匹配
#   2. action_id_resolver 不限位置 fallback
#   3. 角色無法執行的動作 → None
#   4. 睡覺位置匹配
#   5. CHARACTER_VALID_ACTIONS 完整性
#   6. ACTION_TABLE 長度
# ================================================================

import sys
import os
import unittest

# 確保可以 import 專案根目錄下的 config 套件
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.action_list import (
    ACTION_TABLE,
    CHARACTER_VALID_ACTIONS,
    action_id_resolver,
)


class TestActionIdResolver(unittest.TestCase):
    """測試 action_id_resolver 函式的各種情境。"""

    def test_case1_exact_location_match(self):
        """測試情境 1：位置精確匹配時應回傳對應 ID。

        abstract_verb="吃飯", char_code="A", current_location="A家"
        → 預期回傳 19（吃飯 在A家，location="A家"）
        """
        result = action_id_resolver("吃飯", "A", "A家")
        self.assertEqual(result, 19)

    def test_case2_no_location_fallback(self):
        """測試情境 2：沒有精確位置匹配時應回傳 location="" 的 entry。

        abstract_verb="吃飯", char_code="A", current_location="咖啡店"
        → 預期回傳 6（吃飯 餐廳，location=""）
        """
        result = action_id_resolver("吃飯", "A", "咖啡店")
        self.assertEqual(result, 6)

    def test_case3_char_cannot_do_action(self):
        """測試情境 3：角色無法執行的動作應回傳 None。

        abstract_verb="收銀", char_code="A", current_location="超市"
        → 預期回傳 None（角色 A 不在 id=12 的 chars 清單中）
        """
        result = action_id_resolver("收銀", "A", "超市")
        self.assertIsNone(result)

    def test_case4_sleep_location_match(self):
        """測試情境 4：睡覺位置精確匹配。

        abstract_verb="睡覺", char_code="B", current_location="B家"
        → 預期回傳 41（睡覺 在B家，location="B家"）
        """
        result = action_id_resolver("睡覺", "B", "B家")
        self.assertEqual(result, 41)


class TestCharacterValidActions(unittest.TestCase):
    """測試 CHARACTER_VALID_ACTIONS 的內容完整性。"""

    def test_case5_char_e_valid_actions(self):
        """測試情境 5：角色 E 的合法動詞清單包含特定動詞，並排除其他角色專屬動詞。

        CHARACTER_VALID_ACTIONS["E"] 應包含 "備料"、"煮飯"、"服務客人"，
        且不包含 "收銀"、"賣咖啡"。
        """
        actions_e = CHARACTER_VALID_ACTIONS["E"]

        # 應包含的動詞
        self.assertIn("備料", actions_e)
        self.assertIn("煮飯", actions_e)
        self.assertIn("服務客人", actions_e)

        # 不應包含的動詞
        self.assertNotIn("收銀", actions_e)
        self.assertNotIn("賣咖啡", actions_e)


class TestActionTable(unittest.TestCase):
    """測試 ACTION_TABLE 的結構與資料正確性。"""

    def test_case6_action_table_length(self):
        """測試情境 6：ACTION_TABLE 應包含恰好 45 筆資料。"""
        self.assertEqual(len(ACTION_TABLE), 45)


if __name__ == "__main__":
    unittest.main()
