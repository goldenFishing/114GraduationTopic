# ================================================================
# tests/test_core_merge.py
# 驗證 core 目錄整合正確性
#
# 情境 1：mental_state 可以 import confusion 功能
# 情境 2：mental_state 可以 import emotion 功能
# 情境 3：舊模組不存在（core.emotion / core.confusion）
# 情境 4：agent.scheduler 不存在
# 情境 5：consolidation 可以正常 import
# 情境 6：agent.agent 可以正常 import
# ================================================================

import importlib
import sys
import unittest


class TestMentalStateConfusionFunctions(unittest.TestCase):
    """情境 1：mental_state 可以 import confusion 功能"""

    def test_import_confusion_functions(self):
        """不拋出 ImportError"""
        try:
            from core.mental_state import evaluate, adjust_threshold_by_emotion, compute_U
        except ImportError as e:
            self.fail(f"ImportError: {e}")

    def test_evaluate_returns_dict_with_mode(self):
        """evaluate() 可以正常呼叫並回傳含 'mode' 的 dict"""
        from core.mental_state import evaluate
        result = evaluate()
        self.assertIsInstance(result, dict)
        self.assertIn("mode", result)
        self.assertIn(result["mode"], ("intuitive", "deliberate"))

    def test_evaluate_has_all_keys(self):
        """evaluate() 回傳包含 U, K, S, C, mode"""
        from core.mental_state import evaluate
        result = evaluate()
        for key in ("U", "K", "S", "C", "mode"):
            self.assertIn(key, result)


class TestMentalStateEmotionFunctions(unittest.TestCase):
    """情境 2：mental_state 可以 import emotion 功能"""

    def test_import_emotion_functions(self):
        """不拋出 ImportError"""
        try:
            from core.mental_state import should_update_emotion, normalize_emotion
        except ImportError as e:
            self.fail(f"ImportError: {e}")

    def test_normalize_emotion_valid(self):
        """normalize_emotion('開心') == '開心'"""
        from core.mental_state import normalize_emotion
        self.assertEqual(normalize_emotion("開心"), "開心")

    def test_normalize_emotion_invalid(self):
        """normalize_emotion('無效') == '平靜'"""
        from core.mental_state import normalize_emotion
        self.assertEqual(normalize_emotion("無效"), "平靜")

    def test_normalize_emotion_empty(self):
        """normalize_emotion('') == '平靜'"""
        from core.mental_state import normalize_emotion
        self.assertEqual(normalize_emotion(""), "平靜")


class TestOldModulesRemoved(unittest.TestCase):
    """情境 3：舊模組不存在"""

    def test_core_emotion_removed(self):
        """import core.emotion 應拋出 ModuleNotFoundError"""
        # 確保快取不影響測試
        sys.modules.pop("core.emotion", None)
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("core.emotion")

    def test_core_confusion_removed(self):
        """import core.confusion 應拋出 ModuleNotFoundError"""
        sys.modules.pop("core.confusion", None)
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("core.confusion")


class TestSchedulerRemoved(unittest.TestCase):
    """情境 4：agent.scheduler 不存在"""

    def test_agent_scheduler_removed(self):
        """import agent.scheduler 應拋出 ModuleNotFoundError"""
        sys.modules.pop("agent.scheduler", None)
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("agent.scheduler")


class TestConsolidationImport(unittest.TestCase):
    """情境 5：consolidation 可以正常 import"""

    def test_import_consolidation(self):
        """不拋出 ImportError"""
        try:
            import core.consolidation
        except ImportError as e:
            self.fail(f"ImportError: {e}")

    def test_generate_next_day_schedule_in_consolidation(self):
        """generate_next_day_schedule 已存在於 consolidation 模組"""
        import core.consolidation
        self.assertTrue(
            hasattr(core.consolidation, "generate_next_day_schedule"),
            "generate_next_day_schedule 未找到於 core.consolidation",
        )


class TestAgentImport(unittest.TestCase):
    """情境 6：agent.agent 可以正常 import（驗證 eval_confusion 路徑更新正確）"""

    def test_import_agent(self):
        """不拋出 ImportError"""
        try:
            import agent.agent
        except ImportError as e:
            self.fail(f"ImportError: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
