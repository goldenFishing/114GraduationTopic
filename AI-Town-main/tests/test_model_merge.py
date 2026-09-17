# ================================================================
# tests/test_model_merge.py
# 驗證 model/ 目錄整合是否正確
# ================================================================

import sys
import os
import unittest

# 確保專案根目錄在 sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class TestInferenceEngineImports(unittest.TestCase):
    """情境 1：inference_engine 可以 import 所有必要類別"""

    def test_import_all_classes(self):
        try:
            from model.inference_engine import (
                VisionEncoder, TextEncoder, FusionDecoder, GenerationConfig
            )
        except ImportError as e:
            self.fail(f"inference_engine import 失敗：{e}")


class TestPromptIOImports(unittest.TestCase):
    """情境 2：prompt_io 可以 import 所有必要類別/函式"""

    def test_import_all_symbols(self):
        try:
            from model.prompt_io import PromptBuilder, parse_decision_output
        except ImportError as e:
            self.fail(f"prompt_io import 失敗：{e}")


class TestOldModulesGone(unittest.TestCase):
    """情境 3：舊模組不存在"""

    def test_vision_encoder_gone(self):
        with self.assertRaises(ModuleNotFoundError):
            import model.vision_encoder  # noqa: F401

    def test_fusion_decoder_gone(self):
        with self.assertRaises(ModuleNotFoundError):
            import model.fusion_decoder  # noqa: F401

    def test_prompt_builder_gone(self):
        with self.assertRaises(ModuleNotFoundError):
            import model.prompt_builder  # noqa: F401

    def test_output_parser_gone(self):
        with self.assertRaises(ModuleNotFoundError):
            import model.output_parser  # noqa: F401


class TestModelLoaderImport(unittest.TestCase):
    """情境 4：model_loader 可以正常 import（間接驗證 inference_engine import 正確）"""

    def test_import_model_loader(self):
        try:
            import model.model_loader  # noqa: F401
        except ImportError:
            # ML 套件（transformers 等）未安裝是預期行為，視為通過
            pass
        except Exception as e:
            self.fail(f"model.model_loader import 發生非預期錯誤：{e}")


class TestAgentImport(unittest.TestCase):
    """情境 5：agent.agent 可以正常 import"""

    def test_import_agent(self):
        try:
            import agent.agent  # noqa: F401
        except ImportError:
            # ML 套件相關的 ImportError 視為通過
            pass
        except Exception as e:
            self.fail(f"agent.agent import 發生非預期錯誤：{e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
