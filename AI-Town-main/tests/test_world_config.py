# ================================================================
# tests/test_world_config.py
# config/world_config.py 模組的單元測試
# ================================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.world_config import (
    CHARACTER_NAMES,
    CHARACTER_CODES,
    DAY_START_HOUR,
    DAY_END_HOUR,
    MINUTES_PER_TICK,
    MAX_TICKS_PER_DAY,
    STM_SAFETY_LIMIT,
    STM_KEEP_AFTER_CONS,
    LTM_DECAY_RATE,
    LTM_FORGET_THRESHOLD,
    LTM_FALLBACK_COUNT,
    HAM_TRAVERSE_MAX_HOPS,
    HAM_ACTIVATION_DECAY,
    HAM_RETRIEVE_THRESHOLD,
    VALID_EMOTIONS,
    EMOTION_RESET_THRESHOLD,
    MARKOV_BASE_ALPHA,
    MARKOV_BASE_BETA,
    MARKOV_BASE_GAMMA,
    MARKOV_DELTA_ALPHA,
    MARKOV_DELTA_BETA,
    MARKOV_DELTA_GAMMA_LOC,
    MARKOV_DELTA_GAMMA_SCENE,
    MARKOV_RAW_GAMMA_MAX,
    MARKOV_LOOKBACK_N,
    MARKOV_SCENE_BASE_COUNT,
    MAJOR_EVENT_K_THRESHOLD,
    DIALOGUE_MAX_TURNS,
    DIALOGUE_BASE_ACCEPT,
    DIALOGUE_ACCEPT_MIN,
    DIALOGUE_ACCEPT_MAX,
    INTERRUPT_LOCK_LEVELS,
    SLEEP_ACTION,
    WAKE_ACTION,
    SIMULATION_DEFAULT_DAYS,
    SIMULATION_REPORT_PATTERN,
    LOG_LEVEL_CONSOLE,
    LOG_LEVEL_FILE,
    BASE_DIR,
    AI_DATA_DIR,
    LOG_DIR,
    REPORT_DIR,
)


class TestCharacterMappings(unittest.TestCase):
    """測試角色代號與名字的對應關係。"""

    def test_character_names_has_five_entries(self):
        """CHARACTER_NAMES 應包含恰好 5 個角色。"""
        self.assertEqual(len(CHARACTER_NAMES), 5)

    def test_character_names_values(self):
        """CHARACTER_NAMES 的值應包含 Amy、Ben、Claire、David、Emma。"""
        names = set(CHARACTER_NAMES.values())
        self.assertSetEqual(names, {"Amy", "Ben", "Claire", "David", "Emma"})

    def test_character_codes_is_inverse(self):
        """CHARACTER_CODES 應是 CHARACTER_NAMES 的完整反查表。"""
        self.assertEqual(CHARACTER_CODES["Amy"], "A")
        self.assertEqual(CHARACTER_CODES["Ben"], "B")
        self.assertEqual(CHARACTER_CODES["Claire"], "C")
        self.assertEqual(CHARACTER_CODES["David"], "D")
        self.assertEqual(CHARACTER_CODES["Emma"], "E")

    def test_character_codes_roundtrip(self):
        """每個代號經由 CHARACTER_NAMES 再經 CHARACTER_CODES 應回到原代號。"""
        for code, name in CHARACTER_NAMES.items():
            self.assertEqual(CHARACTER_CODES[name], code)


class TestTimeConfig(unittest.TestCase):
    """測試世界時間設定常數。"""

    def test_day_start_hour(self):
        """DAY_START_HOUR 應為 6。"""
        self.assertEqual(DAY_START_HOUR, 6)

    def test_day_end_hour(self):
        """DAY_END_HOUR 應為 2（凌晨 2 點）。"""
        self.assertEqual(DAY_END_HOUR, 2)

    def test_minutes_per_tick(self):
        """MINUTES_PER_TICK 應為 60。"""
        self.assertEqual(MINUTES_PER_TICK, 60)

    def test_max_ticks_per_day(self):
        """MAX_TICKS_PER_DAY 應為 20。"""
        self.assertEqual(MAX_TICKS_PER_DAY, 20)

    def test_ticks_cover_20_hours(self):
        """20 ticks × 60 分鐘 = 1200 分鐘 = 20 小時，與 06:00→02:00 吻合。"""
        total_minutes = MAX_TICKS_PER_DAY * MINUTES_PER_TICK
        self.assertEqual(total_minutes, 1200)


class TestMemoryConfig(unittest.TestCase):
    """測試記憶設定（STM / LTM）常數的合理性。"""

    def test_stm_safety_limit_positive(self):
        """STM_SAFETY_LIMIT 應大於 0。"""
        self.assertGreater(STM_SAFETY_LIMIT, 0)

    def test_stm_keep_less_than_safety_limit(self):
        """STM_KEEP_AFTER_CONS 應小於 STM_SAFETY_LIMIT。"""
        self.assertLess(STM_KEEP_AFTER_CONS, STM_SAFETY_LIMIT)

    def test_ltm_decay_rate_in_range(self):
        """LTM_DECAY_RATE 應在 0 到 1 之間。"""
        self.assertGreater(LTM_DECAY_RATE, 0)
        self.assertLess(LTM_DECAY_RATE, 1)

    def test_ltm_forget_threshold_in_range(self):
        """LTM_FORGET_THRESHOLD 應在 0 到 1 之間。"""
        self.assertGreater(LTM_FORGET_THRESHOLD, 0)
        self.assertLess(LTM_FORGET_THRESHOLD, 1)

    def test_ltm_fallback_count_positive(self):
        """LTM_FALLBACK_COUNT 應大於 0。"""
        self.assertGreater(LTM_FALLBACK_COUNT, 0)


class TestHamConfig(unittest.TestCase):
    """測試 HAM 圖譜擴散激活設定。"""

    def test_ham_traverse_max_hops(self):
        """HAM_TRAVERSE_MAX_HOPS 應為 2。"""
        self.assertEqual(HAM_TRAVERSE_MAX_HOPS, 2)

    def test_ham_activation_decay_in_range(self):
        """HAM_ACTIVATION_DECAY 應在 0 到 1 之間。"""
        self.assertGreater(HAM_ACTIVATION_DECAY, 0)
        self.assertLess(HAM_ACTIVATION_DECAY, 1)

    def test_ham_retrieve_threshold_in_range(self):
        """HAM_RETRIEVE_THRESHOLD 應在 0 到 1 之間。"""
        self.assertGreater(HAM_RETRIEVE_THRESHOLD, 0)
        self.assertLess(HAM_RETRIEVE_THRESHOLD, 1)


class TestEmotionConfig(unittest.TestCase):
    """測試情緒相關常數。"""

    def test_valid_emotions_has_eight(self):
        """VALID_EMOTIONS 應包含恰好 8 種情緒。"""
        self.assertEqual(len(VALID_EMOTIONS), 8)

    def test_valid_emotions_contains_calm(self):
        """VALID_EMOTIONS 應包含「平靜」作為預設情緒。"""
        self.assertIn("平靜", VALID_EMOTIONS)

    def test_emotion_reset_threshold_in_range(self):
        """EMOTION_RESET_THRESHOLD 應在 0 到 1 之間。"""
        self.assertGreater(EMOTION_RESET_THRESHOLD, 0)
        self.assertLess(EMOTION_RESET_THRESHOLD, 1)

    def test_valid_emotions_contains_expected(self):
        """VALID_EMOTIONS 應含開心、緊張、難過、疲憊等常見情緒。"""
        for e in ["開心", "緊張", "難過", "疲憊"]:
            self.assertIn(e, VALID_EMOTIONS)


class TestMarkovWeights(unittest.TestCase):
    """測試動態 Markov 三來源加權設定。"""

    def test_base_weights_all_positive(self):
        """三個來源的底線值應均大於 0。"""
        self.assertGreater(MARKOV_BASE_ALPHA, 0)
        self.assertGreater(MARKOV_BASE_BETA, 0)
        self.assertGreater(MARKOV_BASE_GAMMA, 0)

    def test_delta_weights_all_positive(self):
        """三個來源的動態加分上限應均大於 0。"""
        self.assertGreater(MARKOV_DELTA_ALPHA, 0)
        self.assertGreater(MARKOV_DELTA_BETA, 0)
        self.assertGreater(MARKOV_DELTA_GAMMA_LOC, 0)
        self.assertGreater(MARKOV_DELTA_GAMMA_SCENE, 0)

    def test_raw_gamma_max_clamp_reasonable(self):
        """MARKOV_RAW_GAMMA_MAX 應介於 0 與 1 之間，且不超過 BASE+DELTA_LOC+DELTA_SCENE。"""
        self.assertGreater(MARKOV_RAW_GAMMA_MAX, 0)
        self.assertLess(MARKOV_RAW_GAMMA_MAX, 1.0)
        max_possible = MARKOV_BASE_GAMMA + MARKOV_DELTA_GAMMA_LOC + MARKOV_DELTA_GAMMA_SCENE
        self.assertLessEqual(MARKOV_RAW_GAMMA_MAX, max_possible + 0.01)

    def test_base_plus_max_delta_less_than_one_before_normalization(self):
        """底線總和應小於 1.0（正規化前的 raw 值在合理範圍）。"""
        base_sum = MARKOV_BASE_ALPHA + MARKOV_BASE_BETA + MARKOV_BASE_GAMMA
        self.assertGreater(base_sum, 0)
        self.assertLess(base_sum, 1.5)

    def test_lookback_n_positive(self):
        """MARKOV_LOOKBACK_N 應大於 0。"""
        self.assertGreater(MARKOV_LOOKBACK_N, 0)

    def test_scene_base_count_positive(self):
        """MARKOV_SCENE_BASE_COUNT 應大於 0。"""
        self.assertGreater(MARKOV_SCENE_BASE_COUNT, 0)

    def test_major_event_k_threshold_in_range(self):
        """MAJOR_EVENT_K_THRESHOLD 應在 0 到 1 之間。"""
        self.assertGreater(MAJOR_EVENT_K_THRESHOLD, 0)
        self.assertLess(MAJOR_EVENT_K_THRESHOLD, 1)


class TestDialogueConfig(unittest.TestCase):
    """測試對話設定常數。"""

    def test_dialogue_max_turns_positive(self):
        """DIALOGUE_MAX_TURNS 應大於 0。"""
        self.assertGreater(DIALOGUE_MAX_TURNS, 0)

    def test_dialogue_accept_min_less_than_max(self):
        """DIALOGUE_ACCEPT_MIN 應小於 DIALOGUE_ACCEPT_MAX。"""
        self.assertLess(DIALOGUE_ACCEPT_MIN, DIALOGUE_ACCEPT_MAX)

    def test_dialogue_accept_bounds_in_range(self):
        """DIALOGUE_ACCEPT_MIN/MAX 應在 0 到 1 之間。"""
        self.assertGreaterEqual(DIALOGUE_ACCEPT_MIN, 0)
        self.assertLessEqual(DIALOGUE_ACCEPT_MAX, 1)

    def test_dialogue_base_accept_in_range(self):
        """DIALOGUE_BASE_ACCEPT 應在 ACCEPT_MIN 到 ACCEPT_MAX 之間。"""
        self.assertGreaterEqual(DIALOGUE_BASE_ACCEPT, DIALOGUE_ACCEPT_MIN)
        self.assertLessEqual(DIALOGUE_BASE_ACCEPT, DIALOGUE_ACCEPT_MAX)


class TestInterruptLockLevels(unittest.TestCase):
    """測試中斷鎖等級字典。"""

    def test_sleep_lock_level_two(self):
        """「睡覺」的鎖等級應為 2（不可中斷）。"""
        self.assertEqual(INTERRUPT_LOCK_LEVELS["睡覺"], 2)

    def test_dialogue_lock_level_two(self):
        """「對話」的鎖等級應為 2（不可中斷）。"""
        self.assertEqual(INTERRUPT_LOCK_LEVELS["對話"], 2)

    def test_work_actions_lock_level_one(self):
        """工作類行動（賣咖啡、煮飯、收銀）的鎖等級應為 1。"""
        for action in ["賣咖啡", "煮飯", "收銀"]:
            self.assertEqual(INTERRUPT_LOCK_LEVELS[action], 1,
                             f"{action} 的鎖等級應為 1")

    def test_movement_actions_lock_level_zero(self):
        """移動類行動（前往、回家、散步）的鎖等級應為 0。"""
        for action in ["前往", "回家", "散步"]:
            self.assertEqual(INTERRUPT_LOCK_LEVELS[action], 0,
                             f"{action} 的鎖等級應為 0")

    def test_all_lock_levels_valid(self):
        """所有鎖等級值應在 0、1、2 之中。"""
        valid_levels = {0, 1, 2}
        for action, level in INTERRUPT_LOCK_LEVELS.items():
            self.assertIn(level, valid_levels,
                         f"{action} 的鎖等級 {level} 不在有效範圍內")


class TestSpecialActions(unittest.TestCase):
    """測試特殊行動字串常數。"""

    def test_sleep_action_string(self):
        """SLEEP_ACTION 應為「睡覺」。"""
        self.assertEqual(SLEEP_ACTION, "睡覺")

    def test_wake_action_string(self):
        """WAKE_ACTION 應為「起床」。"""
        self.assertEqual(WAKE_ACTION, "起床")


class TestSimulationDefaults(unittest.TestCase):
    """測試模擬預設值常數。"""

    def test_simulation_default_days_positive(self):
        """SIMULATION_DEFAULT_DAYS 應大於 0。"""
        self.assertGreater(SIMULATION_DEFAULT_DAYS, 0)

    def test_simulation_report_pattern_contains_timestamp(self):
        """SIMULATION_REPORT_PATTERN 應包含 {timestamp} 佔位符。"""
        self.assertIn("{timestamp}", SIMULATION_REPORT_PATTERN)


class TestLogConfig(unittest.TestCase):
    """測試日誌級別常數。"""

    def test_log_level_console_valid(self):
        """LOG_LEVEL_CONSOLE 應為有效的日誌級別字串。"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        self.assertIn(LOG_LEVEL_CONSOLE, valid_levels)

    def test_log_level_file_valid(self):
        """LOG_LEVEL_FILE 應為有效的日誌級別字串。"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        self.assertIn(LOG_LEVEL_FILE, valid_levels)


class TestPathConfig(unittest.TestCase):
    """測試路徑常數的結構正確性。"""

    def test_ai_data_dir_under_base(self):
        """AI_DATA_DIR 應位於 BASE_DIR 之下。"""
        self.assertTrue(AI_DATA_DIR.startswith(BASE_DIR))

    def test_log_dir_under_base(self):
        """LOG_DIR 應位於 BASE_DIR 之下。"""
        self.assertTrue(LOG_DIR.startswith(BASE_DIR))

    def test_report_dir_under_base(self):
        """REPORT_DIR 應位於 BASE_DIR 之下。"""
        self.assertTrue(REPORT_DIR.startswith(BASE_DIR))

    def test_base_dir_is_absolute(self):
        """BASE_DIR 應為絕對路徑。"""
        self.assertTrue(os.path.isabs(BASE_DIR))


if __name__ == "__main__":
    unittest.main(verbosity=2)
