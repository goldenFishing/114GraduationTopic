# ================================================================
# tests/test_agent_decide.py
# agent_decide 模組的單元測試
#
# 涵蓋規格 docs/modules/agent_decide.md 中的 3 個測試情境：
#   1. Markov 路徑的 action_id 欄位存在
#   2. 角色 A 睡覺時的 action_id == 40
#   3. 前往動作 action_id 為 None
# ================================================================

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# 確保可以 import 專案根目錄下的套件
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.action_list import action_id_resolver


class TestActionIdResolverDirect(unittest.TestCase):
    """測試情境 2、3：直接呼叫 action_id_resolver，不需要跑完整 decide()。"""

    def test_case2_sleep_action_id(self):
        """測試情境 2：角色 A 在 A家 睡覺 → action_id == 40。

        action="睡覺", char.code="A", char.current_location="A家"
        預期：action_id_resolver("睡覺", "A", "A家") == 40
        """
        result = action_id_resolver("睡覺", "A", "A家")
        self.assertEqual(result, 40)

    def test_case3_goto_action_id_is_none(self):
        """測試情境 3：前往動作 → action_id 為 None（前往沒有 ActionID）。

        action="前往", char_code="A", current_location="咖啡店"
        預期：action_id_resolver("前往", "A", "咖啡店") is None
        """
        result = action_id_resolver("前往", "A", "咖啡店")
        self.assertIsNone(result)


class TestAgentDecideMarkovPath(unittest.TestCase):
    """測試情境 1：Markov 路徑的 action_id 欄位存在且型別正確。"""

    def _make_mock_agent(self):
        """建立一個 mock Agent，設定所有必要的依賴屬性。"""
        from agent.agent import Agent

        # --- mock character ---
        char = MagicMock()
        char.code = "A"
        char.current_location = "A家"
        char.emotion = "平靜"
        char.current_action = "休息"
        char.day = 1
        char.get_current_slot.return_value = {"time": "08:00", "action": "休息", "location": "A家"}
        char.get_confusion_weights.return_value = {
            "w_yolo": 0.3, "w_input": 0.3, "w_action": 0.2, "w_scene": 0.2, "threshold": 0.5
        }
        char.get_confusion_threshold.return_value = 0.5
        char.get_today_actions.return_value = []
        char.get_relationship.return_value = {"summary": "", "initial": ""}

        # --- mock stm ---
        stm = MagicMock()
        stm.get_recent_actions.return_value = []
        stm.next_turn_number.return_value = 1

        # --- mock ltm ---
        ltm = MagicMock()
        ltm.get_summary.return_value = ""
        ltm.ltm_index = {}      # 新增：compute_S 需要 dict 型別的 ltm_index

        # --- mock value_tracker ---
        value_tracker = MagicMock()
        value_tracker.get_scores.return_value = {}
        value_tracker.compute_reward.return_value = 0.0

        # --- mock weight_adapter ---
        weight_adapter = MagicMock()
        weight_adapter.get_weights.return_value = {"alpha": 0.45, "beta": 0.35, "gamma": 0.2}

        # 建立 Agent（不真正初始化，直接 bypass __init__）
        agent = object.__new__(Agent)
        agent.character = char
        agent.stm = stm
        agent.ltm = ltm
        agent.graph = MagicMock()
        agent.loader = None
        agent.prompt_builder = MagicMock()
        agent.process_log = []
        agent.value_tracker = value_tracker
        agent.weight_adapter = weight_adapter
        agent._prev_emotion = "平靜"
        agent._prev_C = 0.5

        return agent

    def test_case1_markov_path_has_action_id(self):
        """測試情境 1：Markov 路徑回傳 dict 含 "action_id" key，值為 int 或 None。

        強制 confusion mode="intuitive"（C < threshold），確認 decide() 走 Markov 路徑。
        驗證回傳 dict 含 "action_id" 且型別為 int 或 None。
        """
        agent = self._make_mock_agent()

        # Markov 機率分布：強制「休息」機率最高
        fake_probs = {"休息": 0.6, "散步": 0.2, "滑手機": 0.1, "對話": 0.1}
        fake_breakdown = {
            "probs": fake_probs,
            "breakdown": {
                "schedule": {}, "inertia": {}, "situation": {},
                "value": {}, "weights": (0.4, 0.3, 0.3, 0.0),
            },
        }

        # confusion 強制走 intuitive（Markov）路徑
        fake_confusion = {
            "mode": "intuitive",
            "K": 0.0,
            "C": 0.3,
        }

        with patch("agent.agent.compute_action_probabilities", return_value=fake_breakdown), \
             patch("agent.agent.eval_confusion", return_value=fake_confusion), \
             patch("agent.agent.resolve_dialogue_target", return_value=("休息", "")):

            perception = {
                "location": "A家",
                "yolo_desc": [],      # ← 從 "" 改為 []（新格式）
            }
            result = agent.decide(scene="A家", perception=perception)

        # 驗證 "action_id" key 存在
        self.assertIn("action_id", result, "decide() 回傳 dict 應含 'action_id' key")

        # 驗證型別為 int 或 None
        action_id = result["action_id"]
        self.assertTrue(
            isinstance(action_id, int) or action_id is None,
            f"action_id 應為 int 或 None，實際為 {type(action_id).__name__}（值：{action_id}）"
        )


if __name__ == "__main__":
    unittest.main()
