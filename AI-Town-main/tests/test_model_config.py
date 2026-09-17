# ================================================================
# tests/test_model_config.py
# config/model_config.py 模組的單元測試
# ================================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.model_config import (
    MODEL_ID,
    MODEL_NUM_CROPS,
    MODEL_CACHE_DIR,
    DELIBERATE_MAX_TOKENS,
    DELIBERATE_TEMPERATURE,
    DIALOGUE_MAX_TOKENS,
    DIALOGUE_TEMPERATURE,
    CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS,
    CONSOLIDATE_SELECT_MAX_TOKENS,
    CONSOLIDATE_SUMMARY_MAX_TOKENS,
    CONSOLIDATE_RELATION_MAX_TOKENS,
    CONSOLIDATE_EMOTION_MAX_TOKENS,
    SCHEDULE_GEN_MAX_TOKENS,
    STM_TOKEN_BUDGET,
    LTM_TOKEN_BUDGET,
    BATCH_SIZE_MAX_HIGH_VRAM,
    BATCH_SIZE_MAX_MID_VRAM,
    BATCH_SIZE_MAX_LOW_VRAM,
    VRAM_THRESHOLD_HIGH,
    VRAM_THRESHOLD_MID,
)


class TestModelLoadConfig(unittest.TestCase):
    """測試模型載入設定常數。"""

    def test_model_id_is_string(self):
        """MODEL_ID 應為非空字串。"""
        self.assertIsInstance(MODEL_ID, str)
        self.assertGreater(len(MODEL_ID), 0)

    def test_model_id_contains_gemma(self):
        """MODEL_ID 應包含 'gemma'（使用 Gemma 4 模型）。"""
        self.assertIn("gemma", MODEL_ID.lower())

    def test_model_num_crops_positive(self):
        """MODEL_NUM_CROPS 應大於 0。"""
        self.assertGreater(MODEL_NUM_CROPS, 0)

    def test_model_cache_dir_default_none(self):
        """MODEL_CACHE_DIR 預設應為 None（使用 HuggingFace 預設快取）。"""
        self.assertIsNone(MODEL_CACHE_DIR)


class TestDeliberateConfig(unittest.TestCase):
    """測試深思路徑推論參數。"""

    def test_deliberate_max_tokens_positive(self):
        """DELIBERATE_MAX_TOKENS 應大於 0。"""
        self.assertGreater(DELIBERATE_MAX_TOKENS, 0)

    def test_deliberate_temperature_zero(self):
        """DELIBERATE_TEMPERATURE 應為 0.0（確定性輸出）。"""
        self.assertEqual(DELIBERATE_TEMPERATURE, 0.0)

    def test_deliberate_max_tokens_reasonable(self):
        """DELIBERATE_MAX_TOKENS 應在 100 到 2000 之間（合理預算）。"""
        self.assertGreaterEqual(DELIBERATE_MAX_TOKENS, 100)
        self.assertLessEqual(DELIBERATE_MAX_TOKENS, 2000)


class TestDialogueConfig(unittest.TestCase):
    """測試對話生成推論參數。"""

    def test_dialogue_max_tokens_positive(self):
        """DIALOGUE_MAX_TOKENS 應大於 0。"""
        self.assertGreater(DIALOGUE_MAX_TOKENS, 0)

    def test_dialogue_temperature_in_range(self):
        """DIALOGUE_TEMPERATURE 應在 0.0 到 1.0 之間。"""
        self.assertGreaterEqual(DIALOGUE_TEMPERATURE, 0.0)
        self.assertLessEqual(DIALOGUE_TEMPERATURE, 1.0)

    def test_dialogue_temperature_greater_than_deliberate(self):
        """DIALOGUE_TEMPERATURE 應大於 DELIBERATE_TEMPERATURE（對話需要更多多樣性）。"""
        self.assertGreater(DIALOGUE_TEMPERATURE, DELIBERATE_TEMPERATURE)

    def test_dialogue_max_tokens_less_than_deliberate(self):
        """DIALOGUE_MAX_TOKENS 應小於 DELIBERATE_MAX_TOKENS（對話回應較短）。"""
        self.assertLess(DIALOGUE_MAX_TOKENS, DELIBERATE_MAX_TOKENS)


class TestConsolidateConfig(unittest.TestCase):
    """測試睡眠濃縮各步驟的 token 上限。"""

    def test_all_consolidate_tokens_positive(self):
        """所有濃縮步驟的 token 上限應大於 0。"""
        tokens = [
            CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS,
            CONSOLIDATE_SELECT_MAX_TOKENS,
            CONSOLIDATE_SUMMARY_MAX_TOKENS,
            CONSOLIDATE_RELATION_MAX_TOKENS,
            CONSOLIDATE_EMOTION_MAX_TOKENS,
            SCHEDULE_GEN_MAX_TOKENS,
        ]
        for t in tokens:
            self.assertGreater(t, 0, f"token 上限 {t} 應大於 0")

    def test_emotion_token_smallest(self):
        """CONSOLIDATE_EMOTION_MAX_TOKENS 應最小（只需回傳一個詞）。"""
        self.assertLessEqual(CONSOLIDATE_EMOTION_MAX_TOKENS,
                             CONSOLIDATE_SUMMARY_MAX_TOKENS)
        self.assertLessEqual(CONSOLIDATE_EMOTION_MAX_TOKENS,
                             CONSOLIDATE_RELATION_MAX_TOKENS)

    def test_ham_extract_larger_than_select(self):
        """HAM 抽取的 token 上限應不小於篩選步驟（抽取任務更複雜）。"""
        self.assertGreaterEqual(CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS,
                                CONSOLIDATE_SELECT_MAX_TOKENS)

    def test_schedule_gen_tokens_sufficient(self):
        """SCHEDULE_GEN_MAX_TOKENS 應 >= 200（JSON 時間表需要足夠長度）。"""
        self.assertGreaterEqual(SCHEDULE_GEN_MAX_TOKENS, 200)


class TestPromptBudgetConfig(unittest.TestCase):
    """測試 Prompt 注入預算設定。"""

    def test_stm_token_budget_positive(self):
        """STM_TOKEN_BUDGET 應大於 0。"""
        self.assertGreater(STM_TOKEN_BUDGET, 0)

    def test_ltm_token_budget_positive(self):
        """LTM_TOKEN_BUDGET 應大於 0。"""
        self.assertGreater(LTM_TOKEN_BUDGET, 0)

    def test_stm_budget_larger_than_ltm(self):
        """STM_TOKEN_BUDGET 應大於 LTM_TOKEN_BUDGET（STM 敘述文字較長）。"""
        self.assertGreater(STM_TOKEN_BUDGET, LTM_TOKEN_BUDGET)


class TestBatchConfig(unittest.TestCase):
    """測試 Batch 推論設定常數。"""

    def test_batch_sizes_are_positive(self):
        """所有 BATCH_SIZE 常數應大於 0。"""
        for size in [BATCH_SIZE_MAX_HIGH_VRAM, BATCH_SIZE_MAX_MID_VRAM, BATCH_SIZE_MAX_LOW_VRAM]:
            self.assertGreater(size, 0)

    def test_batch_size_order(self):
        """高顯存的 batch size 應 >= 中顯存 >= 低顯存。"""
        self.assertGreaterEqual(BATCH_SIZE_MAX_HIGH_VRAM, BATCH_SIZE_MAX_MID_VRAM)
        self.assertGreaterEqual(BATCH_SIZE_MAX_MID_VRAM, BATCH_SIZE_MAX_LOW_VRAM)

    def test_low_vram_batch_size_is_one(self):
        """BATCH_SIZE_MAX_LOW_VRAM 應為 1（低顯存只能一次一個）。"""
        self.assertEqual(BATCH_SIZE_MAX_LOW_VRAM, 1)

    def test_vram_threshold_order(self):
        """高顯存閾值應大於中顯存閾值。"""
        self.assertGreater(VRAM_THRESHOLD_HIGH, VRAM_THRESHOLD_MID)

    def test_vram_thresholds_in_mb(self):
        """VRAM 閾值應以 MB 為單位（高閾值 >= 12 GB = 12288 MB）。"""
        self.assertGreaterEqual(VRAM_THRESHOLD_MID, 12 * 1024)
        self.assertGreaterEqual(VRAM_THRESHOLD_HIGH, 16 * 1024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
