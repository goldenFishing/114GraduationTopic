# ================================================================
# tests/test_mental_state.py
# mental_state 單元測試（unittest + pytest compatible）
#
# 涵蓋：情緒重置、情緒驗證、困惑度計算 U/K/S/C、模式決策、閾值調整
# ================================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.mental_state import (
    should_update_emotion,
    reset_to_baseline,
    normalize_emotion,
    decide_new_emotion,
    compute_U,
    compute_K,
    compute_S,
    compute_C,
    decide_mode,
    evaluate,
    adjust_threshold_by_emotion,
    BASELINE_EMOTION,
    DELIBERATE_K_OVERRIDE,
    LOCATION_BASE_S,
)
from config.world_config import EMOTION_RESET_THRESHOLD, VALID_EMOTIONS


# ================================================================
# 情緒模組（Emotion）測試
# ================================================================

class TestShouldUpdateEmotion(unittest.TestCase):
    """測試 should_update_emotion 閾值邏輯。"""

    def test_below_threshold_returns_false(self):
        """K 值低於閾值時不應觸發情緒更新。"""
        self.assertFalse(should_update_emotion(EMOTION_RESET_THRESHOLD - 0.01))

    def test_at_threshold_returns_true(self):
        """K 值剛好等於閾值時應觸發情緒更新。"""
        self.assertTrue(should_update_emotion(EMOTION_RESET_THRESHOLD))

    def test_above_threshold_returns_true(self):
        """K 值高於閾值時應觸發情緒更新。"""
        self.assertTrue(should_update_emotion(1.0))

    def test_zero_returns_false(self):
        """K 值為 0 時不應觸發更新。"""
        self.assertFalse(should_update_emotion(0.0))


class TestResetToBaseline(unittest.TestCase):
    """測試 reset_to_baseline 回傳預設情緒。"""

    def test_returns_baseline_emotion(self):
        result = reset_to_baseline()
        self.assertEqual(result, BASELINE_EMOTION)
        self.assertEqual(result, "平靜")


class TestNormalizeEmotion(unittest.TestCase):
    """測試 normalize_emotion 驗證與 fallback 機制。"""

    def test_valid_emotion_passes_through(self):
        """合法情緒直接回傳。"""
        for emotion in VALID_EMOTIONS:
            with self.subTest(emotion=emotion):
                self.assertEqual(normalize_emotion(emotion), emotion)

    def test_invalid_emotion_returns_baseline(self):
        """非合法情緒應 fallback 為平靜。"""
        self.assertEqual(normalize_emotion("生氣"), BASELINE_EMOTION)
        self.assertEqual(normalize_emotion("unknown"), BASELINE_EMOTION)

    def test_empty_string_returns_baseline(self):
        """空字串應 fallback 為平靜。"""
        self.assertEqual(normalize_emotion(""), BASELINE_EMOTION)

    def test_none_like_empty_returns_baseline(self):
        """None 強制轉字串後應 fallback 為平靜。"""
        self.assertEqual(normalize_emotion(None), BASELINE_EMOTION)

    def test_whitespace_stripped(self):
        """帶空白的合法情緒應被 strip 並通過。"""
        self.assertEqual(normalize_emotion("  開心  "), "開心")


class TestDecideNewEmotion(unittest.TestCase):
    """測試 decide_new_emotion 整合邏輯。"""

    def test_low_k_returns_baseline_without_model(self):
        """K 值低於閾值，無論有無模型都回歸平靜。"""
        result = decide_new_emotion(
            character_name="Amy",
            today_max_K=0.1,
            today_narrative="Amy 今天平靜地工作",
            previous_emotion="平靜",
            model_fn=None,
        )
        self.assertEqual(result, BASELINE_EMOTION)

    def test_high_k_but_no_model_returns_baseline(self):
        """K 值高但無模型時也應回歸平靜。"""
        result = decide_new_emotion(
            character_name="Ben",
            today_max_K=0.9,
            today_narrative="Ben 今天遇到很大的衝突",
            previous_emotion="緊張",
            model_fn=None,
        )
        self.assertEqual(result, BASELINE_EMOTION)

    def test_high_k_with_model_returns_normalized_emotion(self):
        """K 值高且有模型時，應回傳 normalize 後的情緒。"""
        mock_model = lambda prompt: "開心"
        result = decide_new_emotion(
            character_name="Claire",
            today_max_K=0.8,
            today_narrative="Claire 今天非常開心",
            previous_emotion="平靜",
            model_fn=mock_model,
        )
        self.assertIn(result, VALID_EMOTIONS)

    def test_model_invalid_output_returns_baseline(self):
        """模型輸出非法情緒時應 fallback 為平靜。"""
        mock_model = lambda prompt: "超級生氣"
        result = decide_new_emotion(
            character_name="David",
            today_max_K=0.8,
            today_narrative="David 今天發生大事",
            previous_emotion="平靜",
            model_fn=mock_model,
        )
        self.assertEqual(result, BASELINE_EMOTION)

    def test_model_exception_returns_baseline(self):
        """模型拋出例外時應 fallback 為平靜。"""
        def bad_model(prompt):
            raise RuntimeError("模型服務中斷")

        result = decide_new_emotion(
            character_name="Emma",
            today_max_K=0.9,
            today_narrative="Emma 今天很混亂",
            previous_emotion="平靜",
            model_fn=bad_model,
        )
        self.assertEqual(result, BASELINE_EMOTION)


# ================================================================
# 困惑度模組（Confusion）測試
# ================================================================

class TestComputeU(unittest.TestCase):
    """測試不確定性計算 compute_U。"""

    def test_empty_candidates_returns_zero(self):
        """空候選列表應回傳 0.0。"""
        self.assertEqual(compute_U([]), 0.0)

    def test_single_candidate_returns_zero(self):
        """只有一個候選應回傳 0.0（完全確定）。"""
        self.assertEqual(compute_U([{"action": "工作", "score": 0.9}]), 0.0)

    def test_high_gap_returns_low_u(self):
        """最高分與次高分差距大時，U 應接近 0（高確定性）。"""
        candidates = [
            {"action": "工作", "score": 0.9},
            {"action": "休息", "score": 0.1},
        ]
        U = compute_U(candidates)
        self.assertLess(U, 0.3)

    def test_low_gap_returns_high_u(self):
        """最高分與次高分差距小時，U 應接近 1.0（低確定性）。"""
        candidates = [
            {"action": "工作", "score": 0.51},
            {"action": "休息", "score": 0.50},
        ]
        U = compute_U(candidates)
        self.assertGreater(U, 0.9)

    def test_result_in_range(self):
        """U 應在 [0, 1] 之間。"""
        candidates = [
            {"action": "工作", "score": 0.6},
            {"action": "散步", "score": 0.3},
            {"action": "休息", "score": 0.1},
        ]
        U = compute_U(candidates)
        self.assertGreaterEqual(U, 0.0)
        self.assertLessEqual(U, 1.0)


class TestComputeK(unittest.TestCase):
    """測試衝突程度計算 compute_K（Salience-First）。"""

    def test_empty_event_and_no_delta_returns_zero(self):
        """無事件且無人員變動時應直接回傳 0.0（早退條件）。"""
        K = compute_K(
            this_tick_event="",
            current_action="工作",
            delta_people={"arrived": [], "departed": []},
        )
        self.assertEqual(K, 0.0)

    def test_none_delta_people_returns_zero(self):
        """delta_people 為 None 且無事件時應回傳 0.0。"""
        K = compute_K(this_tick_event="", current_action="工作")
        self.assertEqual(K, 0.0)

    def test_logical_conflict_increases_k(self):
        """有邏輯衝突（離開 + 等待）時 K 應增加。"""
        K = compute_K(
            this_tick_event="再見，我走了",
            current_action="等待",
        )
        self.assertGreater(K, 0.0)

    def test_strong_emotion_keyword_increases_k(self):
        """事件含強情緒關鍵字（思緒紊亂）時 K 應增加。"""
        K = compute_K(
            this_tick_event="Amy 思緒紊亂，不知所措",
            current_action="休息",
        )
        self.assertGreater(K, 0.0)

    def test_arrived_people_increases_k(self):
        """有人到達（arrived 非空）時 K 應有社交分貢獻。"""
        K = compute_K(
            this_tick_event="",
            current_action="工作",
            delta_people={"arrived": ["B", "C"], "departed": []},
        )
        self.assertGreater(K, 0.0)

    def test_k_capped_at_one(self):
        """K 值不應超過 1.0。"""
        K = compute_K(
            this_tick_event="緊急！快！危險！說不清楚，心亂如麻",
            current_action="睡覺",
            delta_people={"arrived": ["A","B","C","D","E"], "departed": []},
        )
        self.assertLessEqual(K, 1.0)

    def test_k_in_valid_range(self):
        """K 應在 [0.0, 1.0] 之間。"""
        K = compute_K("測試事件", "工作")
        self.assertGreaterEqual(K, 0.0)
        self.assertLessEqual(K, 1.0)


class TestComputeS(unittest.TestCase):
    """測試驚訝程度計算 compute_S（Bayesian Surprise）。"""

    def test_cold_start_no_ltm_high_novelty(self):
        """冷啟動（ltm_index=None）時 S 應偏高（新奇度最大）。"""
        S = compute_S(
            curr_people=["B"],
            location="咖啡店",
            ltm_index=None,
        )
        # freq=0 → S_novelty = 0.7，加上底噪和 variety
        self.assertGreater(S, 0.5)

    def test_familiar_combo_low_s(self):
        """頻繁見過的組合（ltm_index count 高）時 S 應較低。"""
        ltm_index = {("咖啡店", frozenset(["B"])): 50}
        S = compute_S(
            curr_people=["B"],
            location="咖啡店",
            ltm_index=ltm_index,
        )
        self.assertLess(S, 0.2)

    def test_novel_combo_high_s(self):
        """從未見過的組合（ltm_index count=0）時 S 應較高。"""
        ltm_index = {}
        S = compute_S(
            curr_people=["D"],
            location="超市",
            ltm_index=ltm_index,
        )
        self.assertGreater(S, 0.5)

    def test_empty_people_uses_location_base(self):
        """無人在場時 S 應至少等於地點基礎值。"""
        S = compute_S(
            curr_people=[],
            location="廣場",
            ltm_index={},
        )
        # S_novelty=0.7 + S_base=0.06 → S 應 > 0.7
        self.assertGreater(S, LOCATION_BASE_S.get("廣場", 0.0))

    def test_s_capped_at_one(self):
        """S 值不應超過 1.0。"""
        S = compute_S(
            curr_people=["A","B","C"],
            location="咖啡店",
            ltm_index={},
            today_actions=["對話","工作","散步","休息","吃飯","整理"],
        )
        self.assertLessEqual(S, 1.0)

    def test_s_in_valid_range(self):
        """S 應在 [0.0, 1.0] 之間。"""
        S = compute_S(curr_people=[], location="A家")
        self.assertGreaterEqual(S, 0.0)
        self.assertLessEqual(S, 1.0)


class TestComputeC(unittest.TestCase):
    """測試加權困惑度計算 compute_C。"""

    def test_all_zeros(self):
        """U=K=S=0 時 C 應為 0.0。"""
        weights = {"w1": 0.4, "w2": 0.3, "w3": 0.3}
        C = compute_C(0.0, 0.0, 0.0, weights)
        self.assertAlmostEqual(C, 0.0, places=4)

    def test_all_ones_capped_at_one(self):
        """U=K=S=1 時 C 應被 clamp 到 1.0。"""
        weights = {"w1": 0.4, "w2": 0.3, "w3": 0.3}
        C = compute_C(1.0, 1.0, 1.0, weights)
        self.assertAlmostEqual(C, 1.0, places=4)

    def test_weighted_sum(self):
        """驗證加權公式 C = w1*U + w2*K + w3*S。"""
        weights = {"w1": 0.4, "w2": 0.3, "w3": 0.3}
        C = compute_C(0.5, 0.4, 0.2, weights)
        expected = 0.4 * 0.5 + 0.3 * 0.4 + 0.3 * 0.2
        self.assertAlmostEqual(C, expected, places=4)

    def test_default_weights(self):
        """不提供 weights 時應使用預設值。"""
        weights = {"w1": 0.4, "w2": 0.3, "w3": 0.3}
        C = compute_C(0.6, 0.3, 0.1, weights)
        self.assertGreaterEqual(C, 0.0)
        self.assertLessEqual(C, 1.0)


class TestDecideMode(unittest.TestCase):
    """測試模式決策 decide_mode。"""

    def test_high_k_forces_deliberate(self):
        """K >= DELIBERATE_K_OVERRIDE 時強制 deliberate。"""
        mode = decide_mode(C=0.1, threshold=0.9, K=DELIBERATE_K_OVERRIDE)
        self.assertEqual(mode, "deliberate")

    def test_k_above_override_forces_deliberate(self):
        """K 超過閾值即使 C 很低也應為 deliberate。"""
        mode = decide_mode(C=0.0, threshold=0.8, K=0.8)
        self.assertEqual(mode, "deliberate")

    def test_high_c_causes_deliberate(self):
        """C >= threshold 且 K 低時應為 deliberate。"""
        mode = decide_mode(C=0.8, threshold=0.5, K=0.0)
        self.assertEqual(mode, "deliberate")

    def test_low_c_causes_intuitive(self):
        """C < threshold 且 K 低時應為 intuitive。"""
        mode = decide_mode(C=0.2, threshold=0.5, K=0.0)
        self.assertEqual(mode, "intuitive")

    def test_c_equal_threshold_is_deliberate(self):
        """C == threshold 時應為 deliberate。"""
        mode = decide_mode(C=0.5, threshold=0.5, K=0.0)
        self.assertEqual(mode, "deliberate")


class TestEvaluate(unittest.TestCase):
    """測試主入口 evaluate 函式。"""

    def test_returns_all_keys(self):
        """evaluate 應回傳包含 U/K/S/C/mode 的 dict。"""
        result = evaluate()
        for key in ("U", "K", "S", "C", "mode"):
            self.assertIn(key, result)

    def test_values_in_range(self):
        """所有數值指標應在 [0, 1] 之間。"""
        result = evaluate(
            this_tick_event="Ben 突然走進來",
            current_action="收銀",
            delta_people={"arrived": ["B"], "departed": []},
            curr_people=["B"],
            location="超市",
            ltm_index={},
        )
        for key in ("U", "K", "S", "C"):
            self.assertGreaterEqual(result[key], 0.0, f"{key} 不應小於 0")
            self.assertLessEqual(result[key], 1.0, f"{key} 不應大於 1")

    def test_mode_is_valid(self):
        """mode 應為 intuitive 或 deliberate。"""
        result = evaluate()
        self.assertIn(result["mode"], {"intuitive", "deliberate"})


class TestAdjustThresholdByEmotion(unittest.TestCase):
    """測試情緒調整閾值。"""

    def test_calm_no_adjustment(self):
        """平靜情緒不調整閾值。"""
        self.assertAlmostEqual(
            adjust_threshold_by_emotion(0.5, "平靜"), 0.5, places=4
        )

    def test_sad_raises_threshold(self):
        """難過情緒應提高閾值（更難 deliberate）。"""
        result = adjust_threshold_by_emotion(0.5, "難過")
        self.assertGreater(result, 0.5)

    def test_anxious_raises_threshold(self):
        """不安情緒應提高閾值。"""
        result = adjust_threshold_by_emotion(0.5, "不安")
        self.assertGreater(result, 0.5)

    def test_threshold_capped_at_one(self):
        """調整後的閾值不應超過 1.0。"""
        result = adjust_threshold_by_emotion(0.95, "難過")
        self.assertLessEqual(result, 1.0)

    def test_unknown_emotion_no_adjustment(self):
        """未知情緒應不調整閾值。"""
        self.assertAlmostEqual(
            adjust_threshold_by_emotion(0.5, "未知情緒"), 0.5, places=4
        )

    def test_threshold_non_negative(self):
        """調整後的閾值應為非負。"""
        result = adjust_threshold_by_emotion(0.0, "難過")
        self.assertGreaterEqual(result, 0.0)


if __name__ == "__main__":
    unittest.main()
