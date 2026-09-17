# ================================================================
# tests/test_tick_value.py
# tick_value (ActionValueTracker) 單元測試
#
# 涵蓋：decay、update、compute_reward、get_scores、reset、top_values
# ================================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.tick_value import (
    ActionValueTracker,
    VALUE_DECAY,
    REWARD_EMOTION_IMPROVE,
    REWARD_EMOTION_NEUTRAL,
    REWARD_EMOTION_WORSEN,
    REWARD_CONFUSION_DROP,
    REWARD_CONFUSION_SPIKE,
    REWARD_DIALOGUE_ACCEPT,
    REWARD_SCHEDULE_HIT,
    CONFUSION_DROP_THRESHOLD,
    CONFUSION_SPIKE_THRESHOLD,
    POSITIVE_EMOTIONS,
    NEUTRAL_EMOTIONS,
    NEGATIVE_EMOTIONS,
)


class TestActionValueTrackerInit(unittest.TestCase):
    """測試初始化狀態。"""

    def test_initial_values_empty(self):
        """初始化後 values 應為空 dict。"""
        tracker = ActionValueTracker()
        self.assertEqual(tracker.values, {})

    def test_initial_history_empty(self):
        """初始化後 history 應為空列表。"""
        tracker = ActionValueTracker()
        self.assertEqual(tracker.history, [])

    def test_get_scores_returns_empty_dict(self):
        """初始化後 get_scores 應回傳空 dict。"""
        tracker = ActionValueTracker()
        self.assertEqual(tracker.get_scores(), {})


class TestDecay(unittest.TestCase):
    """測試衰減機制。"""

    def test_decay_multiplies_by_decay_factor(self):
        """decay 應將所有 value 乘以 VALUE_DECAY。"""
        tracker = ActionValueTracker()
        tracker.values = {"工作": 1.0, "休息": 0.5}
        tracker.decay()
        self.assertAlmostEqual(tracker.values["工作"], VALUE_DECAY, places=6)
        self.assertAlmostEqual(tracker.values["休息"], 0.5 * VALUE_DECAY, places=6)

    def test_decay_on_empty_values_no_error(self):
        """空 values 執行 decay 不應拋出例外。"""
        tracker = ActionValueTracker()
        try:
            tracker.decay()
        except Exception as e:
            self.fail(f"decay 拋出例外：{e}")

    def test_multiple_decays_reduce_value(self):
        """多次 decay 後 value 應持續減小。"""
        tracker = ActionValueTracker()
        tracker.values = {"對話": 1.0}
        for _ in range(5):
            tracker.decay()
        self.assertLess(tracker.values["對話"], 1.0)
        self.assertAlmostEqual(tracker.values["對話"], VALUE_DECAY ** 5, places=6)


class TestUpdate(unittest.TestCase):
    """測試 update 方法。"""

    def test_update_new_action(self):
        """更新新行動時應正確設定 value。"""
        tracker = ActionValueTracker()
        tracker.update("賣咖啡", 0.3)
        self.assertAlmostEqual(tracker.values["賣咖啡"], 0.3, places=6)

    def test_update_accumulates(self):
        """多次 update 同一行動應累積 value。"""
        tracker = ActionValueTracker()
        tracker.update("散步", 0.2)
        tracker.update("散步", 0.1)
        self.assertAlmostEqual(tracker.values["散步"], 0.3, places=6)

    def test_negative_reward_decreases_value(self):
        """負 reward 應降低 value。"""
        tracker = ActionValueTracker()
        tracker.update("工作", 0.5)
        tracker.update("工作", -0.8)
        self.assertAlmostEqual(tracker.values["工作"], -0.3, places=6)

    def test_get_scores_reflects_updates(self):
        """get_scores 應回傳 update 後的最新狀態。"""
        tracker = ActionValueTracker()
        tracker.update("收銀", 0.4)
        scores = tracker.get_scores()
        self.assertIn("收銀", scores)
        self.assertAlmostEqual(scores["收銀"], 0.4, places=6)

    def test_get_scores_returns_copy(self):
        """get_scores 應回傳副本，不影響原始 values。"""
        tracker = ActionValueTracker()
        tracker.update("補貨", 0.3)
        scores = tracker.get_scores()
        scores["補貨"] = 999.0
        self.assertNotEqual(tracker.values["補貨"], 999.0)


class TestReset(unittest.TestCase):
    """測試 reset 方法。"""

    def test_reset_clears_values(self):
        """reset 後 values 應為空。"""
        tracker = ActionValueTracker()
        tracker.update("吃飯", 0.5)
        tracker.reset()
        self.assertEqual(tracker.values, {})

    def test_reset_clears_history(self):
        """reset 後 history 應為空。"""
        tracker = ActionValueTracker()
        tracker.compute_reward("工作", "平靜", "開心", 0.5, 0.3)
        tracker.reset()
        self.assertEqual(tracker.history, [])


class TestEmotionReward(unittest.TestCase):
    """測試情緒相關 reward 計算。"""

    def setUp(self):
        self.tracker = ActionValueTracker()

    def test_negative_to_positive_emotion_gives_improve_reward(self):
        """從負面到正面情緒應獲得 IMPROVE reward。"""
        for neg in NEGATIVE_EMOTIONS:
            for pos in POSITIVE_EMOTIONS:
                with self.subTest(neg=neg, pos=pos):
                    r = self.tracker._emotion_reward(neg, pos)
                    self.assertAlmostEqual(r, REWARD_EMOTION_IMPROVE, places=6)

    def test_negative_to_neutral_gives_neutral_reward(self):
        """從負面到中性情緒應獲得 NEUTRAL reward。"""
        for neg in NEGATIVE_EMOTIONS:
            r = self.tracker._emotion_reward(neg, "平靜")
            self.assertAlmostEqual(r, REWARD_EMOTION_NEUTRAL, places=6)

    def test_positive_to_negative_gives_worsen_reward(self):
        """從正面到負面情緒應獲得 WORSEN reward（負值）。"""
        for pos in POSITIVE_EMOTIONS:
            for neg in NEGATIVE_EMOTIONS:
                with self.subTest(pos=pos, neg=neg):
                    r = self.tracker._emotion_reward(pos, neg)
                    self.assertAlmostEqual(r, REWARD_EMOTION_WORSEN, places=6)

    def test_no_change_returns_zero(self):
        """同一情緒前後不變應回傳 0.0。"""
        r = self.tracker._emotion_reward("平靜", "平靜")
        self.assertAlmostEqual(r, 0.0, places=6)

    def test_neutral_to_neutral_returns_zero(self):
        """中性到中性應回傳 0.0。"""
        r = self.tracker._emotion_reward("平靜", "平靜")
        self.assertEqual(r, 0.0)

    def test_valid_character_emotions_mapped(self):
        """全域設定中的負面情緒（如 緊張, 難過, 疲憊）應被正確視為負面情緒並觸發 Reward。"""
        # 如果前一情緒為「緊張」（config.world_config 中合法的負面情緒），後一情緒為「平靜」
        r = self.tracker._emotion_reward("緊張", "平靜")
        self.assertAlmostEqual(r, REWARD_EMOTION_NEUTRAL, places=6)

        # 如果前一情緒為「平靜」，後一情緒為「難過」
        r = self.tracker._emotion_reward("平靜", "難過")
        self.assertAlmostEqual(r, REWARD_EMOTION_WORSEN, places=6)



class TestConfusionReward(unittest.TestCase):
    """測試困惑度相關 reward 計算。"""

    def setUp(self):
        self.tracker = ActionValueTracker()

    def test_large_drop_gives_positive_reward(self):
        """C 值明顯下降應獲得正向 reward。"""
        r = self.tracker._confusion_reward(0.8, 0.5)
        self.assertGreater(r, 0.0)
        self.assertLessEqual(r, REWARD_CONFUSION_DROP)

    def test_large_spike_gives_negative_reward(self):
        """C 值明顯上升應獲得負向 reward。"""
        r = self.tracker._confusion_reward(0.3, 0.6)
        self.assertLess(r, 0.0)
        self.assertGreaterEqual(r, REWARD_CONFUSION_SPIKE)

    def test_small_change_returns_zero(self):
        """C 值微小變動應回傳 0.0。"""
        r = self.tracker._confusion_reward(0.5, 0.49)
        self.assertEqual(r, 0.0)

    def test_no_change_returns_zero(self):
        """C 值不變應回傳 0.0。"""
        r = self.tracker._confusion_reward(0.5, 0.5)
        self.assertEqual(r, 0.0)


class TestComputeReward(unittest.TestCase):
    """測試 compute_reward 整合計算。"""

    def setUp(self):
        self.tracker = ActionValueTracker()

    def test_basic_reward_computation(self):
        """基本 reward 計算應回傳浮點數。"""
        reward = self.tracker.compute_reward(
            action="工作",
            prev_emotion="平靜",
            curr_emotion="開心",
            prev_C=0.5,
            curr_C=0.3,
        )
        self.assertIsInstance(reward, float)

    def test_dialogue_accepted_adds_reward(self):
        """對話被接受時 reward 應增加 DIALOGUE_ACCEPT。"""
        base = self.tracker.compute_reward(
            action="對話",
            prev_emotion="平靜",
            curr_emotion="平靜",
            prev_C=0.4,
            curr_C=0.4,
        )
        self.tracker.reset()
        with_accept = self.tracker.compute_reward(
            action="對話",
            prev_emotion="平靜",
            curr_emotion="平靜",
            prev_C=0.4,
            curr_C=0.4,
            dialogue_accepted=True,
        )
        self.assertAlmostEqual(with_accept - base, REWARD_DIALOGUE_ACCEPT, places=6)

    def test_schedule_hit_adds_reward(self):
        """符合時間表應增加 SCHEDULE_HIT reward。"""
        base = self.tracker.compute_reward(
            action="賣咖啡",
            prev_emotion="平靜",
            curr_emotion="平靜",
            prev_C=0.4,
            curr_C=0.4,
        )
        self.tracker.reset()
        with_hit = self.tracker.compute_reward(
            action="賣咖啡",
            prev_emotion="平靜",
            curr_emotion="平靜",
            prev_C=0.4,
            curr_C=0.4,
            schedule_hit=True,
        )
        self.assertAlmostEqual(with_hit - base, REWARD_SCHEDULE_HIT, places=6)

    def test_dialogue_accepted_only_for_dialogue_action(self):
        """dialogue_accepted=True 但行動非「對話」時不應加 DIALOGUE_ACCEPT reward。"""
        base = self.tracker.compute_reward(
            action="工作",
            prev_emotion="平靜",
            curr_emotion="平靜",
            prev_C=0.4,
            curr_C=0.4,
        )
        self.tracker.reset()
        no_bonus = self.tracker.compute_reward(
            action="工作",
            prev_emotion="平靜",
            curr_emotion="平靜",
            prev_C=0.4,
            curr_C=0.4,
            dialogue_accepted=True,  # 行動非對話，不應加分
        )
        self.assertAlmostEqual(no_bonus, base, places=6)

    def test_history_recorded(self):
        """compute_reward 應記錄到 history。"""
        self.tracker.compute_reward(
            action="散步",
            prev_emotion="緊張",
            curr_emotion="平靜",
            prev_C=0.6,
            curr_C=0.3,
            tick_id="tick_001",
        )
        self.assertEqual(len(self.tracker.history), 1)
        record = self.tracker.history[0]
        self.assertEqual(record["action"], "散步")
        self.assertEqual(record["tick_id"], "tick_001")

    def test_full_positive_scenario(self):
        """Emma 烹飪後情緒改善、困惑度下降且符合時間表時應有正向 reward。"""
        reward = self.tracker.compute_reward(
            action="煮飯",
            prev_emotion="不安",
            curr_emotion="開心",
            prev_C=0.7,
            curr_C=0.3,
            schedule_hit=True,
        )
        self.assertGreater(reward, 0.0)


class TestTopValues(unittest.TestCase):
    """測試 top_values 排序功能。"""

    def test_top_values_sorted_descending(self):
        """top_values 應回傳從高到低排序的行動。"""
        tracker = ActionValueTracker()
        tracker.values = {"工作": 0.8, "休息": 0.2, "散步": 0.5, "對話": 0.9}
        top = tracker.top_values(3)
        values = [v for _, v in top]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_top_values_respects_n(self):
        """top_values 應回傳指定的前 N 個行動。"""
        tracker = ActionValueTracker()
        tracker.values = {"工作": 0.5, "休息": 0.3, "散步": 0.1}
        top = tracker.top_values(2)
        self.assertEqual(len(top), 2)

    def test_top_values_empty(self):
        """無 values 時 top_values 應回傳空列表。"""
        tracker = ActionValueTracker()
        top = tracker.top_values()
        self.assertEqual(top, [])


class TestSummaryStr(unittest.TestCase):
    """測試 summary_str 輸出格式。"""

    def test_empty_tracker_returns_empty_string(self):
        """無 values 時應回傳 (empty)。"""
        tracker = ActionValueTracker()
        self.assertEqual(tracker.summary_str(), "(empty)")

    def test_with_values_returns_non_empty(self):
        """有 values 時應回傳非空字串。"""
        tracker = ActionValueTracker()
        tracker.values = {"工作": 0.5, "休息": 0.3}
        result = tracker.summary_str()
        self.assertNotEqual(result, "(empty)")
        self.assertIn("|", result)


class TestRLIntegration(unittest.TestCase):
    """整合測試：模擬 Amy 的一天中 RL 更新流程。"""

    def test_amy_positive_day_increases_coffee_value(self):
        """Amy 賣咖啡後情緒改善，其 value score 應增加。"""
        tracker = ActionValueTracker()

        # 模擬每個 tick 的 decay + update 流程
        for i in range(3):
            tracker.decay()
            reward = tracker.compute_reward(
                action="賣咖啡",
                prev_emotion="平靜",
                curr_emotion="開心",
                prev_C=0.5,
                curr_C=0.2,
                schedule_hit=True,
                tick_id=f"tick_{i}",
            )
            tracker.update("賣咖啡", reward)

        scores = tracker.get_scores()
        self.assertIn("賣咖啡", scores)
        self.assertGreater(scores["賣咖啡"], 0.0)

    def test_decay_then_update_flow(self):
        """標準 decay-then-update 流程應正確執行。"""
        tracker = ActionValueTracker()

        # tick 1
        tracker.decay()
        r1 = tracker.compute_reward("工作", "不安", "平靜", 0.7, 0.4)
        tracker.update("工作", r1)

        # tick 2
        tracker.decay()
        r2 = tracker.compute_reward("工作", "平靜", "開心", 0.4, 0.2)
        tracker.update("工作", r2)

        scores = tracker.get_scores()
        self.assertIn("工作", scores)


if __name__ == "__main__":
    unittest.main()
