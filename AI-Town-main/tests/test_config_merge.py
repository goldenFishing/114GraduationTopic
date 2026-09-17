# ================================================================
# tests/test_config_merge.py
# 驗證 config/triggers.py 已正確合併進 config/action_list.py
# ================================================================

import unittest


class TestConfigMerge(unittest.TestCase):
    """驗證 config.triggers 內容已合併至 config.action_list。"""

    # ── 情境 1：ACTION_KEYWORD_BOOST 可正確 import ──────────────
    def test_action_keyword_boost_importable(self):
        """config.action_list 可以正確 import ACTION_KEYWORD_BOOST。"""
        from config.action_list import ACTION_KEYWORD_BOOST

        self.assertIsInstance(ACTION_KEYWORD_BOOST, dict,
                              "ACTION_KEYWORD_BOOST 應為 dict")
        self.assertIn("對話", ACTION_KEYWORD_BOOST,
                      "ACTION_KEYWORD_BOOST 應包含 key '對話'")
        self.assertIn("賣咖啡", ACTION_KEYWORD_BOOST,
                      "ACTION_KEYWORD_BOOST 應包含 key '賣咖啡'")

    # ── 情境 2：DIALOGUE_REJECT_TEMPLATES 可正確 import ─────────
    def test_dialogue_reject_templates_importable(self):
        """config.action_list 可以正確 import DIALOGUE_REJECT_TEMPLATES。"""
        from config.action_list import DIALOGUE_REJECT_TEMPLATES

        self.assertIsInstance(DIALOGUE_REJECT_TEMPLATES, list,
                              "DIALOGUE_REJECT_TEMPLATES 應為 list")
        self.assertGreaterEqual(len(DIALOGUE_REJECT_TEMPLATES), 3,
                                "DIALOGUE_REJECT_TEMPLATES 長度應 >= 3")

    # ── 情境 3：config/triggers.py 不再存在 ─────────────────────
    def test_triggers_module_deleted(self):
        """config.triggers 應不再存在，import 應拋出 ModuleNotFoundError。"""
        import importlib
        import sys

        # 清除可能殘留的 cached import
        sys.modules.pop("config.triggers", None)

        with self.assertRaises(ModuleNotFoundError,
                               msg="config.triggers 仍可 import，表示檔案尚未刪除"):
            importlib.import_module("config.triggers")

    # ── 情境 4：markov_engine 可正確 import（驗證 import 路徑更新）──
    def test_markov_engine_importable(self):
        """core.markov_engine 可以正確 import，間接驗證 import 路徑更新正確。"""
        try:
            import core.markov_engine  # noqa: F401
        except ImportError as e:
            self.fail(f"import core.markov_engine 拋出 ImportError：{e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
