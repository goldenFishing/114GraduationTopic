# ================================================================
# tests/test_markov_engine.py
# markov_engine 單元測試（使用 Python 內建 unittest）
#
# 涵蓋規格 docs/modules/markov_engine.md 的 5 個測試情境
# ================================================================

import sys
import os
import unittest

# 將專案根目錄加入 sys.path，確保可以 import core / config 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.markov_engine import compute_action_probabilities, compute_dynamic_weights
from config.action_list import VALID_ACTIONS, CHARACTER_VALID_ACTIONS


class TestComputeActionProbabilities(unittest.TestCase):

    # ----------------------------------------------------------------
    # 測試情境 1：角色 A 的機率分布鍵集合
    #   輸入：char_code="A", 其他參數使用預設（空 schedule_slot, 空 STM 等）
    #   預期輸出：probs.keys() == set(CHARACTER_VALID_ACTIONS["A"])
    # ----------------------------------------------------------------
    def test_case1_char_A_keys(self):
        probs = compute_action_probabilities(char_code="A")
        self.assertEqual(
            set(probs.keys()),
            set(CHARACTER_VALID_ACTIONS["A"]),
            "角色 A 的機率分布鍵集合應等於 CHARACTER_VALID_ACTIONS['A']",
        )

    # ----------------------------------------------------------------
    # 測試情境 2：機率總和約等於 1.0
    #   輸入：char_code="B", 各參數用合理預設值
    #   預期輸出：sum(probs.values()) ≈ 1.0（±0.001）
    # ----------------------------------------------------------------
    def test_case2_prob_sum_char_B(self):
        probs = compute_action_probabilities(
            char_code="B",
            schedule_slot=None,
            stm_recent_verbs=[],
            perception={},
            co_located=[],
            emotion="平靜",
        )
        total = sum(probs.values())
        self.assertAlmostEqual(
            total,
            1.0,
            delta=0.001,
            msg=f"機率總和應約等於 1.0，實際為 {total}",
        )

    # ----------------------------------------------------------------
    # 測試情境 3：B 的機率分布不含 A 專屬動作
    #   輸入：char_code="B"
    #   預期輸出："賣咖啡" 不在 probs.keys()，"收銀" 在 probs.keys()
    # ----------------------------------------------------------------
    def test_case3_char_B_excludes_A_actions(self):
        probs = compute_action_probabilities(char_code="B")
        self.assertNotIn(
            "賣咖啡",
            probs.keys(),
            "角色 B 的機率分布不應包含角色 A 專屬動作「賣咖啡」",
        )
        self.assertIn(
            "收銀",
            probs.keys(),
            "角色 B 的機率分布應包含「收銀」",
        )

    # ----------------------------------------------------------------
    # 測試情境 4：char_code 為空字串時退回全域 VALID_ACTIONS
    #   輸入：char_code=""
    #   預期輸出：probs.keys() == set(VALID_ACTIONS)
    # ----------------------------------------------------------------
    def test_case4_empty_char_code_fallback(self):
        probs = compute_action_probabilities(char_code="")
        self.assertEqual(
            set(probs.keys()),
            set(VALID_ACTIONS),
            "char_code 為空字串時，機率分布鍵集合應退回全域 VALID_ACTIONS",
        )

    # ----------------------------------------------------------------
    # 測試情境 5：return_breakdown=True 時的 probs 鍵集合
    #   輸入：char_code="C", return_breakdown=True
    #   預期輸出：result["probs"].keys() == set(CHARACTER_VALID_ACTIONS["C"])
    # ----------------------------------------------------------------
    def test_case5_return_breakdown_char_C(self):
        result = compute_action_probabilities(char_code="C", return_breakdown=True)
        self.assertIn("probs", result, "return_breakdown=True 時回傳值應包含 'probs' 鍵")
        self.assertEqual(
            set(result["probs"].keys()),
            set(CHARACTER_VALID_ACTIONS["C"]),
            "return_breakdown=True 時，probs 鍵集合應等於 CHARACTER_VALID_ACTIONS['C']",
        )


class TestComputeDynamicWeights(unittest.TestCase):
    """測試動態三來源加權計算邏輯。"""

    # ----------------------------------------------------------------
    # 測試情境 6：習慣穩定狀態 → β 應明顯高於底線
    #   條件：最近 5 筆動詞全部相同（entropy=0）、地點全部相同（S_loc=1.0）
    #   預期：beta > alpha, beta > gamma（習慣主導）
    # ----------------------------------------------------------------
    def test_case6_habit_state_beta_dominant(self):
        verbs = ["休息", "休息", "休息", "休息", "休息"]
        locs  = ["A家", "A家", "A家", "A家", "A家"]
        alpha, beta, gamma = compute_dynamic_weights(
            stm_recent_verbs = verbs,
            stm_recent_locs  = locs,
            current_loc      = "A家",
            prev_loc         = "A家",
            prev_yolo        = [],
            current_yolo     = [],
            schedule_slot    = None,
        )
        self.assertGreater(beta, alpha, "習慣穩定時 β 應大於 α")
        self.assertGreater(beta, gamma, "習慣穩定時 β 應大於 γ")
        total = alpha + beta + gamma
        self.assertAlmostEqual(total, 1.0, places=5, msg="三來源加總應為 1.0")

    # ----------------------------------------------------------------
    # 測試情境 7：地點剛改變 + 新場景物件出現 → γ 應高於底線
    #   條件：上一地點與當前不同，且 yolo 新增 2 個物件
    # ----------------------------------------------------------------
    def test_case7_location_change_gamma_elevated(self):
        verbs = ["前往", "散步", "休息", "前往", "散步"]
        locs  = ["A家", "A家", "A家", "A家", "咖啡店"]
        alpha, beta, gamma = compute_dynamic_weights(
            stm_recent_verbs = verbs,
            stm_recent_locs  = locs,
            current_loc      = "咖啡店",
            prev_loc         = "A家",
            prev_yolo        = ["杯子"],
            current_yolo     = ["杯子", "Ben", "Claire"],
            schedule_slot    = None,
        )
        from config.world_config import MARKOV_BASE_GAMMA
        self.assertGreater(gamma, MARKOV_BASE_GAMMA,
                           "地點改變 + 新物件時 γ 應高於底線")
        total = alpha + beta + gamma
        self.assertAlmostEqual(total, 1.0, places=5)

    # ----------------------------------------------------------------
    # 測試情境 8：新時段壓力 → α 應高於底線
    #   條件：schedule_slot 有新行動，STM 最近動詞與 slot 不同（P_sched=1.0）
    # ----------------------------------------------------------------
    def test_case8_new_schedule_slot_alpha_elevated(self):
        verbs = ["休息", "休息", "滑手機", "休息", "休息"]
        locs  = ["A家"] * 5
        slot  = {"action": "賣咖啡", "location": "咖啡店", "completed": False}
        alpha, beta, gamma = compute_dynamic_weights(
            stm_recent_verbs = verbs,
            stm_recent_locs  = locs,
            current_loc      = "A家",
            prev_loc         = "A家",
            prev_yolo        = [],
            current_yolo     = [],
            schedule_slot    = slot,
        )
        from config.world_config import MARKOV_BASE_ALPHA
        self.assertGreater(alpha, MARKOV_BASE_ALPHA,
                           "新時段時 α 應高於底線")
        total = alpha + beta + gamma
        self.assertAlmostEqual(total, 1.0, places=5)

    # ----------------------------------------------------------------
    # 測試情境 9：三來源加總恆為 1.0（各種極端輸入）
    # ----------------------------------------------------------------
    def test_case9_weights_always_sum_to_one(self):
        cases = [
            # (verbs, locs, curr_loc, prev_loc, prev_yolo, curr_yolo, slot)
            ([], [], "", "", [], [], None),
            (["休息"], ["A家"], "A家", "A家", [], [], None),
            (["前往", "前往", "前往", "前往", "前往"],
             ["A家", "B家", "咖啡店", "超市", "廣場"],
             "廣場", "超市",
             ["杯子", "椅子"], ["桌子", "人1", "人2", "人3"],
             {"action": "散步", "completed": False}),
        ]
        for verbs, locs, cur, prev, py, cy, slot in cases:
            alpha, beta, gamma = compute_dynamic_weights(
                stm_recent_verbs = verbs,
                stm_recent_locs  = locs,
                current_loc      = cur,
                prev_loc         = prev,
                prev_yolo        = py,
                current_yolo     = cy,
                schedule_slot    = slot,
            )
            total = alpha + beta + gamma
            self.assertAlmostEqual(
                total, 1.0, places=5,
                msg=f"三來源加總應為 1.0，實際 {total:.6f}（輸入：verbs={verbs}）"
            )

    # ----------------------------------------------------------------
    # 測試情境 10：return_breakdown=True 包含 dynamic_weights
    # ----------------------------------------------------------------
    def test_case10_breakdown_includes_dynamic_weights(self):
        result = compute_action_probabilities(
            char_code        = "A",
            stm_recent_verbs = ["賣咖啡", "賣咖啡", "賣咖啡"],
            stm_recent_locs  = ["咖啡店", "咖啡店", "咖啡店"],
            return_breakdown = True,
        )
        self.assertIn("dynamic_weights", result,
                      "return_breakdown=True 時應包含 'dynamic_weights' 鍵")
        dw = result["dynamic_weights"]
        self.assertIn("alpha", dw)
        self.assertIn("beta",  dw)
        self.assertIn("gamma", dw)
        total = dw["alpha"] + dw["beta"] + dw["gamma"]
        self.assertAlmostEqual(total, 1.0, places=3,
                               msg="dynamic_weights 三值加總應為 1.0")


if __name__ == "__main__":
    unittest.main()
